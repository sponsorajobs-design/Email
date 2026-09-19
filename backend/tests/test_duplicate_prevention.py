import pytest
from backend.app.models.match import CandidateJobHistory
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.models.match import CandidateJobMatch
from backend.app.services.campaign_service import campaign_service
from sqlalchemy import select

@pytest.mark.asyncio
async def test_duplicate_prevention_in_campaign(test_db):
    # Setup candidate & job
    candidate = SubscriberSnapshot(
        source_subscriber_id="sub-1",
        name="John Doe",
        email="john@example.com",
        subscription_status="active",
        is_unsubscribed=False
    )
    job = JobSnapshot(
        source_job_id="job-1",
        title="Software Engineer",
        company="TechCorp",
        application_url="https://example.com",
        source_status="active",
        verification_status="LIVE"
    )
    test_db.add(candidate)
    test_db.add(job)
    await test_db.flush()

    # Pre-record history indicating this candidate already received this job
    history = CandidateJobHistory(
        subscriber_id=candidate.id,
        job_id=job.id,
        match_score=90,
        email_status="SENT"
    )
    match = CandidateJobMatch(
        subscriber_id=candidate.id,
        job_id=job.id,
        match_score=90
    )
    test_db.add(history)
    test_db.add(match)
    await test_db.commit()

    # Generate campaign
    campaign = await campaign_service.create_and_generate_campaign(
        db=test_db,
        name="Test Dup Campaign",
        match_threshold=70,
        batch_size=10
    )

    # Should have queued 0 emails because the candidate-job pair is already in history
    assert campaign.total_queued == 0
    assert campaign.total_skipped >= 1
