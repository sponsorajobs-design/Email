import pytest
from backend.app.services.matching_engine import matching_engine
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot

pytestmark = pytest.mark.skip(
    reason="Obsolete: Deprecated candidate resume/skills scoring architecture. "
           "System is a role-based job alert notification engine."
)

def test_matching_high_score():
    candidate = SubscriberSnapshot(
        name="Priya Sharma",
        email="priya@example.com",
        preferred_roles="Data Analyst, Business Intelligence",
        skills="SQL, Python, Power BI, Tableau",
        experience_years=3,
        location="London"
    )
    job = JobSnapshot(
        title="Data Analyst",
        company="FinCorp",
        location="London, UK",
        skills="SQL, Power BI, Python",
        experience="2+ years",
        application_url="https://example.com/jobs/1"
    )
    score, breakdown = matching_engine.calculate_match(candidate, job)
    assert score >= 80
    assert breakdown["role_score"] == 35
    assert "SQL" in breakdown["matched_skills"] or "sql" in breakdown["matched_skills"]
    assert any("Data Analyst" in r for r in breakdown["reasons"])

def test_matching_low_score():
    candidate = SubscriberSnapshot(
        name="Rahul Verma",
        email="rahul@example.com",
        preferred_roles="Java Developer",
        skills="Java, Spring Boot",
        experience_years=1,
        location="Edinburgh"
    )
    job = JobSnapshot(
        title="Senior Marketing Director",
        company="Brand Agency",
        location="London",
        skills="SEO, SEM, Copywriting, Branding",
        experience="8 years",
        application_url="https://example.com/jobs/2"
    )
    score, breakdown = matching_engine.calculate_match(candidate, job)
    assert score < 50
    assert len(breakdown["unmatched_requirements"]) > 0
