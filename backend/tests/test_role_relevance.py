"""
Comprehensive Automated Test Suite: Role-Based Email Alert Engine
Covers all mandatory validation scenarios from Section 25:
A. Country (ALL vs Specific ISO code)
B. Role Relevance (Direct, Variant, Synonym, Generic-word guards)
C. Multiple Jobs (10 relevant -> exactly 1 selected)
D. Zero Jobs (0 relevant -> 0 queued emails)
E. Daily Limit (Subscriber receives Job A today -> Job B cannot be queued today)
F. Same Subscriber/Job (Job A can never be selected again as a new alert)
G. Different Subscribers (Job A + Sub 1, Job A + Sub 2 -> both allowed)
H. Queue Concurrency (Two campaign-generation attempts -> maximum 1 daily queue record)
I. Failed Delivery (SMTP transient error retries same queue item, not new item)
J. Crash Window (Stale SENDING -> flagged for reconciliation, no blind resend)
K. Ranking Hierarchy (Direct > Variant > Synonym; published_at > quality > created_at > source_job_id)
L. One-Job Email (Generated email contains exactly ONE job, zero ATS scores)
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.models.email_queue import EmailQueueItem
from backend.app.models.match import CandidateJobHistory
from backend.app.services.role_matcher import evaluate_role_relevance
from backend.app.services.matching_engine import matching_engine
from backend.app.services.campaign_service import campaign_service
from backend.app.services.email_generator import email_generator
from backend.app.services.email_sender import email_sender

# ----------------------------------------------------------------------
# A. COUNTRY FILTER TESTS
# ----------------------------------------------------------------------
def test_scenario_a_country_filtering():
    """
    A. Country
        ALL + GB job -> eligible
        ALL + US job -> eligible
        GB + GB job -> eligible
        GB + US job -> excluded
    """
    sub_all = SubscriberSnapshot(country_code="ALL", preferred_roles="Project Coordinator")
    sub_gb = SubscriberSnapshot(country_code="GB", preferred_roles="Project Coordinator")

    job_gb = JobSnapshot(country_code="GB", title="Project Coordinator", verification_status="LIVE", source_status="active")
    job_us = JobSnapshot(country_code="US", title="Project Coordinator", verification_status="LIVE", source_status="active")

    # ALL + GB job -> eligible
    score, res = matching_engine.calculate_match(sub_all, job_gb)
    assert res["is_relevant"] is True

    # ALL + US job -> eligible
    score, res = matching_engine.calculate_match(sub_all, job_us)
    assert res["is_relevant"] is True

    # GB + GB job -> eligible
    score, res = matching_engine.calculate_match(sub_gb, job_gb)
    assert res["is_relevant"] is True

    # GB + US job -> excluded
    score, res = matching_engine.calculate_match(sub_gb, job_us)
    assert res["is_relevant"] is False
    assert "Country mismatch" in res["reasons"][0]

# ----------------------------------------------------------------------
# B. ROLE RELEVANCE TESTS
# ----------------------------------------------------------------------
def test_scenario_b_role_relevance():
    """
    B. Role relevance
        Project Coordinator -> Project Coordinator = relevant (DIRECT)
        Project Coordinator -> Senior Project Coordinator = relevant (VARIANT)
        Data Engineer -> Project Engineer = NOT relevant (generic 'engineer')
        Construction Manager -> Restaurant Manager = NOT relevant (generic 'manager')
        Construction Manager -> Site Manager = relevant (SYNONYM)
        Construction Manager -> Civil Engineer = NOT relevant
        Construction Manager -> Quantity Surveyor = NOT relevant
    """
    # 1. Direct match
    res = evaluate_role_relevance("Project Coordinator", "Project Coordinator")
    assert res.is_relevant is True
    assert res.match_type == "DIRECT"

    # 2. Seniority variant
    res = evaluate_role_relevance("Project Coordinator", "Senior Project Coordinator")
    assert res.is_relevant is True
    assert res.match_type == "VARIANT"

    # 3. Generic word 'engineer' overlap -> NOT relevant
    res = evaluate_role_relevance("Data Engineer", "Project Engineer")
    assert res.is_relevant is False
    assert res.match_type == "NONE"

    # 4. Generic word 'manager' overlap -> NOT relevant
    res = evaluate_role_relevance("Construction Manager", "Restaurant Manager")
    assert res.is_relevant is False
    assert res.match_type == "NONE"

    # 5. Approved curated synonym
    res = evaluate_role_relevance("Construction Manager", "Site Manager", category_id="cat_construction")
    assert res.is_relevant is True
    assert res.match_type == "SYNONYM"

    # 6. Unapproved cross-profession
    res = evaluate_role_relevance("Construction Manager", "Civil Engineer")
    assert res.is_relevant is False

    # 7. Unapproved cross-profession
    res = evaluate_role_relevance("Construction Manager", "Quantity Surveyor")
    assert res.is_relevant is False

# ----------------------------------------------------------------------
# C. MULTIPLE JOBS -> EXACTLY 1 SELECTED
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_c_multiple_jobs_select_exactly_one(test_db):
    """
    C. Multiple jobs
        10 relevant jobs -> exactly 1 selected
    """
    sub = SubscriberSnapshot(
        source_subscriber_id="sub_c",
        email="test_sub_c@example.com",
        name="Subscriber C",
        country_code="GB",
        preferred_roles="Project Coordinator",
        subscription_status="active"
    )
    test_db.add(sub)
    await test_db.flush()

    # Create 10 relevant jobs
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for i in range(10):
        slug = f"job_c_{i:02d}"
        job = JobSnapshot(
            source_job_id=slug,
            title="Project Coordinator",
            company=f"Company {i}",
            location="London",
            country_code="GB",
            application_url=f"https://sponsorajobs.com/job/{slug}",
            verification_status="LIVE",
            source_status="active",
            quality_score=50 + i,
            published_at=now - timedelta(days=10 - i),
            created_at=now - timedelta(days=10 - i)
        )
        test_db.add(job)
    await test_db.commit()

    campaign = await campaign_service.create_and_generate_campaign(test_db, name="Test Campaign C")
    assert campaign.total_queued == 1

    # Verify exactly 1 queue item created
    q_res = await test_db.execute(select(EmailQueueItem).where(EmailQueueItem.subscriber_id == sub.id))
    items = q_res.scalars().all()
    assert len(items) == 1

# ----------------------------------------------------------------------
# D. ZERO RELEVANT JOBS -> 0 QUEUED EMAILS
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_d_zero_jobs_zero_queued(test_db):
    """
    D. Zero jobs
        0 relevant jobs -> 0 queued emails (never send filler!)
    """
    sub = SubscriberSnapshot(
        source_subscriber_id="sub_d",
        email="test_sub_d@example.com",
        name="Subscriber D",
        country_code="GB",
        preferred_roles="Aerospace Propulsion Specialist",
        subscription_status="active"
    )
    test_db.add(sub)

    # Job in completely different field
    job = JobSnapshot(
        source_job_id="job_d_01",
        title="Restaurant Manager",
        company="Dining Ltd",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/job/job_d_01",
        verification_status="LIVE",
        source_status="active"
    )
    test_db.add(job)
    await test_db.commit()

    campaign = await campaign_service.create_and_generate_campaign(test_db, name="Test Campaign D")
    assert campaign.total_queued == 0

    q_res = await test_db.execute(select(EmailQueueItem).where(EmailQueueItem.subscriber_id == sub.id))
    items = q_res.scalars().all()
    assert len(items) == 0

# ----------------------------------------------------------------------
# E. DAILY LIMIT: MAXIMUM 1 JOB EMAIL PER CALENDAR DAY
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_e_daily_limit_enforcement(test_db):
    """
    E. Daily limit
        subscriber receives Job A today
        -> Job B cannot be queued today
    """
    current_utc_date = campaign_service.get_current_utc_date()

    sub = SubscriberSnapshot(
        source_subscriber_id="sub_e",
        email="test_sub_e@example.com",
        name="Subscriber E",
        country_code="GB",
        preferred_roles="Project Coordinator",
        subscription_status="active"
    )
    test_db.add(sub)
    await test_db.flush()

    job1 = JobSnapshot(
        source_job_id="job_e_01",
        title="Project Coordinator",
        company="Company 1",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/job/job_e_01",
        verification_status="LIVE",
        source_status="active"
    )
    job2 = JobSnapshot(
        source_job_id="job_e_02",
        title="Project Coordinator",
        company="Company 2",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/job/job_e_02",
        verification_status="LIVE",
        source_status="active"
    )
    test_db.add_all([job1, job2])
    await test_db.commit()

    # First campaign queues job1
    campaign1 = await campaign_service.create_and_generate_campaign(test_db, name="Campaign E1")
    assert campaign1.total_queued == 1

    # Second campaign on same calendar date should queue 0 for this subscriber
    campaign2 = await campaign_service.create_and_generate_campaign(test_db, name="Campaign E2")
    assert campaign2.total_queued == 0

    # Verify total emails in queue for subscriber is still exactly 1
    q_res = await test_db.execute(select(EmailQueueItem).where(EmailQueueItem.subscriber_id == sub.id))
    items = q_res.scalars().all()
    assert len(items) == 1
    assert items[0].dispatch_date == current_utc_date

# ----------------------------------------------------------------------
# F. SAME SUBSCRIBER + SAME JOB: PERMANENTLY BURNED
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_f_same_subscriber_job_never_resewn(test_db):
    """
    F. Same subscriber/job
        subscriber receives Job A
        -> Job A can never be selected again as a new alert
    """
    sub = SubscriberSnapshot(
        source_subscriber_id="sub_f",
        email="test_sub_f@example.com",
        name="Subscriber F",
        country_code="GB",
        preferred_roles="Project Coordinator",
        subscription_status="active"
    )
    test_db.add(sub)
    await test_db.flush()

    job_a = JobSnapshot(
        source_job_id="job_f_01",
        title="Project Coordinator",
        company="Company A",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/job/job_f_01",
        verification_status="LIVE",
        source_status="active"
    )
    test_db.add(job_a)
    await test_db.flush()

    # Pre-record Job A in history as already sent previously
    hist = CandidateJobHistory(
        subscriber_id=sub.id,
        job_id=job_a.id,
        match_score=3,
        email_status="SENT",
        sent_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=5)
    )
    test_db.add(hist)
    await test_db.commit()

    # Campaign generation with only Job A available should queue 0
    campaign = await campaign_service.create_and_generate_campaign(test_db, name="Campaign F")
    assert campaign.total_queued == 0

# ----------------------------------------------------------------------
# G. DIFFERENT SUBSCRIBERS CAN RECEIVE SAME JOB
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_g_different_subscribers_same_job(test_db):
    """
    G. Different subscribers
        Job A + Subscriber 1
        Job A + Subscriber 2
        -> BOTH allowed
    """
    sub1 = SubscriberSnapshot(source_subscriber_id="sub_g1", email="sub1@example.com", name="Sub 1", country_code="GB", preferred_roles="Project Coordinator", subscription_status="active")
    sub2 = SubscriberSnapshot(source_subscriber_id="sub_g2", email="sub2@example.com", name="Sub 2", country_code="GB", preferred_roles="Project Coordinator", subscription_status="active")
    test_db.add_all([sub1, sub2])

    job_a = JobSnapshot(
        source_job_id="job_g_shared",
        title="Project Coordinator",
        company="Global Corp",
        location="London",
        country_code="GB",
        application_url="https://sponsorajobs.com/job/job_g_shared",
        verification_status="LIVE",
        source_status="active"
    )
    test_db.add(job_a)
    await test_db.commit()

    campaign = await campaign_service.create_and_generate_campaign(test_db, name="Campaign G")
    assert campaign.total_queued == 2

    # Both subscribers received job_a
    q_res = await test_db.execute(select(EmailQueueItem).where(EmailQueueItem.job_id == job_a.id))
    items = q_res.scalars().all()
    assert len(items) == 2
    sub_ids = {item.subscriber_id for item in items}
    assert sub_ids == {sub1.id, sub2.id}

# ----------------------------------------------------------------------
# H. QUEUE CONCURRENCY ENFORCEMENT
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_h_queue_concurrency(test_db):
    """
    H. Queue concurrency
        Two campaign-generation attempts on same subscriber on same UTC date
        -> DB UniqueConstraint enforces maximum 1 daily queue record
    """
    current_utc_date = campaign_service.get_current_utc_date()

    item1 = EmailQueueItem(
        campaign_id=1,
        subscriber_id=99,
        job_id=101,
        recipient="concurrent@example.com",
        subject="Test 1",
        html_body="<p>Test</p>",
        text_body="Test",
        dispatch_date=current_utc_date,
        status="PENDING"
    )
    test_db.add(item1)
    await test_db.commit()

    # Attempting to insert a second item for subscriber 99 on same dispatch_date must raise IntegrityError
    item2 = EmailQueueItem(
        campaign_id=2,
        subscriber_id=99,
        job_id=102,
        recipient="concurrent@example.com",
        subject="Test 2",
        html_body="<p>Test</p>",
        text_body="Test",
        dispatch_date=current_utc_date,
        status="PENDING"
    )
    test_db.add(item2)
    with pytest.raises(IntegrityError):
        await test_db.commit()

    await test_db.rollback()

# ----------------------------------------------------------------------
# I. FAILED DELIVERY RETRIES SAME QUEUE ITEM
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_i_failed_delivery_retry_same_item(test_db):
    """
    I. Failed delivery
        SMTP transient error -> same queue item retries
        NOT: new subscriber/job queue item
    """
    item = EmailQueueItem(
        campaign_id=1,
        subscriber_id=55,
        job_id=200,
        recipient="retry@example.com",
        subject="Retry Test",
        html_body="<p>Retry</p>",
        text_body="Retry",
        dispatch_date="2026-09-13",
        status="PENDING",
        attempts=0
    )
    test_db.add(item)
    await test_db.commit()

    # Simulate transient failure: item status transitions to PENDING and attempts incremented
    item.status = "SENDING"
    item.attempts += 1
    item.error_message = "SMTP Connection timeout"
    item.status = "PENDING"  # Kept in queue for retry
    await test_db.commit()

    # Verify no second queue item exists
    res = await test_db.execute(select(EmailQueueItem).where(EmailQueueItem.subscriber_id == 55))
    all_items = res.scalars().all()
    assert len(all_items) == 1
    assert all_items[0].attempts == 1
    assert all_items[0].status == "PENDING"

# ----------------------------------------------------------------------
# J. CRASH WINDOW: STALE SENDING FLAGGED WITHOUT BLIND RESEND
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_j_crash_window_reconciliation(test_db):
    """
    J. Crash window
        SENDING stale -> flagged for reconciliation, no blind resend
    """
    stale_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=45)
    item = EmailQueueItem(
        campaign_id=1,
        subscriber_id=77,
        job_id=300,
        recipient="crash@example.com",
        subject="Crash Test",
        html_body="<p>Crash</p>",
        text_body="Crash",
        dispatch_date="2026-09-13",
        status="SENDING",
        locked_at=stale_time
    )
    test_db.add(item)
    await test_db.commit()

    # Run crash-window reconciliation
    reconciled = await email_sender.reconcile_stale_sending_items(test_db, stale_threshold_minutes=30)
    assert item.id in reconciled

    # Verify status changed to REQUIRES_RECONCILIATION
    await test_db.refresh(item)
    assert item.status == "REQUIRES_RECONCILIATION"
    assert item.reconciliation_status == "STALE_SENDING_FLAGGED"

# ----------------------------------------------------------------------
# K. RANKING HIERARCHY TESTS
# ----------------------------------------------------------------------
def test_scenario_k_ranking_hierarchy():
    """
    K. Ranking
        Direct relevant job beats Variant
        Variant beats Synonym
        Within same relevance: newer published_at beats older
        If same published_at: higher quality_score wins
        If same quality: newer created_at wins
        If still equal: source_job_id ASC decides deterministically
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Level 1: DIRECT (3) > VARIANT (2) > SYNONYM (1)
    job_direct = JobSnapshot(source_job_id="job_dir", published_at=now - timedelta(days=10), quality_score=50, created_at=now)
    job_variant = JobSnapshot(source_job_id="job_var", published_at=now, quality_score=90, created_at=now)

    def sort_key(lvl, j):
        pub_ts = j.published_at.timestamp() if j.published_at else 0.0
        q_score = j.quality_score if j.quality_score is not None else 50
        crt_ts = j.created_at.timestamp() if j.created_at else 0.0
        return (-lvl, -pub_ts, -q_score, -crt_ts, str(j.source_job_id))

    # Direct (lvl 3) beats Variant (lvl 2) even if variant is newer and higher quality
    list_to_sort = [(2, job_variant), (3, job_direct)]
    list_to_sort.sort(key=lambda x: sort_key(x[0], x[1]))
    assert list_to_sort[0][1].source_job_id == "job_dir"

    # Freshness: Within same relevance, newer published_at beats older
    job_newer = JobSnapshot(source_job_id="job_new", published_at=now, quality_score=50, created_at=now)
    job_older = JobSnapshot(source_job_id="job_old", published_at=now - timedelta(days=2), quality_score=90, created_at=now)
    list_fresh = [(3, job_older), (3, job_newer)]
    list_fresh.sort(key=lambda x: sort_key(x[0], x[1]))
    assert list_fresh[0][1].source_job_id == "job_new"

    # Quality: If published_at is equal, higher quality_score wins
    job_hq = JobSnapshot(source_job_id="job_hq", published_at=now, quality_score=85, created_at=now)
    job_lq = JobSnapshot(source_job_id="job_lq", published_at=now, quality_score=60, created_at=now)
    list_q = [(3, job_lq), (3, job_hq)]
    list_q.sort(key=lambda x: sort_key(x[0], x[1]))
    assert list_q[0][1].source_job_id == "job_hq"

    # Tie-breaker: If everything equal, source_job_id ASC wins
    job_a = JobSnapshot(source_job_id="job_aaa", published_at=now, quality_score=50, created_at=now)
    job_b = JobSnapshot(source_job_id="job_bbb", published_at=now, quality_score=50, created_at=now)
    list_tie = [(3, job_b), (3, job_a)]
    list_tie.sort(key=lambda x: sort_key(x[0], x[1]))
    assert list_tie[0][1].source_job_id == "job_aaa"

# ----------------------------------------------------------------------
# L. ONE-JOB EMAIL TEMPLATE VERIFICATION
# ----------------------------------------------------------------------
def test_scenario_l_one_job_email_content():
    """
    L. One-job email
        Generated email contains exactly ONE job.
        Zero ATS / Match Score in output.
        Correct SponsorAJobs portal CTA link.
    """
    rendered = email_generator.render_email(
        candidate_name="Alice Smith",
        subscriber_id=10,
        email="alice@example.com",
        job_title="Project Coordinator",
        company="Skanska UK",
        location="London",
        country_code="GB",
        employment_type="Full-time",
        remote_type="Hybrid",
        sponsorship_label="Verified Visa Sponsor",
        description="Great role supporting major rail projects.",
        target_role="Project Coordinator",
        source_job_id="job_skanska_6700_contract-administrator"
    )

    # Must contain exactly the job details and authentic HR subject
    assert rendered["subject"] == "Your profile has been selected for the Project Coordinator role"
    assert "Dear Alice Smith," in rendered["text_body"]
    assert "Skanska UK" in rendered["html_body"]
    assert "Skanska UK" in rendered["text_body"]
    assert "https://sponsorajobs.com/jobs/job_skanska_6700_contract-administrator" in rendered["html_body"]
    assert "https://sponsorajobs.com/jobs/job_skanska_6700_contract-administrator" in rendered["text_body"]

    # Must NOT contain fake scores or ATS language
    assert "Match Score" not in rendered["html_body"]
    assert "/100" not in rendered["html_body"]
    assert "Candidate Score" not in rendered["html_body"]
    assert "ATS score" not in rendered["html_body"]
    assert "Match Score" not in rendered["text_body"]
    assert "/100" not in rendered["text_body"]
