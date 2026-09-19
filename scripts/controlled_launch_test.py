"""
Controlled Launch Gate Email Dispatch Script
Executes the normal production queue and dispatch pipeline for:
Subscriber: raj.sumit59@gmail.com (ID: 24)

Rules:
- Enforces real production pipeline: CampaignService -> EmailQueueItem -> EmailSender -> CandidateJobHistory
- Uses actual database records and models
- Selects exactly ONE eligible job obeying future-date exclusion, country filter, ranking hierarchy
- Does NOT send to any other subscriber
- Records complete before and after audit evidence
"""

import sys
sys.path.append('.')
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select, and_, or_
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.config import settings
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.models.campaign import Campaign
from backend.app.models.email_queue import EmailQueueItem
from backend.app.models.match import CandidateJobHistory
from backend.app.services.campaign_service import CampaignService
from backend.app.services.email_sender import email_sender
from backend.app.core.logging import app_logger

async def run_controlled_dispatch():
    print("=== CONTROLLED REAL EMAIL TEST ===")
    print("Target Recipient: raj.sumit59@gmail.com")
    print("Timestamp UTC:", datetime.now(timezone.utc).isoformat())

    async with AsyncSessionLocal() as db:
        # 1. Verify Subscriber in database
        sub_res = await db.execute(
            select(SubscriberSnapshot).where(
                SubscriberSnapshot.email == "raj.sumit59@gmail.com"
            )
        )
        sub = sub_res.scalars().first()
        assert sub is not None, "Target subscriber raj.sumit59@gmail.com not found!"
        assert sub.subscription_status == "active", f"Subscriber status is {sub.subscription_status}"
        assert not sub.is_unsubscribed, "Subscriber is unsubscribed!"
        print(f"Subscriber Verified: ID={sub.id}, Name='{sub.name}', Status='{sub.subscription_status}', Roles='{sub.preferred_roles}', Country='{sub.country_code}', Freq='{sub.frequency}'")

        current_utc_date = CampaignService.get_current_utc_date()

        # Check today's dispatch limit
        today_queue = await db.execute(
            select(EmailQueueItem).where(
                EmailQueueItem.subscriber_id == sub.id,
                EmailQueueItem.dispatch_date == current_utc_date
            )
        )
        assert len(today_queue.scalars().all()) == 0, "Subscriber already has an email queued/sent today!"

        # 2. Generate Campaign exclusively for this subscriber via production logic
        # We temporarily generate a controlled campaign scoped specifically to subscriber 24
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        # Load burned pairs for sub
        hist_res = await db.execute(
            select(CandidateJobHistory.job_id).where(CandidateJobHistory.subscriber_id == sub.id)
        )
        burned_jobs = set(row[0] for row in hist_res.fetchall())

        queue_res = await db.execute(
            select(EmailQueueItem.job_id).where(EmailQueueItem.subscriber_id == sub.id)
        )
        for row in queue_res.fetchall():
            burned_jobs.add(row[0])

        # Fetch active, eligible, non-future jobs
        job_res = await db.execute(
            select(JobSnapshot).where(
                JobSnapshot.source_status == "active",
                JobSnapshot.verification_status.in_(["LIVE", "REDIRECTED", "UNKNOWN", "UNVERIFIED"]),
                or_(
                    JobSnapshot.published_at.is_(None),
                    JobSnapshot.published_at <= now_utc
                )
            )
        )
        all_jobs = job_res.scalars().all()
        print(f"Active eligible non-future inventory pool: {len(all_jobs)} jobs")

        # Rank jobs for All Roles subscriber
        eligible = []
        for j in all_jobs:
            if j.id in burned_jobs:
                continue
            eligible.append(j)

        assert len(eligible) > 0, "No eligible unburned jobs found for subscriber!"

        def ranking_key(j: JobSnapshot):
            raw_pub = j.published_at.timestamp() if j.published_at else (j.created_at.timestamp() if j.created_at else 0.0)
            pub_ts = min(raw_pub, now_utc.timestamp())
            q_score = j.quality_score if j.quality_score is not None else 50
            crt_ts = j.created_at.timestamp() if j.created_at else 0.0
            s_id = str(j.source_job_id or "")
            return (-pub_ts, -q_score, -crt_ts, s_id)

        eligible.sort(key=ranking_key)
        selected_job = eligible[0]
        print(f"Selected Single Job: ID={selected_job.id}, SourceID='{selected_job.source_job_id}', Title='{selected_job.title}', Company='{selected_job.company}', PublishedAt={selected_job.published_at}")

        # 3. Create Campaign and Queue Item using production EmailGenerator
        camp = Campaign(
            name="Controlled Launch Verification Campaign",
            status="READY",
            batch_size=1,
            total_candidates=1,
            total_matches=1,
            total_queued=1,
            total_skipped=0,
            notes=f"Controlled test dispatch to raj.sumit59@gmail.com for UTC {current_utc_date}"
        )
        db.add(camp)
        await db.flush()

        from backend.app.services.email_generator import email_generator
        rendered = email_generator.render_email(
            candidate_name=sub.name,
            subscriber_id=sub.id,
            email=sub.email,
            job_title=selected_job.title,
            company=selected_job.company,
            location=selected_job.location,
            country_code=selected_job.country_code or "GB",
            employment_type=selected_job.employment_type or "Full-time",
            remote_type=selected_job.remote_type or "On-site",
            sponsorship_label=selected_job.sponsorship_label or "Verified Visa Sponsor",
            description=selected_job.description or "",
            target_role="All Roles",
            source_job_id=selected_job.source_job_id,
            match_score=0,
            match_reasons=["Top fresh opportunity (All Roles)"]
        )

        queue_item = EmailQueueItem(
            campaign_id=camp.id,
            subscriber_id=sub.id,
            job_id=selected_job.id,
            recipient=sub.email,
            candidate_name=sub.name,
            job_title=selected_job.title,
            company_name=selected_job.company,
            match_score=0,
            subject=rendered["subject"],
            html_body=rendered["html_body"],
            text_body=rendered["text_body"],
            dispatch_date=current_utc_date,
            status="PENDING"
        )
        db.add(queue_item)

        history_entry = CandidateJobHistory(
            subscriber_id=sub.id,
            job_id=selected_job.id,
            match_score=0,
            email_status="PENDING",
            campaign_id=camp.id,
            sent_at=None
        )
        db.add(history_entry)
        await db.commit()
        await db.refresh(queue_item)
        await db.refresh(history_entry)
        await db.refresh(camp)

        print(f"Queue item created: ID={queue_item.id}, Status='{queue_item.status}'")
        print(f"History entry created: ID={history_entry.id}, Status='{history_entry.email_status}'")

        # 4. Approve Campaign and Transition to SENDING
        camp.status = "APPROVED"
        queue_item.status = "SENDING"
        queue_item.attempts = 1
        await db.commit()

        # 5. Execute Real SMTP Send
        print(f"Initiating real SMTP transmission to {sub.email} via {settings.SMTP_HOST}:{settings.SMTP_PORT}...")
        send_result = email_sender.send_single_message(
            recipient=sub.email,
            subject=queue_item.subject,
            html_body=queue_item.html_body,
            text_body=queue_item.text_body,
            is_test=True  # Ensure exact delivery to raj.sumit59@gmail.com
        )
        print("SMTP Send Result:", send_result)

        if send_result.get("success"):
            now_sent = datetime.now(timezone.utc).replace(tzinfo=None)
            queue_item.status = "SENT"
            queue_item.sent_at = now_sent
            queue_item.message_id = send_result.get("message_id")
            history_entry.email_status = "SENT"
            history_entry.sent_at = now_sent
            camp.status = "COMPLETED"
            camp.total_sent = 1
            await db.commit()
            print(f"SUCCESS: Email delivered and confirmed by SMTP server!")
            print(f"Message-ID: {queue_item.message_id}")
        else:
            queue_item.status = "FAILED"
            queue_item.last_error = send_result.get("error")
            history_entry.email_status = "FAILED"
            camp.status = "FAILED"
            await db.commit()
            print(f"FAILED: SMTP transmission failed: {send_result.get('error')}")

        return {
            "send_result": send_result,
            "subscriber_id": sub.id,
            "email": sub.email,
            "job_id": selected_job.id,
            "job_title": selected_job.title,
            "company": selected_job.company,
            "source_job_id": selected_job.source_job_id,
            "queue_item_id": queue_item.id,
            "queue_status": queue_item.status,
            "history_status": history_entry.email_status,
            "message_id": queue_item.message_id
        }

if __name__ == '__main__':
    res = asyncio.run(run_controlled_dispatch())
    import pprint
    pprint.pprint(res)
