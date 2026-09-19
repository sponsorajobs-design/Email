import sys
sys.path.append('.')
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select, delete, or_
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.models.campaign import Campaign
from backend.app.models.email_queue import EmailQueueItem
from backend.app.models.match import CandidateJobHistory
from backend.app.services.campaign_service import CampaignService
from backend.app.services.email_sender import email_sender
from backend.app.services.email_generator import email_generator

async def send_relevant_job():
    print("=== DISPATCHING RELEVANT CIVIL ENGINEER JOB ALERT ===")
    print("Recipient: raj.sumit59@gmail.com")
    
    async with AsyncSessionLocal() as db:
        # 1. Update preferred_roles to 'Civil Engineer'
        sub_res = await db.execute(
            select(SubscriberSnapshot).where(SubscriberSnapshot.email == "raj.sumit59@gmail.com")
        )
        sub = sub_res.scalars().first()
        assert sub is not None, "Subscriber not found!"
        sub.preferred_roles = "Civil Engineer"
        sub.subscription_status = "active"
        print(f"Updated Subscriber {sub.id}: preferred_roles='{sub.preferred_roles}'")

        # 2. Reset previous test send from earlier today to allow new dispatch
        await db.execute(
            delete(EmailQueueItem).where(EmailQueueItem.subscriber_id == sub.id)
        )
        await db.execute(
            delete(CandidateJobHistory).where(CandidateJobHistory.subscriber_id == sub.id)
        )
        await db.commit()
        print("Previous test queue and history records reset for fresh relevant dispatch.")

        # Clean up campaign 10 queue item if created
        await db.execute(delete(EmailQueueItem).where(EmailQueueItem.campaign_id == 10))
        await db.execute(delete(Campaign).where(Campaign.id == 10))
        await db.commit()

        # 3. Find top relevant Civil Engineer job using production RoleMatcher & ranking
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        current_utc_date = CampaignService.get_current_utc_date()

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
        level_map = {"DIRECT": 3, "VARIANT": 2, "SYNONYM": 1, "NONE": 0}

        eligible_candidate_jobs = []
        from backend.app.services.role_matcher import evaluate_role_relevance
        for job in all_jobs:
            match_res = evaluate_role_relevance(
                subscriber_role="Civil Engineer",
                job_title=job.title,
                category_id=job.category_id,
                description=job.description
            )
            if match_res.is_relevant:
                lvl = level_map.get(match_res.match_type, 0)
                eligible_candidate_jobs.append((lvl, job, match_res.matched_reason))

        assert len(eligible_candidate_jobs) > 0, "No matching Civil Engineer jobs found!"

        # Rank: Relevance Level DESC -> Freshness DESC -> Quality DESC -> Created DESC -> source_job_id ASC
        def ranking_key(item):
            lvl, j, _ = item
            raw_pub = j.published_at.timestamp() if j.published_at else (j.created_at.timestamp() if j.created_at else 0.0)
            pub_ts = min(raw_pub, now_utc.timestamp())
            q_score = j.quality_score if j.quality_score is not None else 50
            crt_ts = j.created_at.timestamp() if j.created_at else 0.0
            s_id = str(j.source_job_id or "")
            return (-lvl, -pub_ts, -q_score, -crt_ts, s_id)

        eligible_candidate_jobs.sort(key=ranking_key)
        top_lvl, selected_job, top_reason = eligible_candidate_jobs[0]
        print(f"Selected Relevant Job: Level={top_lvl}, ID={selected_job.id}, Title='{selected_job.title}', Company='{selected_job.company}', Reason='{top_reason}'")

        # Create Campaign & Queue Item
        camp = Campaign(
            name="Civil Engineer Alert Campaign",
            status="APPROVED",
            batch_size=1,
            total_candidates=1,
            total_matches=1,
            total_queued=1,
            total_skipped=0,
            notes=f"Relevant Civil Engineer dispatch to raj.sumit59@gmail.com for UTC {current_utc_date}"
        )
        db.add(camp)
        await db.flush()

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
            target_role="Civil Engineer",
            source_job_id=selected_job.source_job_id,
            match_score=top_lvl,
            match_reasons=[top_reason]
        )

        queue_item = EmailQueueItem(
            campaign_id=camp.id,
            subscriber_id=sub.id,
            job_id=selected_job.id,
            recipient=sub.email,
            candidate_name=sub.name,
            job_title=selected_job.title,
            company_name=selected_job.company,
            match_score=top_lvl,
            subject=rendered["subject"],
            html_body=rendered["html_body"],
            text_body=rendered["text_body"],
            dispatch_date=current_utc_date,
            status="SENDING",
            attempts=1
        )
        db.add(queue_item)

        hist_entry = CandidateJobHistory(
            subscriber_id=sub.id,
            job_id=selected_job.id,
            match_score=top_lvl,
            email_status="PENDING",
            campaign_id=camp.id,
            sent_at=None
        )
        db.add(hist_entry)
        await db.commit()
        await db.refresh(queue_item)
        queue_item.status = "SENDING"
        queue_item.attempts = 1
        await db.commit()

        # 5. Transmit via SMTP
        print(f"Transmitting to {sub.email} via SMTP...")
        send_res = email_sender.send_single_message(
            recipient=sub.email,
            subject=queue_item.subject,
            html_body=queue_item.html_body,
            text_body=queue_item.text_body,
            is_test=True
        )
        print("SMTP Result:", send_res)

        now_sent = datetime.now(timezone.utc).replace(tzinfo=None)
        if send_res.get("success"):
            queue_item.status = "SENT"
            queue_item.sent_at = now_sent
            queue_item.message_id = send_res.get("message_id")

            # Update history entry
            h_res = await db.execute(
                select(CandidateJobHistory).where(
                    CandidateJobHistory.subscriber_id == sub.id,
                    CandidateJobHistory.job_id == queue_item.job_id
                )
            )
            hist = h_res.scalars().first()
            if hist:
                hist.email_status = "SENT"
                hist.sent_at = now_sent

            camp.status = "COMPLETED"
            camp.total_sent = 1
            await db.commit()
            print("SUCCESS: Relevant Civil Engineer Job Alert Transmitted and Confirmed!")
            print("Message-ID:", queue_item.message_id)
        else:
            queue_item.status = "FAILED"
            queue_item.last_error = send_res.get("error")
            camp.status = "FAILED"
            await db.commit()
            print("FAILED:", send_res.get("error"))

        return {
            "recipient": sub.email,
            "job_title": queue_item.job_title,
            "company": queue_item.company_name,
            "subject": queue_item.subject,
            "message_id": queue_item.message_id,
            "status": queue_item.status
        }

if __name__ == '__main__':
    res = asyncio.run(send_relevant_job())
    import pprint
    pprint.pprint(res)
