import pytest
from backend.app.services.email_generator import email_generator

def test_email_subject_generation():
    subject_da = email_generator.generate_subject("Data Analyst")
    assert subject_da == "New Opportunity: Data Analyst"

    subject_se = email_generator.generate_subject("Director of Product Design")
    assert subject_se == "New Opportunity: Director of Product Design"

    subject_fallback = email_generator.generate_subject("")
    assert subject_fallback == "New Opportunity: New Opportunity"

def test_email_rendering_and_honest_disclaimer():
    rendered = email_generator.render_email(
        candidate_name="Priya Sharma",
        subscriber_id=101,
        email="priya@example.com",
        job_title="Data Analyst",
        company="KPMG UK",
        location="London",
        country_code="GB",
        employment_type="Full-time",
        remote_type="Hybrid",
        sponsorship_label="Verified Visa Sponsor",
        target_role="Data Analyst",
        source_job_id="kpmg_101_data-analyst"
    )

    # Subject check
    assert rendered["subject"] == "New Opportunity: Data Analyst"

    # HTML content checks
    html = rendered["html_body"]
    assert "Priya Sharma" in html
    assert "Data Analyst" in html
    assert "KPMG UK" in html
    assert "https://sponsorajobs.com/jobs/kpmg_101_data-analyst" in html
    assert "Hello <strong>Priya Sharma</strong>" in html
    assert "A new job opportunity matching your job-alert preferences is available" in html
    assert "View Job & Apply" in html
    # Must NOT contain fake match scores or false selection claims
    assert "Match Score" not in html
    assert "/100" not in html
    assert "shortlisted" not in html.lower()
    assert "selected" not in html.lower() or "does not represent an employer's selection" in html.lower()

    # Plain-text checks
    text = rendered["text_body"]
    assert "Priya Sharma" in text
    assert "Data Analyst" in text
    assert "https://sponsorajobs.com/jobs/kpmg_101_data-analyst" in text
    assert "/100" not in text
