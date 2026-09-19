import pytest
from backend.app.services.subscriber_service import subscriber_service
from backend.app.services.supabase_service import supabase_service

def test_subscriber_email_validation():
    assert subscriber_service.is_valid_email("valid.user@example.com") is True
    assert subscriber_service.is_valid_email("candidate+test@domain.co.uk") is True
    assert subscriber_service.is_valid_email("invalid-email-no-at") is False
    assert subscriber_service.is_valid_email("test@.com") is False
    assert subscriber_service.is_valid_email("") is False

def test_subscriber_token_normalization():
    tokens = subscriber_service.normalize_tokens("Python, SQL; FastAPI / Docker")
    assert "python" in tokens
    assert "sql" in tokens
    assert "fastapi" in tokens
    assert "docker" in tokens

def test_supabase_adapter_field_mapping():
    raw_sub = {
        "user_id": 456,
        "full_name": "Test User",
        "email": "test@domain.com",
        "preferred_role": ["Data Analyst", "BI Specialist"],
        "skills": ["SQL", "Power BI"],
        "experience": "3-5 years",
        "status": "active"
    }
    mapped = supabase_service._map_subscriber_record(raw_sub)
    assert mapped["source_subscriber_id"] == "456"
    assert mapped["name"] == "Test User"
    assert mapped["email"] == "test@domain.com"
    assert "data analyst" in mapped["preferred_roles"].lower()
    assert mapped["experience_years"] == 3

def test_job_adapter_field_mapping():
    raw_job = {
        "job_id": "job-999",
        "position": "Lead AI Engineer",
        "employer": "Tech UK Ltd",
        "job_location": "London",
        "url": "https://example.com/apply",
        "skills_needed": ["PyTorch", "Python"],
        "is_active": True
    }
    mapped = supabase_service._map_job_record(raw_job)
    assert mapped["source_job_id"] == "job-999"
    assert mapped["title"] == "Lead AI Engineer"
    assert mapped["company"] == "Tech UK Ltd"
    assert mapped["application_url"] == "https://example.com/apply"
    assert mapped["source_status"] == "active"
