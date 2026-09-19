import pytest
import httpx
from backend.app.main import app
from backend.app.core.database import init_db
from backend.app.services.categorization_service import categorization_service

def test_categorization_service_rules():
    # Test Data & BI mapping
    cat_data = categorization_service.categorize_profile("Senior Data Analyst, BI Specialist", "SQL, Tableau, Python")
    assert cat_data == "Data & Business Intelligence"

    # Test Software Engineering mapping
    cat_swe = categorization_service.categorize_profile("Fullstack Software Developer", "React, Node.js, PostgreSQL")
    assert cat_swe == "Software & Web Engineering"

    # Test DevOps mapping
    cat_devops = categorization_service.categorize_profile("Site Reliability Engineer, Cloud Architect", "AWS, Kubernetes, Terraform")
    assert cat_devops == "Cloud, DevOps & Infrastructure"

    # Test Marketing mapping
    cat_mkt = categorization_service.categorize_profile("Digital Marketing Lead", "HubSpot, SEO, Copywriting")
    assert cat_mkt == "Marketing, Growth & CRM"

    # Test job categorization
    job_cat = categorization_service.categorize_job("Lead AWS DevOps Engineer", "Kubernetes, Docker, CI/CD", "AWS, Terraform")
    assert job_cat == "Cloud, DevOps & Infrastructure"

@pytest.mark.asyncio
async def test_subscribers_category_endpoints():
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Sync initial data
        await client.post("/api/sync/subscribers")
        await client.post("/api/sync/jobs")
        await client.post("/api/matching/run?threshold=60")

        # 1. Test GET /api/subscribers/categories
        cat_resp = await client.get("/api/subscribers/categories")
        assert cat_resp.status_code == 200
        categories = cat_resp.json()
        assert len(categories) >= 4
        cat_names = [c["category_name"] for c in categories]
        assert "Data & Business Intelligence" in cat_names
        assert "Software & Web Engineering" in cat_names
        assert "Cloud, DevOps & Infrastructure" in cat_names

        # 2. Test GET /api/subscribers with category filter
        filter_resp = await client.get("/api/subscribers?category=Data%20%26%20Business%20Intelligence")
        assert filter_resp.status_code == 200
        data_subs = filter_resp.json()
        assert len(data_subs) > 0
        for s in data_subs:
            assert s["category"] == "Data & Business Intelligence"
            # Ensure email dispatch fields are present
            assert "best_match_job_title" in s
            assert "dispatch_readiness" in s
            assert "email_subject_preview" in s

        # 3. Test POST /api/campaigns/send-category
        camp_resp = await client.post("/api/campaigns/send-category", json={
            "category": "Data & Business Intelligence",
            "match_threshold": 60,
            "batch_size": 10,
            "auto_send": False
        })
        assert camp_resp.status_code == 200
        camp_data = camp_resp.json()
        assert "campaign" in camp_data
        assert camp_data["campaign"]["notes"] is not None
