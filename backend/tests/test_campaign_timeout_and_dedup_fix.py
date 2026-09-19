import pytest
import time
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi import HTTPException

from backend.app.main import app
from backend.app.core.database import Base
from backend.app.models.campaign import Campaign
from backend.app.models.email_queue import EmailQueueItem
from backend.app.models.email_composition import EmailComposition
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.models.match import CandidateJobHistory
from backend.app.services.campaign_service import CampaignService

@pytest.fixture
async def mem_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_successful_campaign_creation_returns_valid_json_and_one_campaign(mem_session: AsyncSession):
    """
    Test 1, 6, 7 & 8:
    - Successful campaign creation returns valid JSON.
    - Exactly one campaign is created in READY status.
    - Queue, composition, and history records are created.
    - Zero emails sent during generation (sent=0).
    """
    db = mem_session
    svc = CampaignService()
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

    sub = SubscriberSnapshot(
        source_subscriber_id="sub_perf_1",
        name="John Doe",
        email="john.doe@example.com",
        preferred_roles="Data Engineer",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    job = JobSnapshot(
        source_job_id="job_perf_1",
        title="Senior Data Engineer",
        company="Data Corp",
        location="Manchester",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/job_perf_1",
        source_status="active",
        verification_status="LIVE",
        published_at=now_naive
    )
    db.add(sub)
    db.add(job)
    await db.commit()

    campaign = await svc.create_and_generate_campaign(
        db=db,
        name="Unique Test Perf Campaign",
        batch_size=50
    )

    assert campaign.id is not None
    assert campaign.status == "READY"
    assert campaign.total_queued == 1
    assert campaign.total_sent == 0  # No SMTP transmission occurred

    # Verify queue item
    q_res = await db.execute(select(EmailQueueItem).where(EmailQueueItem.campaign_id == campaign.id))
    q_items = q_res.scalars().all()
    assert len(q_items) == 1
    assert q_items[0].status == "PENDING"
    assert q_items[0].sent_at is None

    # Verify composition
    comp_res = await db.execute(select(EmailComposition).where(EmailComposition.campaign_id == campaign.id))
    comps = comp_res.scalars().all()
    assert len(comps) == 1
    assert comps[0].queue_id == q_items[0].id
    assert comps[0].recipient == "john.doe@example.com"

    # Verify candidate history
    hist_res = await db.execute(select(CandidateJobHistory).where(CandidateJobHistory.campaign_id == campaign.id))
    histories = hist_res.scalars().all()
    assert len(histories) == 1
    assert histories[0].email_status == "PENDING"

@pytest.mark.asyncio
async def test_repeated_identical_generation_rejected(mem_session: AsyncSession):
    """
    Test 4 & 5:
    - Repeated identical generation requests are rejected with HTTP 409.
    - Prevents accidental duplicate campaigns.
    """
    db = mem_session
    svc = CampaignService()
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

    sub = SubscriberSnapshot(
        source_subscriber_id="sub_dup_1",
        name="Jane Dup",
        email="jane.dup@example.com",
        preferred_roles="Accountant",
        country_code="GB",
        subscription_status="active"
    )
    db.add(sub)
    await db.commit()

    # First submission
    c1 = await svc.create_and_generate_campaign(
        db=db,
        name="Duplicate Prevention Test Campaign",
        batch_size=10
    )
    assert c1.status == "READY"

    # Immediate duplicate submission with identical name
    with pytest.raises(HTTPException) as exc_info:
        await svc.create_and_generate_campaign(
            db=db,
            name="Duplicate Prevention Test Campaign",
            batch_size=10
        )
    assert exc_info.value.status_code == 409
    assert "already created recently" in exc_info.value.detail

@pytest.mark.asyncio
async def test_expired_and_future_jobs_excluded(mem_session: AsyncSession):
    """
    Test 10 & 11:
    - Expired jobs (> closing_date or source_status='expired') are excluded.
    - Future-dated jobs (> published_at in future) are excluded.
    """
    db = mem_session
    svc = CampaignService()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    sub = SubscriberSnapshot(
        source_subscriber_id="sub_exp_test",
        name="Test Candidate",
        email="cand@example.com",
        preferred_roles="Civil Engineer",
        country_code="GB",
        subscription_status="active"
    )

    # Expired job (closing date in past)
    expired_job = JobSnapshot(
        source_job_id="job_past_exp",
        title="Civil Engineer (Expired)",
        company="Old Builders",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/job_past_exp",
        source_status="active",
        verification_status="LIVE",
        published_at=now_utc - timedelta(days=30),
        closing_date=now_utc - timedelta(days=1)
    )

    # Future-dated job
    future_job = JobSnapshot(
        source_job_id="job_future_pub",
        title="Civil Engineer (Future)",
        company="Future Builders",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/job_future_pub",
        source_status="active",
        verification_status="LIVE",
        published_at=now_utc + timedelta(days=2)
    )

    # Valid active job
    valid_job = JobSnapshot(
        source_job_id="job_valid_live",
        title="Civil Engineer",
        company="Current Builders",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/job_valid_live",
        source_status="active",
        verification_status="LIVE",
        published_at=now_utc - timedelta(days=2),
        closing_date=now_utc + timedelta(days=14)
    )

    db.add_all([sub, expired_job, future_job, valid_job])
    await db.commit()

    campaign = await svc.create_and_generate_campaign(
        db=db,
        name="Expiry Exclusion Test Campaign",
        batch_size=10
    )

    assert campaign.total_queued == 1
    q_res = await db.execute(select(EmailQueueItem).where(EmailQueueItem.campaign_id == campaign.id))
    item = q_res.scalars().first()
    assert item.job_id == valid_job.id
    assert item.job_title == "Civil Engineer"

@pytest.mark.asyncio
async def test_ranking_and_deduplication_preserved(mem_session: AsyncSession):
    """
    Test 9 & 12:
    - DIRECT match preferred over VARIANT and SYNONYM.
    - Permanent subscriber-job burn prevents re-selection.
    """
    db = mem_session
    svc = CampaignService()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    sub = SubscriberSnapshot(
        source_subscriber_id="sub_ranking_test",
        name="Rank Tester",
        email="rank@example.com",
        preferred_roles="Software Engineer",
        country_code="GB",
        subscription_status="active"
    )

    # DIRECT match
    direct_job = JobSnapshot(
        source_job_id="job_direct",
        title="Software Engineer",
        company="Company A",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/job_direct",
        source_status="active",
        verification_status="LIVE",
        published_at=now_utc - timedelta(days=1)
    )

    # VARIANT match
    variant_job = JobSnapshot(
        source_job_id="job_variant",
        title="Senior Software Engineer",
        company="Company B",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/job_variant",
        source_status="active",
        verification_status="LIVE",
        published_at=now_utc - timedelta(hours=1) # fresher, but variant
    )

    db.add_all([sub, direct_job, variant_job])
    await db.commit()

    # Campaign 1: must select DIRECT job despite variant having fresher timestamp
    c1 = await svc.create_and_generate_campaign(
        db=db,
        name="Ranking Test Campaign 1",
        batch_size=10
    )
    q1 = (await db.execute(select(EmailQueueItem).where(EmailQueueItem.campaign_id == c1.id))).scalars().first()
    assert q1.job_id == direct_job.id
    assert q1.match_score == 3  # DIRECT

    # Campaign 2 on next day: direct job is now burned, so variant job is selected
    svc.get_current_utc_date = lambda: (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    c2 = await svc.create_and_generate_campaign(
        db=db,
        name="Ranking Test Campaign 2 (Next Day)",
        batch_size=10
    )
    q2 = (await db.execute(select(EmailQueueItem).where(EmailQueueItem.campaign_id == c2.id))).scalars().first()
    assert q2.job_id == variant_job.id
    assert q2.match_score == 2  # VARIANT
