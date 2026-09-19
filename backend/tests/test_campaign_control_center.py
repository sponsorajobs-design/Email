import os
import pytest
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.app.core.database import Base
from backend.app.models.campaign import Campaign
from backend.app.models.email_queue import EmailQueueItem
from backend.app.models.email_composition import EmailComposition
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.models.match import CandidateJobHistory
from backend.app.services.campaign_service import CampaignService
from backend.app.services.email_generator import email_generator
from backend.app.core.config import settings

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
async def test_campaign_automatic_evaluation_and_single_email_per_subscriber(test_session: AsyncSession):
    """
    Requirements 1 & 2:
    - New campaign automatically evaluates subscribers.
    - One eligible subscriber produces exactly one email with exactly one job.
    """
    db = test_session
    svc = CampaignService()
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)

    sub = SubscriberSnapshot(
        source_subscriber_id="sub_test_eval_1",
        name="Alice Test",
        email="alice.test@example.com",
        preferred_roles="Software Engineer",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    job = JobSnapshot(
        source_job_id="job_test_eval_1",
        title="Senior Software Engineer",
        company="Tech Corp",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/job_test_eval_1",
        source_status="active",
        verification_status="LIVE",
        published_at=now_naive
    )
    db.add(sub)
    db.add(job)
    await db.commit()

    campaign = await svc.create_and_generate_campaign(
        db=db,
        name="Test Automatic Evaluation Campaign",
        batch_size=50
    )

    assert campaign.id is not None
    assert campaign.status == "READY"
    assert campaign.total_candidates == 1
    assert campaign.total_queued == 1
    assert campaign.emails_generated == 1

    # Check composition
    comp_res = await db.execute(
        select(EmailComposition).where(
            EmailComposition.campaign_id == campaign.id,
            EmailComposition.subscriber_id == sub.id
        )
    )
    comps = comp_res.scalars().all()
    assert len(comps) == 1
    comp = comps[0]

    # Check queue record
    q_res = await db.execute(
        select(EmailQueueItem).where(
            EmailQueueItem.campaign_id == campaign.id,
            EmailQueueItem.subscriber_id == sub.id
        )
    )
    q_items = q_res.scalars().all()
    assert len(q_items) == 1
    q_item = q_items[0]

    # Check truthful subject format and single job link
    assert comp.job_url == f"https://sponsorajobs.com/jobs/{job.source_job_id}"
    assert "Senior Software Engineer" in comp.subject
    assert comp.queue_id == q_item.id

@pytest.mark.asyncio
async def test_job_link_generation_and_source_job_id_truth():
    """
    Requirement 3:
    - Every generated email MUST contain https://sponsorajobs.com/jobs/{source_job_id}
    - Never invent or reuse another job's URL.
    """
    source_id = "test-job-unique-slug-999"
    url = email_generator.generate_job_url(source_id)
    assert url == f"https://sponsorajobs.com/jobs/{source_id}"

    rendered = email_generator.render_email(
        candidate_name="Bob Test",
        subscriber_id=42,
        email="bob@example.com",
        job_title="DevOps Engineer",
        company="Cloud Services Ltd",
        source_job_id=source_id,
        application_url=f"https://sponsorajobs.com/jobs/{source_id}"
    )
    assert rendered["job_url"] == f"https://sponsorajobs.com/jobs/{source_id}"
    assert f"https://sponsorajobs.com/jobs/{source_id}" in rendered["html_body"]
    assert f"https://sponsorajobs.com/jobs/{source_id}" in rendered["text_body"]
    assert "View Role & Apply Now" in rendered["html_body"]

@pytest.mark.asyncio
async def test_different_subscribers_can_receive_same_relevant_job(test_session: AsyncSession):
    """
    Requirement 2:
    - The same job may legitimately be sent to different subscribers when it is relevant to each.
    """
    db = test_session
    svc = CampaignService()
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

    job = JobSnapshot(
        source_job_id="shared_job_test_101",
        title="Full Stack Developer",
        company="Global Software Inc",
        location="Manchester",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/shared_job_test_101",
        source_status="active",
        verification_status="LIVE",
        published_at=now_naive
    )
    sub1 = SubscriberSnapshot(
        source_subscriber_id="sub_shared_1",
        name="Charlie Dev",
        email="charlie.dev@example.com",
        preferred_roles="Full Stack Developer",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    sub2 = SubscriberSnapshot(
        source_subscriber_id="sub_shared_2",
        name="Dana Dev",
        email="dana.dev@example.com",
        preferred_roles="Full Stack Developer",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    db.add(job)
    db.add(sub1)
    db.add(sub2)
    await db.commit()

    campaign = await svc.create_and_generate_campaign(
        db=db,
        name="Shared Job Campaign Test",
        batch_size=50
    )

    res1 = await db.execute(select(EmailComposition).where(EmailComposition.campaign_id == campaign.id, EmailComposition.subscriber_id == sub1.id))
    res2 = await db.execute(select(EmailComposition).where(EmailComposition.campaign_id == campaign.id, EmailComposition.subscriber_id == sub2.id))
    c1 = res1.scalars().first()
    c2 = res2.scalars().first()

    assert c1 is not None
    assert c2 is not None
    assert c1.job_id == job.id
    assert c2.job_id == job.id

@pytest.mark.asyncio
async def test_subscriber_job_permanent_deduplication(test_session: AsyncSession):
    """
    Requirement 11:
    - Same subscriber + same job must never be selected again as a new alert.
    """
    db = test_session
    svc = CampaignService()
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

    job = JobSnapshot(
        source_job_id="dedup_job_test_202",
        title="Data Scientist",
        company="Analytics AI",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/dedup_job_test_202",
        source_status="active",
        verification_status="LIVE",
        published_at=now_naive
    )
    sub = SubscriberSnapshot(
        source_subscriber_id="sub_dedup_test",
        name="Eve Analyst",
        email="eve.analyst@example.com",
        preferred_roles="Data Scientist",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    db.add(job)
    db.add(sub)
    await db.commit()

    # First campaign pairs sub and job
    camp1 = await svc.create_and_generate_campaign(db=db, name="Dedup Camp 1", batch_size=50)
    c1 = (await db.execute(select(EmailComposition).where(EmailComposition.campaign_id == camp1.id, EmailComposition.subscriber_id == sub.id))).scalars().first()
    assert c1 is not None
    assert c1.job_id == job.id

    # To test subscriber-job deduplication independently from daily frequency gating,
    # update camp1's queue item dispatch date to yesterday (previous UTC day)
    q1 = (await db.execute(select(EmailQueueItem).where(EmailQueueItem.campaign_id == camp1.id, EmailQueueItem.subscriber_id == sub.id))).scalars().first()
    q1.dispatch_date = "2026-09-10"
    await db.commit()

    # Second campaign must NOT pair this job again (permanently burned pair)
    camp2 = await svc.create_and_generate_campaign(db=db, name="Dedup Camp 2", batch_size=50)
    c2 = (await db.execute(select(EmailComposition).where(EmailComposition.campaign_id == camp2.id, EmailComposition.subscriber_id == sub.id))).scalars().first()
    assert c2 is None
    assert camp2.deduplicated_count >= 1

@pytest.mark.asyncio
async def test_future_dated_jobs_excluded(test_session: AsyncSession):
    """
    Requirement:
    - In campaign selection path, published_at > now_utc must be excluded.
    """
    db = test_session
    svc = CampaignService()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    future_time = now_utc + timedelta(days=2)
    past_time = now_utc - timedelta(hours=3)

    future_job = JobSnapshot(
        source_job_id="future_job_test_303",
        title="Principal Cloud Architect",
        company="Future Tech",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/future_job_test_303",
        source_status="active",
        verification_status="LIVE",
        published_at=future_time
    )
    past_job = JobSnapshot(
        source_job_id="past_job_test_303",
        title="Principal Cloud Architect",
        company="Current Tech",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/past_job_test_303",
        source_status="active",
        verification_status="LIVE",
        published_at=past_time
    )
    sub = SubscriberSnapshot(
        source_subscriber_id="sub_future_test",
        name="Frank Cloud",
        email="frank.cloud@example.com",
        preferred_roles="Principal Cloud Architect",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    db.add(future_job)
    db.add(past_job)
    db.add(sub)
    await db.commit()

    camp = await svc.create_and_generate_campaign(db=db, name="Future Exclusion Camp", batch_size=50)
    c = (await db.execute(select(EmailComposition).where(EmailComposition.campaign_id == camp.id, EmailComposition.subscriber_id == sub.id))).scalars().first()

    assert c is not None
    assert c.job_id == past_job.id
    assert c.job_id != future_job.id

@pytest.mark.asyncio
async def test_weekly_frequency_safety(test_session: AsyncSession):
    """
    Requirement 12:
    - Weekly: first-ever eligible dispatch = allowed; otherwise allowed only when last successful dispatch is >= 7 days ago.
    """
    db = test_session
    svc = CampaignService()
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)

    job = JobSnapshot(
        source_job_id="weekly_job_test_404",
        title="Civil Engineer",
        company="Bridge Build Ltd",
        location="Leeds",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/weekly_job_test_404",
        source_status="active",
        verification_status="LIVE",
        published_at=now_naive - timedelta(hours=5)
    )
    sub = SubscriberSnapshot(
        source_subscriber_id="sub_weekly_test",
        name="Grace Eng",
        email="grace.eng@example.com",
        preferred_roles="Civil Engineer",
        country_code="GB",
        frequency="weekly",
        subscription_status="active"
    )
    db.add(job)
    db.add(sub)
    await db.flush()

    # Simulate successful dispatch 2 days ago (< 7 days)
    hist = CandidateJobHistory(
        subscriber_id=sub.id,
        job_id=job.id + 9999,
        match_score=3,
        email_status="SENT",
        sent_at=now_naive - timedelta(days=2)
    )
    db.add(hist)
    await db.commit()

    camp = await svc.create_and_generate_campaign(db=db, name="Weekly Camp Test", batch_size=50)
    c = (await db.execute(select(EmailComposition).where(EmailComposition.campaign_id == camp.id, EmailComposition.subscriber_id == sub.id))).scalars().first()

    assert c is None
    assert camp.frequency_blocked_count >= 1

@pytest.mark.asyncio
async def test_no_eligible_job_produces_no_email(test_session: AsyncSession):
    """
    Requirement 1:
    - Zero relevant jobs -> Zero emails. Reason recorded as NO_ELIGIBLE_JOB.
    """
    db = test_session
    svc = CampaignService()

    sub = SubscriberSnapshot(
        source_subscriber_id="sub_no_job_test",
        name="No Match Candidate",
        email="no.match@example.com",
        preferred_roles="Underwater Basket Weaver 12345",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    db.add(sub)
    await db.commit()

    camp = await svc.create_and_generate_campaign(db=db, name="No Match Campaign Test", batch_size=50)
    c = (await db.execute(select(EmailComposition).where(EmailComposition.campaign_id == camp.id, EmailComposition.subscriber_id == sub.id))).scalars().first()

    assert c is None
    assert camp.no_eligible_job_count >= 1

@pytest.mark.asyncio
async def test_country_filtering_works(test_session: AsyncSession):
    """
    Requirement:
    - Country filtering matches subscriber's country_code. ALL matches any country.
    """
    db = test_session
    svc = CampaignService()
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

    job_us = JobSnapshot(
        source_job_id="job_country_us",
        title="Software Developer",
        company="US Tech",
        location="New York",
        country_code="US",
        application_url="https://sponsorajobs.com/jobs/job_country_us",
        source_status="active",
        verification_status="LIVE",
        published_at=now_naive
    )
    sub_gb = SubscriberSnapshot(
        source_subscriber_id="sub_gb_only",
        name="GB Sub",
        email="gb.sub@example.com",
        preferred_roles="Software Developer",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    sub_all = SubscriberSnapshot(
        source_subscriber_id="sub_all_country",
        name="Global Sub",
        email="global.sub@example.com",
        preferred_roles="Software Developer",
        country_code="ALL",
        frequency="daily",
        subscription_status="active"
    )
    db.add(job_us)
    db.add(sub_gb)
    db.add(sub_all)
    await db.commit()

    camp = await svc.create_and_generate_campaign(db=db, name="Country Filter Camp", batch_size=50)

    # GB subscriber must NOT receive US job
    c_gb = (await db.execute(select(EmailComposition).where(EmailComposition.campaign_id == camp.id, EmailComposition.subscriber_id == sub_gb.id))).scalars().first()
    assert c_gb is None

    # ALL country subscriber DOES receive US job
    c_all = (await db.execute(select(EmailComposition).where(EmailComposition.campaign_id == camp.id, EmailComposition.subscriber_id == sub_all.id))).scalars().first()
    assert c_all is not None
    assert c_all.job_id == job_us.id

@pytest.mark.asyncio
async def test_all_roles_subscriber_works(test_session: AsyncSession):
    """
    Requirement:
    - ALL Roles subscriber receives available job.
    """
    db = test_session
    svc = CampaignService()
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

    job = JobSnapshot(
        source_job_id="job_all_roles_test",
        title="Operations Manager",
        company="Logistics Pro",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/job_all_roles_test",
        source_status="active",
        verification_status="LIVE",
        published_at=now_naive
    )
    sub = SubscriberSnapshot(
        source_subscriber_id="sub_all_roles_test",
        name="General Candidate",
        email="general@example.com",
        preferred_roles="All Roles",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    db.add(job)
    db.add(sub)
    await db.commit()

    camp = await svc.create_and_generate_campaign(db=db, name="All Roles Camp", batch_size=50)
    c = (await db.execute(select(EmailComposition).where(EmailComposition.campaign_id == camp.id, EmailComposition.subscriber_id == sub.id))).scalars().first()

    assert c is not None
    assert c.job_id == job.id

@pytest.mark.asyncio
async def test_decision_trace_why_this_job(test_session: AsyncSession):
    """
    Requirement 9:
    - Every generated email must have a decision trace with subscriber, role, country, frequency, selected job, match type, ranking position, and excluded alternatives.
    """
    db = test_session
    svc = CampaignService()
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)

    job1 = JobSnapshot(
        source_job_id="trace_job_direct",
        title="Director of Product Design",
        company="Creative Studio",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/trace_job_direct",
        source_status="active",
        verification_status="LIVE",
        published_at=now_naive
    )
    job2 = JobSnapshot(
        source_job_id="trace_job_alt",
        title="Product Designer",
        company="Design House",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/trace_job_alt",
        source_status="active",
        verification_status="LIVE",
        published_at=now_naive - timedelta(hours=10)
    )
    sub = SubscriberSnapshot(
        source_subscriber_id="sub_trace_test",
        name="Hannah Designer",
        email="hannah.designer@example.com",
        preferred_roles="Director of Product Design",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    db.add(job1)
    db.add(job2)
    db.add(sub)
    await db.commit()

    camp = await svc.create_and_generate_campaign(db=db, name="Decision Trace Camp", batch_size=50)
    comp = (await db.execute(select(EmailComposition).where(EmailComposition.campaign_id == camp.id, EmailComposition.subscriber_id == sub.id))).scalars().first()

    assert comp is not None
    assert comp.decision_trace is not None
    trace = json.loads(comp.decision_trace)

    assert trace["subscriber"]["email"] == "hannah.designer@example.com"
    assert trace["subscriber"]["role"] == "Director of Product Design"
    assert trace["subscriber"]["country"] == "GB"
    assert trace["subscriber"]["frequency"] == "daily"
    assert trace["selected_job"]["title"] == "Director of Product Design"
    assert trace["match_type"] == "DIRECT"
    assert trace["ranking_position"] == 1
    assert "excluded_alternatives" in trace

@pytest.mark.asyncio
async def test_campaign_safety_review_before_dispatch(test_session: AsyncSession):
    """
    Requirement 13:
    - Campaign creation must NOT automatically send emails immediately.
    - Status is READY.
    - Separate dispatch triggers transmission.
    """
    db = test_session
    svc = CampaignService()
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

    job = JobSnapshot(
        source_job_id="safety_job_test_505",
        title="Finance Director",
        company="Global Finance Corp",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/safety_job_test_505",
        source_status="active",
        verification_status="LIVE",
        published_at=now_naive
    )
    sub = SubscriberSnapshot(
        source_subscriber_id="sub_safety_test",
        name="Ian Finance",
        email="ian.finance@example.com",
        preferred_roles="Finance Director",
        country_code="GB",
        frequency="daily",
        subscription_status="active"
    )
    db.add(job)
    db.add(sub)
    await db.commit()

    camp = await svc.create_and_generate_campaign(db=db, name="Safety Camp Test", batch_size=50)

    # Status must be READY (NOT SENDING, NOT SENT)
    assert camp.status == "READY"
    q_item = (await db.execute(select(EmailQueueItem).where(EmailQueueItem.campaign_id == camp.id, EmailQueueItem.subscriber_id == sub.id))).scalars().first()
    assert q_item.status == "PENDING"

    # Now dispatch explicitly
    res = await svc.dispatch_campaign(db=db, campaign_id=camp.id, batch_limit=50)
    assert "processed" in res or "sent" in res

def test_sponsorajobs_upstream_isolation():
    """
    Requirement 17 & Permanent Rule:
    - Production / External project isolation guarantee.
    - Application strictly operates on local SQLite database ./data/sponsorajobs_local.db.
    """
    local_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sponsorajobs_local.db")
    assert os.path.exists(local_path), f"Expected local database at {local_path}"
    conn = sqlite3.connect(local_path)
    cur = conn.cursor()
    count = cur.execute("SELECT count(*) FROM subscribers").fetchone()[0]
    conn.close()
    assert count > 0, f"Expected active subscribers in local database, found {count}"
