from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime

class SubscriberBase(BaseModel):
    name: str
    email: str
    preferred_roles: Optional[str] = None
    location: Optional[str] = None
    skills: Optional[str] = None
    experience_years: Optional[int] = 0
    qualification: Optional[str] = None
    education: Optional[str] = None
    job_preferences: Optional[str] = None
    subscription_status: Optional[str] = "active"

class SubscriberCreate(SubscriberBase):
    source_subscriber_id: str

class SubscriberResponse(SubscriberBase):
    id: int
    source_subscriber_id: str
    is_unsubscribed: bool
    created_at: datetime
    total_emails_sent: int = 0
    last_email_sent_at: Optional[datetime] = None
    last_recommended_job: Optional[str] = None
    category: str = "General Professional"
    
    # Enriched Email Dispatch Fields
    best_match_job_id: Optional[int] = None
    best_match_job_title: Optional[str] = None
    best_match_company: Optional[str] = None
    best_match_score: Optional[int] = None
    best_match_application_url: Optional[str] = None
    best_match_url_status: Optional[str] = None
    email_subject_preview: Optional[str] = None
    dispatch_readiness: str = "NO_MATCH"  # READY_TO_SEND, ALREADY_SENT, UNSUBSCRIBED, NO_MATCH

    model_config = ConfigDict(from_attributes=True)

class CategorySummaryResponse(BaseModel):
    category_name: str
    total_candidates: int
    ready_to_send_count: int
    already_sent_count: int
    unsubscribed_count: int
    live_jobs_count: int

class SubscriberSentEmailHistoryItem(BaseModel):
    id: int
    job_id: int
    job_title: str
    company_name: str
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    match_score: int
    subject: str
    sent_at: Optional[datetime] = None
    message_id: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)

class NormalizedCandidateProfile(BaseModel):
    id: int
    source_subscriber_id: str
    name: str
    email: str
    preferred_roles: List[str]
    location: str
    skills: List[str]
    experience_years: int
    is_unsubscribed: bool
