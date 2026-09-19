"""
Email Transmission Service
Delivers queued job alert emails via SMTP with:
1. Strict rate limiting and DRY_RUN / TEST_MODE safeguards.
2. Crash-window protection: Stale SENDING items (>30 mins) marked REQUIRES_RECONCILIATION (never blindly resent).
3. Transmission retry on SAME queue item (never creates a new queue item).
4. Permanent failure marking (subscriber-job pair remains permanently burned).
"""

import smtplib
import asyncio
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from backend.app.core.config import settings
from backend.app.core.logging import email_logger, log_audit
from backend.app.models.email_queue import EmailQueueItem
from backend.app.models.match import CandidateJobHistory
from backend.app.models.campaign import Campaign

class EmailSender:
    @staticmethod
    def is_smtp_configured() -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD)

    def send_single_message(
        self,
        recipient: str,
        subject: str,
        html_body: str,
        text_body: str,
        is_test: bool = False
    ) -> Dict[str, Any]:
        """
        Deliver a single email via SMTP port 587 with STARTTLS.
        Enforces DRY_RUN and EMAIL_TEST_MODE protections.
        """
        message_id = f"<{uuid.uuid4()}@sponsorajobs.com>"
        intended_recipient = recipient

        # Enforce TEST MODE redirect
        actual_recipient = recipient
        if settings.EMAIL_TEST_MODE and not is_test:
            actual_recipient = settings.TEST_EMAIL_ADDRESS
            email_logger.info(
                f"[TEST_MODE_REDIRECT] Intended: {intended_recipient} -> Redirected to: {actual_recipient}"
            )

        # Enforce DRY RUN safeguard
        if settings.DRY_RUN:
            email_logger.info(
                f"[DRY_RUN] Simulated send to: {actual_recipient} (Intended: {intended_recipient}) | Subject: '{subject}' | Message-ID: {message_id}"
            )
            return {
                "success": True,
                "message_id": message_id,
                "mode": "DRY_RUN",
                "actual_recipient": actual_recipient,
                "intended_recipient": intended_recipient,
                "error": None
            }

        # Real SMTP Delivery
        if not self.is_smtp_configured():
            err_msg = "SMTP credentials incomplete in .env. Cannot transmit outbound email."
            email_logger.error(err_msg)
            return {"success": False, "error": err_msg, "message_id": None, "is_transient": False}

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
            msg["To"] = actual_recipient
            msg["Message-ID"] = message_id
            msg["X-Intended-Recipient"] = intended_recipient
            if settings.EMAIL_TEST_MODE:
                msg["X-SponsorAJobs-Test-Mode"] = "true"

            part_text = MIMEText(text_body, "plain", "utf-8")
            part_html = MIMEText(html_body, "html", "utf-8")
            msg.attach(part_text)
            msg.attach(part_html)

            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20)
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, [actual_recipient], msg.as_string())
            server.quit()

            email_logger.info(
                f"[SENT] To: {actual_recipient} | Intended: {intended_recipient} | Subject: '{subject}' | ID: {message_id}"
            )
            return {
                "success": True,
                "message_id": message_id,
                "mode": "SMTP",
                "actual_recipient": actual_recipient,
                "intended_recipient": intended_recipient,
                "error": None
            }

        except smtplib.SMTPAuthenticationError as e:
            err = f"SMTP Authentication failed: {str(e)}"
            email_logger.error(err)
            return {"success": False, "error": err, "is_transient": False}
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected) as e:
            err = f"SMTP Connection error: {str(e)}"
            email_logger.error(err)
            return {"success": False, "error": err, "is_transient": True}
        except smtplib.SMTPRecipientsRefused as e:
            err = f"Recipient refused: {str(e)}"
            email_logger.error(err)
            return {"success": False, "error": err, "is_transient": False}
        except Exception as e:
            err = f"Unexpected SMTP failure: {str(e)}"
            email_logger.error(err)
            return {"success": False, "error": err, "is_transient": True}

    async def reconcile_stale_sending_items(
        self,
        db: AsyncSession,
        stale_threshold_minutes: int = 30
    ) -> List[int]:
        """
        Crash-Window Protection:
        Detects queue items locked in 'SENDING' status beyond the stale threshold.
        Instead of blindly resending, transitions them to 'REQUIRES_RECONCILIATION'.
        """
        cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=stale_threshold_minutes)
        res = await db.execute(
            select(EmailQueueItem).where(
                EmailQueueItem.status == "SENDING",
                EmailQueueItem.locked_at < cutoff_time
            )
        )
        stale_items = res.scalars().all()
        reconciled_ids = []

        for item in stale_items:
            item.status = "REQUIRES_RECONCILIATION"
            item.reconciliation_status = "STALE_SENDING_FLAGGED"
            item.error_message = (
                f"Worker crash or timeout detected: Item was in SENDING since {item.locked_at}. "
                "Withheld from blind resend pending manual delivery confirmation."
            )
            reconciled_ids.append(item.id)

        if reconciled_ids:
            await db.commit()
            log_audit(
                actor="system",
                action="RECONCILE_STALE_SENDING",
                details=f"Flagged {len(reconciled_ids)} stale SENDING items for reconciliation: {reconciled_ids}"
            )

        return reconciled_ids

    async def process_campaign_queue(
        self,
        db: AsyncSession,
        campaign_id: int,
        batch_limit: int = 50
    ) -> Dict[str, Any]:
        """
        Process pending emails in the campaign queue with rate limiting and idempotency controls.
        """
        # 1. First run crash-window reconciliation for any stale items
        await self.reconcile_stale_sending_items(db, stale_threshold_minutes=30)

        # 2. Load campaign
        c_res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = c_res.scalars().first()
        if not campaign:
            return {"error": "Campaign not found"}

        if campaign.status not in ("READY", "APPROVED", "DISPATCHING", "SENDING"):
            return {"error": f"Cannot send campaign in status '{campaign.status}'. Campaign must be READY or APPROVED."}

        campaign.status = "DISPATCHING"
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        if not campaign.started_at:
            campaign.started_at = now_utc
        await db.commit()

        # 3. Query pending emails for this campaign
        q_res = await db.execute(
            select(EmailQueueItem).where(
                EmailQueueItem.campaign_id == campaign_id,
                EmailQueueItem.status == "PENDING"
            ).limit(batch_limit)
        )
        items = q_res.scalars().all()

        if not items:
            # Check if all items in campaign are completed
            rem_res = await db.execute(
                select(EmailQueueItem).where(
                    EmailQueueItem.campaign_id == campaign_id,
                    EmailQueueItem.status.in_(["PENDING", "SENDING"])
                )
            )
            if not rem_res.scalars().first():
                campaign.status = "COMPLETED"
                campaign.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await db.commit()
            return {"processed": 0, "status": campaign.status}

        sent_count = 0
        failed_count = 0
        rate_per_min = max(1, settings.EMAIL_RATE_PER_MINUTE)
        delay_between_sends = 60.0 / rate_per_min

        for item in items:
            # Idempotency check: Ensure not already delivered
            if item.status == "SENT":
                continue

            # Lock item into SENDING state with timestamp
            item.status = "SENDING"
            item.locked_at = datetime.now(timezone.utc).replace(tzinfo=None)
            item.attempts += 1
            await db.commit()

            # Execute SMTP send in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.send_single_message,
                item.recipient,
                item.subject,
                item.html_body,
                item.text_body,
                False
            )

            now_sent = datetime.now(timezone.utc).replace(tzinfo=None)

            if result["success"]:
                item.status = "SENT"
                item.sent_at = now_sent
                item.locked_at = None
                item.message_id = result.get("message_id")
                sent_count += 1
                campaign.total_sent += 1

                # Update or record in candidate_job_history for duplicate prevention
                h_res = await db.execute(
                    select(CandidateJobHistory).where(
                        CandidateJobHistory.subscriber_id == item.subscriber_id,
                        CandidateJobHistory.job_id == item.job_id
                    )
                )
                history_entry = h_res.scalars().first()
                if history_entry:
                    history_entry.email_status = "SENT"
                    history_entry.sent_at = now_sent
                else:
                    db.add(CandidateJobHistory(
                        subscriber_id=item.subscriber_id,
                        job_id=item.job_id,
                        match_score=item.match_score,
                        email_status="SENT",
                        campaign_id=campaign_id,
                        sent_at=now_sent
                    ))
            else:
                item.error_message = result.get("error")
                item.locked_at = None
                is_transient = result.get("is_transient", True)

                # Update history status on failure
                h_res = await db.execute(
                    select(CandidateJobHistory).where(
                        CandidateJobHistory.subscriber_id == item.subscriber_id,
                        CandidateJobHistory.job_id == item.job_id
                    )
                )
                history_entry = h_res.scalars().first()

                if item.attempts >= settings.EMAIL_MAX_RETRIES or not is_transient:
                    # Permanent failure: mark FAILED.
                    # The (subscriber_id, job_id) remains permanently burned via history & queue.
                    item.status = "FAILED"
                    if history_entry:
                        history_entry.email_status = "FAILED"
                    failed_count += 1
                    campaign.total_failed += 1
                else:
                    # Transient error: keep SAME queue item for retry
                    item.status = "PENDING"
                    if history_entry:
                        history_entry.email_status = "RETRY"

            await db.commit()

            # Rate limit delay unless in dry run
            if not settings.DRY_RUN:
                await asyncio.sleep(delay_between_sends)

        # Check if entire campaign queue has completed
        check_res = await db.execute(
            select(EmailQueueItem).where(
                EmailQueueItem.campaign_id == campaign_id,
                EmailQueueItem.status.in_(["PENDING", "SENDING"])
            )
        )
        if not check_res.scalars().first():
            campaign.status = "COMPLETED"
            campaign.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()

        log_audit(
            actor="worker",
            action="PROCESS_EMAIL_QUEUE",
            details=f"Campaign {campaign_id}: Processed {len(items)} items. {sent_count} sent, {failed_count} failed."
        )

        return {
            "processed": len(items),
            "sent": sent_count,
            "failed": failed_count,
            "campaign_status": campaign.status
        }

    async def send_single_queue_item(
        self,
        db: AsyncSession,
        queue_id: int
    ) -> Dict[str, Any]:
        """Send a single verified queue item immediately."""
        res = await db.execute(select(EmailQueueItem).where(EmailQueueItem.id == queue_id))
        item = res.scalars().first()
        if not item:
            return {"success": False, "error": f"Queue item #{queue_id} not found"}

        if item.status == "SENT":
            return {"success": True, "already_sent": True, "message": f"Email #{queue_id} already sent previously", "message_id": item.message_id}

        item.status = "SENDING"
        item.locked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        item.attempts += 1
        await db.commit()

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.send_single_message,
            item.recipient,
            item.subject,
            item.html_body,
            item.text_body,
            False
        )

        now_sent = datetime.now(timezone.utc).replace(tzinfo=None)
        if result["success"]:
            item.status = "SENT"
            item.sent_at = now_sent
            item.locked_at = None
            item.message_id = result.get("message_id")
            item.error_message = None

            # Update campaign stats if linked
            if item.campaign_id:
                c_res = await db.execute(select(Campaign).where(Campaign.id == item.campaign_id))
                camp = c_res.scalars().first()
                if camp:
                    camp.total_sent = (camp.total_sent or 0) + 1

            # Update candidate_job_history
            h_res = await db.execute(
                select(CandidateJobHistory).where(
                    CandidateJobHistory.subscriber_id == item.subscriber_id,
                    CandidateJobHistory.job_id == item.job_id
                )
            )
            history_entry = h_res.scalars().first()
            if history_entry:
                history_entry.email_status = "SENT"
                history_entry.sent_at = now_sent
            else:
                db.add(CandidateJobHistory(
                    subscriber_id=item.subscriber_id,
                    job_id=item.job_id,
                    match_score=item.match_score,
                    email_status="SENT",
                    campaign_id=item.campaign_id,
                    sent_at=now_sent
                ))
            await db.commit()

            log_audit(
                actor="admin",
                action="SINGLE_EMAIL_SENT",
                details=f"Directly sent email queue item #{queue_id} to {item.recipient} (MsgID: {item.message_id})"
            )
            return {"success": True, "queue_id": queue_id, "recipient": item.recipient, "message_id": item.message_id}
        else:
            item.error_message = result.get("error")
            item.locked_at = None
            item.status = "FAILED"
            if item.campaign_id:
                c_res = await db.execute(select(Campaign).where(Campaign.id == item.campaign_id))
                camp = c_res.scalars().first()
                if camp:
                    camp.total_failed = (camp.total_failed or 0) + 1
            await db.commit()
            return {"success": False, "queue_id": queue_id, "error": result.get("error")}

    async def send_selected_queue_items(
        self,
        db: AsyncSession,
        queue_ids: List[int]
    ) -> Dict[str, Any]:
        """Send a chosen batch of verified queue items with safety controls."""
        if not queue_ids:
            return {"processed": 0, "sent": 0, "failed": 0, "message": "No queue IDs provided"}

        sent_count = 0
        failed_count = 0
        results = []

        rate_per_min = max(1, settings.EMAIL_RATE_PER_MINUTE)
        delay_between_sends = 60.0 / rate_per_min

        for q_id in queue_ids:
            res = await self.send_single_queue_item(db, q_id)
            results.append(res)
            if res.get("success"):
                sent_count += 1
            else:
                failed_count += 1

            if not settings.DRY_RUN and len(queue_ids) > 1:
                await asyncio.sleep(delay_between_sends)

        log_audit(
            actor="admin",
            action="BATCH_SELECTED_EMAILS_SENT",
            details=f"Admin sent {len(queue_ids)} selected emails: {sent_count} sent, {failed_count} failed."
        )

        return {
            "total_selected": len(queue_ids),
            "sent": sent_count,
            "failed": failed_count,
            "results": results
        }

email_sender = EmailSender()
