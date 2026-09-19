from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.models.match import CandidateJobMatch
from backend.app.models.campaign import Campaign
from backend.app.models.email_queue import EmailQueueItem
from backend.app.models.email_composition import EmailComposition
from backend.app.models.unsubscribe import Unsubscribe
from backend.app.schemas.stats import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    # Subscribers
    sub_count = (await db.execute(select(func.count(SubscriberSnapshot.id)))).scalar() or 0
    active_sub_count = (await db.execute(
        select(func.count(SubscriberSnapshot.id)).where(
            SubscriberSnapshot.subscription_status == "active",
            SubscriberSnapshot.is_unsubscribed == False
        )
    )).scalar() or 0
    unsub_count = (await db.execute(select(func.count(Unsubscribe.id)))).scalar() or 0

    # Jobs
    job_count = (await db.execute(select(func.count(JobSnapshot.id)))).scalar() or 0
    live_jobs = (await db.execute(
        select(func.count(JobSnapshot.id)).where(
            JobSnapshot.source_status == "active"
        )
    )).scalar() or 0
    verified_jobs = (await db.execute(
        select(func.count(JobSnapshot.id)).where(
            JobSnapshot.verification_status.in_(["LIVE", "REDIRECTED"])
        )
    )).scalar() or 0
    dead_jobs = (await db.execute(
        select(func.count(JobSnapshot.id)).where(
            JobSnapshot.verification_status == "DEAD"
        )
    )).scalar() or 0

    # Matches
    match_count = (await db.execute(select(func.count(CandidateJobMatch.id)))).scalar() or 0

    # Email Queue & Delivery
    queued = (await db.execute(
        select(func.count(EmailQueueItem.id)).where(
            EmailQueueItem.status.in_(["PENDING", "SENDING"])
        )
    )).scalar() or 0
    sent = (await db.execute(
        select(func.count(EmailQueueItem.id)).where(EmailQueueItem.status == "SENT")
    )).scalar() or 0
    failed = (await db.execute(
        select(func.count(EmailQueueItem.id)).where(EmailQueueItem.status == "FAILED")
    )).scalar() or 0

    # Today's UTC Date start
    now_utc = datetime.now(timezone.utc)
    today_utc_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

    todays_camps = (await db.execute(
        select(func.count(Campaign.id)).where(Campaign.created_at >= today_utc_start)
    )).scalar() or 0

    emails_generated = (await db.execute(
        select(func.count(EmailComposition.id))
    )).scalar() or 0

    total_skipped = (await db.execute(
        select(func.sum(Campaign.total_skipped))
    )).scalar() or 0

    jobs_selected = (await db.execute(
        select(func.count(distinct(EmailComposition.job_id)))
    )).scalar() or 0

    smtp_failures = (await db.execute(
        select(func.count(EmailQueueItem.id)).where(
            EmailQueueItem.status == "FAILED"
        )
    )).scalar() or 0

    retries = (await db.execute(
        select(func.count(EmailQueueItem.id)).where(
            EmailQueueItem.attempts > 1
        )
    )).scalar() or 0

    reconciliation_required = (await db.execute(
        select(func.count(EmailQueueItem.id)).where(
            EmailQueueItem.status == "REQUIRES_RECONCILIATION"
        )
    )).scalar() or 0

    return DashboardStats(
        total_subscribers=sub_count,
        active_subscribers=active_sub_count,
        unsubscribed_users=unsub_count,
        total_jobs=job_count,
        live_jobs=live_jobs,
        verified_jobs=verified_jobs,
        dead_jobs=dead_jobs,
        potential_matches=match_count,
        queued_emails=queued,
        sent_emails=sent,
        failed_emails=failed,
        dry_run_mode=settings.DRY_RUN,
        email_test_mode=settings.EMAIL_TEST_MODE,
        test_email_address=settings.TEST_EMAIL_ADDRESS,
        todays_campaigns=todays_camps,
        emails_generated=emails_generated,
        subscribers_skipped=int(total_skipped),
        jobs_selected=jobs_selected,
        smtp_failures=smtp_failures,
        retries=retries,
        reconciliation_required_records=reconciliation_required
    )
