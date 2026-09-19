import pytest
from backend.app.core.security import generate_unsubscribe_token
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.models.match import CandidateJobMatch
from backend.app.models.unsubscribe import Unsubscribe
from backend.app.services.campaign_service import campaign_service

def test_unsubscribe_token_deterministic():
    token1 = generate_unsubscribe_token(123, "user@example.com")
    token2 = generate_unsubscribe_token(123, "user@example.com")
    assert token1 == token2
    assert len(token1) == 32

@pytest.mark.asyncio
async def test_unsubscribed_candidate_excluded(test_db):
    candidate = SubscriberSnapshot(
        source_subscriber_id="sub-2",
        name="Unsub Candidate",
        email="unsub@example.com",
        subscription_status="active",
        is_unsubscribed=True  # Opted out
    )
    job = JobSnapshot(
        source_job_id="job-2",
        title="DevOps Engineer",
        company="CloudCo",
        application_url="https://example.com/apply",
        source_status="active",
        verification_status="LIVE"
    )
    test_db.add(candidate)
    test_db.add(job)
    await test_db.flush()

    match = CandidateJobMatch(
        subscriber_id=candidate.id,
        job_id=job.id,
        match_score=95
    )
    test_db.add(match)
    await test_db.commit()

    campaign = await campaign_service.create_and_generate_campaign(
        db=test_db,
        name="Unsub Test Campaign"
    )
    assert campaign.total_queued == 0
    assert campaign.total_skipped >= 1
