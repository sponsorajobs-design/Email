import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.app.core.database import Base
from backend.app.models.campaign import Campaign
from backend.app.models.email_queue import EmailQueueItem
from backend.app.models.email_composition import EmailComposition
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.services.campaign_service import CampaignService
from backend.app.services.matching_engine import matching_engine

@pytest.fixture
async def test_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_expired_job_by_status_excluded(test_session: AsyncSession):
    """Rule 2: If the job is explicitly marked expired/inactive/closed -> EXCLUDE."""
    db = test_session
    svc = CampaignService()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    sub = SubscriberSnapshot(
        source_subscriber_id="sub_exp_status_1",
        name="Bob Test",
        email="bob.test@example.com",
        preferred_roles="Software Engineer",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    job_expired = JobSnapshot(
        source_job_id="job_exp_1",
        title="Software Engineer",
        company="Old Tech",
        location="London",
        country_code="GB",
        application_url="https://example.com/jobs/1",
        source_status="expired",
        verification_status="LIVE",
        published_at=now_utc - timedelta(days=2)
    )
    db.add(sub)
    db.add(job_expired)
    await db.commit()

    campaign = await svc.create_and_generate_campaign(db=db, name="Test Status Expired Campaign")
    assert campaign.total_candidates == 1
    assert campaign.emails_generated == 0
    assert campaign.total_queued == 0
    assert campaign.no_eligible_job_count == 1

    # Verify no queue items created
    q_items = (await db.execute(select(EmailQueueItem))).scalars().all()
    assert len(q_items) == 0

@pytest.mark.asyncio
async def test_expired_job_past_closing_date_excluded(test_session: AsyncSession):
    """Rule 1: If closing_date exists and is in the past -> EXCLUDE."""
    db = test_session
    svc = CampaignService()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    sub = SubscriberSnapshot(
        source_subscriber_id="sub_exp_date_1",
        name="Charlie Test",
        email="charlie.test@example.com",
        preferred_roles="Civil Engineer",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    job_past = JobSnapshot(
        source_job_id="job_exp_date_past",
        title="Civil Engineer",
        company="Infra Ltd",
        location="London",
        country_code="GB",
        application_url="https://example.com/jobs/2",
        source_status="active",
        verification_status="LIVE",
        published_at=now_utc - timedelta(days=5),
        closing_date=now_utc - timedelta(hours=1)  # Expired 1 hour ago
    )
    db.add(sub)
    db.add(job_past)
    await db.commit()

    campaign = await svc.create_and_generate_campaign(db=db, name="Test Past Date Campaign")
    assert campaign.emails_generated == 0
    assert campaign.total_queued == 0
    assert campaign.no_eligible_job_count == 1

@pytest.mark.asyncio
async def test_future_valid_job_eligible(test_session: AsyncSession):
    """Rule: Future-valid job with future closing_date is ELIGIBLE."""
    db = test_session
    svc = CampaignService()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    sub = SubscriberSnapshot(
        source_subscriber_id="sub_future_valid_1",
        name="David Test",
        email="david.test@example.com",
        preferred_roles="Data Analyst",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    job_valid = JobSnapshot(
        source_job_id="job_future_valid",
        title="Data Analyst",
        company="Analytics Corp",
        location="London",
        country_code="GB",
        application_url="https://example.com/jobs/3",
        source_status="active",
        verification_status="LIVE",
        published_at=now_utc - timedelta(days=1),
        closing_date=now_utc + timedelta(days=14)  # Closing in 14 days
    )
    db.add(sub)
    db.add(job_valid)
    await db.commit()

    campaign = await svc.create_and_generate_campaign(db=db, name="Test Future Valid Campaign")
    assert campaign.emails_generated == 1
    assert campaign.total_queued == 1

    q_item = (await db.execute(select(EmailQueueItem))).scalars().first()
    assert q_item.job_id == job_valid.id

@pytest.mark.asyncio
async def test_expiration_today_timestamp_logic(test_session: AsyncSession):
    """
    Rule 3: A job whose expiration date is TODAY must be treated according to exact timestamp:
    - If expiration timestamp has passed -> EXCLUDE.
    - If it has not yet passed -> ELIGIBLE.
    """
    db = test_session
    svc = CampaignService()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    sub1 = SubscriberSnapshot(
        source_subscriber_id="sub_today_passed",
        name="Passed Candidate",
        email="passed@example.com",
        preferred_roles="Product Manager",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    # Job closing earlier today (e.g., 30 minutes ago)
    job_passed_today = JobSnapshot(
        source_job_id="job_closed_earlier_today",
        title="Product Manager",
        company="Passed PM Corp",
        location="London",
        country_code="GB",
        application_url="https://example.com/jobs/4",
        source_status="active",
        verification_status="LIVE",
        published_at=now_utc - timedelta(days=1),
        closing_date=now_utc - timedelta(minutes=30)
    )

    sub2 = SubscriberSnapshot(
        source_subscriber_id="sub_today_future",
        name="Future Candidate",
        email="future@example.com",
        preferred_roles="DevOps Engineer",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    # Job closing later today (e.g., 4 hours in the future)
    job_future_today = JobSnapshot(
        source_job_id="job_closing_later_today",
        title="DevOps Engineer",
        company="Future DevOps Corp",
        location="London",
        country_code="GB",
        application_url="https://example.com/jobs/5",
        source_status="active",
        verification_status="LIVE",
        published_at=now_utc - timedelta(days=1),
        closing_date=now_utc + timedelta(hours=4)
    )

    db.add(sub1)
    db.add(job_passed_today)
    db.add(sub2)
    db.add(job_future_today)
    await db.commit()

    campaign = await svc.create_and_generate_campaign(db=db, name="Test Timestamp Exact Campaign")
    # sub1 should have 0 jobs (passed today -> excluded)
    # sub2 should have 1 job (future today -> eligible)
    assert campaign.total_candidates == 2
    assert campaign.emails_generated == 1
    assert campaign.total_queued == 1

    queued = (await db.execute(select(EmailQueueItem))).scalars().all()
    assert len(queued) == 1
    assert queued[0].subscriber_id == sub2.id
    assert queued[0].job_id == job_future_today.id

@pytest.mark.asyncio
async def test_all_roles_and_synonyms_with_expired_jobs(test_session: AsyncSession):
    """
    Rules 7 & 8:
    If all matching jobs for a subscriber are expired -> NO EMAIL.
    Applies to All Roles, direct, variant, synonym.
    """
    db = test_session
    svc = CampaignService()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    # All Roles subscriber
    sub_all = SubscriberSnapshot(
        source_subscriber_id="sub_all_roles_1",
        name="All Roles Candidate",
        email="allroles@example.com",
        preferred_roles="All Roles",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    # Only 1 job in entire DB, but it is expired
    job_expired_all = JobSnapshot(
        source_job_id="job_expired_for_all",
        title="General Assistant",
        company="Old Agency",
        location="London",
        country_code="GB",
        application_url="https://example.com/jobs/6",
        source_status="active",
        verification_status="LIVE",
        published_at=now_utc - timedelta(days=10),
        closing_date=now_utc - timedelta(days=1)
    )

    db.add(sub_all)
    db.add(job_expired_all)
    await db.commit()

    campaign = await svc.create_and_generate_campaign(db=db, name="Test All Roles Expired Campaign")
    assert campaign.total_candidates == 1
    assert campaign.emails_generated == 0
    assert campaign.total_queued == 0
    assert campaign.no_eligible_job_count == 1

def test_matching_engine_calculates_expired_as_not_relevant():
    """Verify MatchingEngine.calculate_match flags expired jobs as not relevant."""
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    candidate = SubscriberSnapshot(
        name="Emma Stone",
        email="emma@example.com",
        preferred_roles="Software Engineer",
        country_code="GB",
        subscription_status="active"
    )

    # Job with expired closing date
    job_expired_date = JobSnapshot(
        title="Software Engineer",
        country_code="GB",
        source_status="active",
        verification_status="LIVE",
        closing_date=now_utc - timedelta(hours=2)
    )
    score, details = matching_engine.calculate_match(candidate, job_expired_date)
    assert not details["is_relevant"]
    assert details["match_type"] == "NONE"
    assert "expired" in details["reasons"][0].lower()

    # Job with inactive source_status
    job_closed_status = JobSnapshot(
        title="Software Engineer",
        country_code="GB",
        source_status="closed",
        verification_status="LIVE"
    )
    score2, details2 = matching_engine.calculate_match(candidate, job_closed_status)
    assert not details2["is_relevant"]
    assert details2["match_type"] == "NONE"
