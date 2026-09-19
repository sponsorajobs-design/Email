from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

class EmailQueueResponse(BaseModel):
    id: int
    campaign_id: int
    subscriber_id: int
    job_id: int
    recipient: str
    candidate_name: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    match_score: int
    subject: str
    status: str
    skip_reason: Optional[str] = None
    attempts: int
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TestEmailRequest(BaseModel):
    recipient: EmailStr
    candidate_name: Optional[str] = "Priya Sharma"
    job_title: Optional[str] = "Senior Full Stack Engineer"
    company_name: Optional[str] = "FinTech Global UK"
    location: Optional[str] = "London, UK (Hybrid)"
    experience: Optional[str] = "3+ years"
    match_reasons: Optional[str] = "- Preferred role matches Senior Full Stack Engineer\n- Python and React skills match core requirements\n- Location matches candidate preference"
    application_url: Optional[str] = "https://sponsorajobs.com/jobs/sample-101"
