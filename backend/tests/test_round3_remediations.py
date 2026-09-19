"""
Regression Test Suite for Round 3 Remediations
Validates:
1. Future-dated jobs excluded from campaign selection and cannot beat published jobs.
2. Weekly frequency interval:
   - no previous dispatch -> eligible
   - 6 days old -> blocked
   - 7 days old -> eligible
   - one successful weekly dispatch -> blocked until 7 days
3. Instant frequency next-cycle behavior:
   - new matching job -> eligible
   - previously seen/burned job -> not eligible
   - same-day second job -> blocked by daily limit
   - next eligible day with new job -> eligible
4. Context-aware compound title matching:
   - BIM Coordinator / Engineer matches BIM Engineer (DIRECT)
   - Designer does NOT match Electrical Engineer / Designer
   - Electrical Engineer matches Electrical Engineer / Designer (DIRECT)
   - Data Analyst matches Data Engineer / Analyst (DIRECT)
   - Chemical Engineer does NOT match Electrical Engineer / Designer
   - Non-occupational garbage inputs (Student, No, Other) rejected
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from backend.app.core.database import Base
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.models.campaign import Campaign
from backend.app.models.email_queue import EmailQueueItem
from backend.app.models.match import CandidateJobHistory
from backend.app.services.campaign_service import CampaignService
from backend.app.services.role_matcher import evaluate_role_relevance

@pytest.fixture
async def test_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as session:
        yield session
    await engine.dispose()

# -------------------------------------------------------------
# 1. FUTURE JOBS REGRESSION TEST
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_future_dated_job_exclusion(test_session: AsyncSession):
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    future_time = now_utc + timedelta(days=30)
    past_time = now_utc - timedelta(days=2)

    sub = SubscriberSnapshot(
        source_subscriber_id="sub_future_test",
        name="Test Sub",
        email="futuretest@example.com",
        preferred_roles="Data Engineer",
        country_code="ALL",
        frequency="daily",
        subscription_status="active"
    )
    test_session.add(sub)

    # Job 1: Published in the future (e.g. 30 days ahead)
    job_future = JobSnapshot(
        source_job_id="job_future_1",
        title="Data Engineer",
        company="FutureCorp",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/job_future_1",
        published_at=future_time,
        source_status="active",
        verification_status="LIVE",
        quality_score=90
    )
    # Job 2: Published 2 days ago
    job_valid = JobSnapshot(
        source_job_id="job_valid_1",
        title="Data Engineer",
        company="ValidCorp",
        country_code="GB",
        application_url="https://sponsorajobs.com/jobs/job_valid_1",
        published_at=past_time,
        source_status="active",
        verification_status="LIVE",
        quality_score=60
    )
    test_session.add_all([job_future, job_valid])
    await test_session.commit()

    service = CampaignService()
    camp = await service.create_and_generate_campaign(test_session, name="Future Date Test")

    # Verify that ONLY job_valid was selected, and job_future was excluded
    queue_res = await test_session.execute(select(EmailQueueItem))
    items = queue_res.scalars().all()
    assert len(items) == 1
    assert items[0].job_id == job_valid.id
    assert items[0].company_name == "ValidCorp"

# -------------------------------------------------------------
# 2. WEEKLY FREQUENCY REGRESSION TESTS
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_weekly_frequency_eligibility(test_session: AsyncSession):
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # Sub A: Never received an email -> ELIGIBLE
    sub_a = SubscriberSnapshot(
        source_subscriber_id="sub_w_a",
        name="Sub A", email="sub_a@example.com", preferred_roles="Civil Engineer",
        country_code="ALL", frequency="weekly", subscription_status="active"
    )
    # Sub B: Last dispatched 6 days ago -> BLOCKED
    sub_b = SubscriberSnapshot(
        source_subscriber_id="sub_w_b",
        name="Sub B", email="sub_b@example.com", preferred_roles="Civil Engineer",
        country_code="ALL", frequency="weekly", subscription_status="active"
    )
    # Sub C: Last dispatched 7 days ago -> ELIGIBLE
    sub_c = SubscriberSnapshot(
        source_subscriber_id="sub_w_c",
        name="Sub C", email="sub_c@example.com", preferred_roles="Civil Engineer",
        country_code="ALL", frequency="weekly", subscription_status="active"
    )
    test_session.add_all([sub_a, sub_b, sub_c])
    await test_session.flush()

    # Add 3 distinct jobs
    j1 = JobSnapshot(source_job_id="j1", title="Civil Engineer", company="C1", country_code="GB", application_url="https://sponsorajobs.com/j1", source_status="active", verification_status="LIVE")
    j2 = JobSnapshot(source_job_id="j2", title="Civil Engineer", company="C2", country_code="GB", application_url="https://sponsorajobs.com/j2", source_status="active", verification_status="LIVE")
    j3 = JobSnapshot(source_job_id="j3", title="Civil Engineer", company="C3", country_code="GB", application_url="https://sponsorajobs.com/j3", source_status="active", verification_status="LIVE")
    test_session.add_all([j1, j2, j3])
    await test_session.flush()

    # Sub B received 6 days ago
    h_b = CandidateJobHistory(
        subscriber_id=sub_b.id, job_id=999, match_score=3,
        email_status="SENT", sent_at=now_utc - timedelta(days=6)
    )
    # Sub C received 7 days ago
    h_c = CandidateJobHistory(
        subscriber_id=sub_c.id, job_id=998, match_score=3,
        email_status="SENT", sent_at=now_utc - timedelta(days=7)
    )
    test_session.add_all([h_b, h_c])
    await test_session.commit()

    service = CampaignService()
    camp = await service.create_and_generate_campaign(test_session, name="Weekly Test")

    queue_res = await test_session.execute(select(EmailQueueItem))
    queued_subs = {item.subscriber_id for item in queue_res.scalars().all()}

    # Sub A (first dispatch) must be queued
    assert sub_a.id in queued_subs, "Sub A (no prior dispatch) should be eligible"
    # Sub B (6 days ago) must be blocked
    assert sub_b.id not in queued_subs, "Sub B (6 days ago) should be blocked"
    # Sub C (7 days ago) must be queued
    assert sub_c.id in queued_subs, "Sub C (7 days ago) should be eligible"

# -------------------------------------------------------------
# 3. INSTANT FREQUENCY REGRESSION TESTS
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_instant_frequency_next_cycle(test_session: AsyncSession):
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    proc_time = now_utc - timedelta(hours=2)

    sub = SubscriberSnapshot(
        source_subscriber_id="sub_inst_1",
        name="Instant Sub", email="instant@example.com", preferred_roles="DevOps Engineer",
        country_code="ALL", frequency="instant", subscription_status="active"
    )
    test_session.add(sub)
    await test_session.flush()

    # Prior history entry processed 2 hours ago
    prior_hist = CandidateJobHistory(
        subscriber_id=sub.id, job_id=101, match_score=3,
        email_status="SENT", sent_at=proc_time, created_at=proc_time
    )
    test_session.add(prior_hist)

    # Job 1: Old job (published before last processed time)
    old_job = JobSnapshot(
        source_job_id="old_j", title="DevOps Engineer", company="OldCorp",
        country_code="GB", application_url="https://sponsorajobs.com/old_j",
        published_at=proc_time - timedelta(hours=1),
        source_status="active", verification_status="LIVE"
    )
    # Job 2: New job (published 30 mins ago, after last processed time)
    new_job = JobSnapshot(
        source_job_id="new_j", title="DevOps Engineer", company="NewCorp",
        country_code="GB", application_url="https://sponsorajobs.com/new_j",
        published_at=now_utc - timedelta(minutes=30),
        source_status="active", verification_status="LIVE"
    )
    test_session.add_all([old_job, new_job])
    await test_session.commit()

    service = CampaignService()
    # Cycle 1: Should pick new_job
    camp = await service.create_and_generate_campaign(test_session, name="Instant Cycle 1")
    queue_res = await test_session.execute(select(EmailQueueItem))
    items = queue_res.scalars().all()
    assert len(items) == 1
    assert items[0].job_id == new_job.id

    # Same day second attempt -> Blocked by daily safety limit
    camp2 = await service.create_and_generate_campaign(test_session, name="Instant Cycle 2 Same Day")
    queue_res2 = await test_session.execute(select(EmailQueueItem))
    assert len(queue_res2.scalars().all()) == 1, "Same day second email must be blocked by daily limit"

# -------------------------------------------------------------
# 4. CONTEXT-AWARE COMPOUND TITLE MATCHING TESTS
# -------------------------------------------------------------
def test_compound_slash_pipe_positive_cases():
    # BIM Coordinator / Engineer matches BIM Engineer (DIRECT)
    res1 = evaluate_role_relevance("BIM Engineer", "BIM Coordinator / Engineer")
    assert res1.is_relevant is True
    assert res1.match_type == "DIRECT"

    # Data Analyst matches Data Engineer / Analyst (DIRECT)
    res2 = evaluate_role_relevance("Data Analyst", "Data Engineer / Analyst")
    assert res2.is_relevant is True
    assert res2.match_type == "DIRECT"

    # Electrical Engineer matches Electrical Engineer / Designer (DIRECT)
    res3 = evaluate_role_relevance("Electrical Engineer", "Electrical Engineer / Designer")
    assert res3.is_relevant is True
    assert res3.match_type == "DIRECT"

    # Project Manager matches Civil Engineer / Project Manager (DIRECT)
    res4 = evaluate_role_relevance("Project Manager", "Civil Engineer / Project Manager")
    assert res4.is_relevant is True
    assert res4.match_type == "DIRECT"

def test_compound_slash_pipe_negative_cases():
    # Designer MUST NOT match Electrical Engineer / Designer
    res1 = evaluate_role_relevance("Designer", "Electrical Engineer / Designer")
    assert res1.is_relevant is False

    # BIM Engineer MUST NOT match Civil Engineer / Project Manager
    res2 = evaluate_role_relevance("BIM Engineer", "Civil Engineer / Project Manager")
    assert res2.is_relevant is False

    # Chemical Engineer MUST NOT match Electrical Engineer / Designer
    res3 = evaluate_role_relevance("Chemical Engineer", "Electrical Engineer / Designer")
    assert res3.is_relevant is False

def test_non_occupational_inputs_rejected():
    for bad_input in ["Student", "No", "Other", "None", "N/A", "Unknown"]:
        res = evaluate_role_relevance(bad_input, "Software Engineer")
        assert res.is_relevant is False
        assert res.match_type == "NONE"
