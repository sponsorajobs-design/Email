from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class CampaignCreate(BaseModel):
    name: str
    match_threshold: Optional[int] = 70
    batch_size: Optional[int] = 25
    notes: Optional[str] = None
    category: Optional[str] = None
    custom_subject_template: Optional[str] = None
    custom_intro_note: Optional[str] = None

class CategoryCampaignRequest(BaseModel):
    category: str
    match_threshold: Optional[int] = 70
    batch_size: Optional[int] = 50
    auto_send: Optional[bool] = False

class SendSelectedRequest(BaseModel):
    queue_ids: List[int]

class CampaignResponse(BaseModel):
    id: int
    name: str
    status: str
    total_candidates: int
    total_matches: int
    total_queued: int
    total_sent: int
    total_failed: int
    total_skipped: int
    emails_generated: int = 0
    no_eligible_job_count: int = 0
    frequency_blocked_count: int = 0
    deduplicated_count: int = 0
    batch_size: int
    match_threshold: int
    notes: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CampaignPreviewItem(BaseModel):
    queue_id: int
    subscriber_id: int
    job_id: int
    candidate_name: str
    candidate_email: str
    job_title: str
    company_name: str
    match_score: int
    url_status: str
    status: str
    subject: str
    html_preview: str

class CampaignSubscriberItem(BaseModel):
    queue_id: int
    composition_id: Optional[int] = None
    subscriber_id: int
    subscriber_name: str
    subscriber_email: str
    preferred_roles: Optional[str] = None
    country_code: Optional[str] = None
    frequency: Optional[str] = None
    job_id: int
    source_job_id: Optional[str] = None
    job_title: str
    company_name: str
    location: Optional[str] = None
    job_url: str
    email_subject: str
    queue_status: str
    smtp_status: Optional[str] = None
    message_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    match_type: str = "DIRECT"

class CampaignCompositionDetail(BaseModel):
    id: int
    campaign_id: int
    queue_id: Optional[int] = None
    subscriber_id: int
    job_id: int
    recipient: str
    candidate_name: Optional[str] = None
    subject: str
    rendered_html: str
    rendered_text: str
    template_version: str
    role_used: Optional[str] = None
    country_filter: Optional[str] = None
    frequency: Optional[str] = None
    job_url: str
    decision_trace: Optional[Dict[str, Any]] = None
    created_at: datetime


class AudienceRecipient(BaseModel):
    id: int
    name: str
    email: str
    preferred_roles: Optional[str] = ""
    location: Optional[str] = ""


class AudienceCategory(BaseModel):
    category_name: str
    display_title: str
    icon: str
    total_candidates: int
    recipients: List[AudienceRecipient]


class CustomPreviewRequest(BaseModel):
    job_title: str
    job_link: str
    company_name: Optional[str] = "SponsorAJobs Partner"
    location: Optional[str] = "United Kingdom"
    employment_type: Optional[str] = "Full-time"
    custom_subject: Optional[str] = None
    custom_message: Optional[str] = None


class CustomPreviewResponse(BaseModel):
    subject: str
    html_body: str
    text_body: str
    job_url: str


class DirectComposeSendRequest(BaseModel):
    job_title: str
    job_link: str
    company_name: Optional[str] = "SponsorAJobs Partner"
    location: Optional[str] = "United Kingdom"
    employment_type: Optional[str] = "Full-time"
    selected_categories: Optional[List[str]] = []
    selected_subscriber_ids: Optional[List[int]] = []
    custom_subject: Optional[str] = None
    custom_message: Optional[str] = None
    is_test_send: Optional[bool] = False
    test_recipient: Optional[str] = None

