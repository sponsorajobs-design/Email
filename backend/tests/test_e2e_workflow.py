import pytest
import httpx
from sqlalchemy import delete
from backend.app.main import app
from backend.app.core.database import init_db, AsyncSessionLocal
from backend.app.models.match import CandidateJobHistory

@pytest.mark.asyncio
async def test_end_to_end_api_pipeline():
    await init_db()
    # Clear any previous test history to allow fresh campaign staging in E2E test
    async with AsyncSessionLocal() as db_sess:
        await db_sess.execute(delete(CandidateJobHistory))
        await db_sess.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health Check
        health_resp = await client.get("/api/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] in ("healthy", "degraded")

        # 2. Sync Subscribers
        sub_resp = await client.post("/api/sync/subscribers")
        assert sub_resp.status_code == 200
        assert sub_resp.json()["result"]["total_processed"] > 0

        # 3. Sync Jobs
        job_resp = await client.post("/api/sync/jobs")
        assert job_resp.status_code == 200
        assert job_resp.json()["result"]["total_processed"] > 0

        # 4. Verify Job Links
        verify_resp = await client.post("/api/jobs/verify")
        assert verify_resp.status_code == 200
        assert "total_verified" in verify_resp.json()["result"]

        # 5. Run Matching Engine
        match_resp = await client.post("/api/matching/run?threshold=60")
        assert match_resp.status_code == 200
        assert match_resp.json()["result"]["total_evaluations"] > 0

        # 6. Check Matches Explorer
        matches_list = await client.get("/api/matching/matches?min_score=60")
        assert matches_list.status_code == 200
        matches = matches_list.json()
        assert len(matches) > 0

        # 7. Create and Stage Campaign
        camp_payload = {
            "name": "Integration Test Campaign",
            "match_threshold": 60,
            "batch_size": 10
        }
        camp_resp = await client.post("/api/campaigns", json=camp_payload)
        assert camp_resp.status_code == 200
        camp = camp_resp.json()
        camp_id = camp["id"]
        assert camp["status"] == "READY"
        assert camp["total_queued"] > 0

        # 8. Preview Campaign
        preview_resp = await client.get(f"/api/campaigns/{camp_id}/preview")
        assert preview_resp.status_code == 200
        previews = preview_resp.json()
        assert len(previews) > 0
        first_item = previews[0]
        assert "Congratulations! Your Profile Has Been Shortlisted" in first_item["subject"]
        assert "profile-to-opportunity matching" in first_item["html_preview"]

        # 9. Send Test Email
        test_email_resp = await client.post("/api/email/test", json={
            "recipient": "test-admin@sponsorajobs.com",
            "candidate_name": "Test Candidate",
            "job_title": "Data Analyst",
            "company_name": "Test Company",
            "application_url": "https://sponsorajobs.com"
        })
        assert test_email_resp.status_code == 200
        assert test_email_resp.json()["result"]["success"] is True

        # 10. Approve Campaign
        approve_resp = await client.post(f"/api/campaigns/{camp_id}/approve")
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "APPROVED"

        # 11. Send Campaign (in Dry Run mode)
        send_resp = await client.post(f"/api/campaigns/{camp_id}/send?batch_limit=10")
        assert send_resp.status_code == 200
        assert send_resp.json()["sent"] > 0

        # 12. Public Unsubscribe Link
        unsub_resp = await client.get("/unsubscribe/test-security-token-12345")
        assert unsub_resp.status_code == 200
        assert "Unsubscribed Successfully" in unsub_resp.text

        # 13. Audit Logs
        audit_resp = await client.get("/api/audit-logs")
        assert audit_resp.status_code == 200
        logs = audit_resp.json()
        assert len(logs) > 0

        # 14. Verify Subscriber Sent Email Tracking & History Trail
        subs_resp = await client.get("/api/subscribers?limit=500")
        assert subs_resp.status_code == 200
        subscribers = subs_resp.json()
        assert len(subscribers) > 0
        tracked_sub = next((s for s in subscribers if s.get("total_emails_sent", 0) > 0), None)
        assert tracked_sub is not None
        assert tracked_sub["last_email_sent_at"] is not None
        assert tracked_sub["last_recommended_job"] is not None

        # Fetch history for this subscriber
        hist_resp = await client.get(f"/api/subscribers/{tracked_sub['id']}/history")
        assert hist_resp.status_code == 200
        history_items = hist_resp.json()
        assert len(history_items) == tracked_sub["total_emails_sent"]
        assert "Congratulations! Your Profile Has Been Shortlisted" in history_items[0]["subject"]
        assert history_items[0]["job_title"] is not None
