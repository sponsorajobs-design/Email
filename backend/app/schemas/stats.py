from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any

class DashboardStats(BaseModel):
    total_subscribers: int
    active_subscribers: int
    unsubscribed_users: int
    total_jobs: int
    live_jobs: int
    verified_jobs: int
    dead_jobs: int
    potential_matches: int
    queued_emails: int
    sent_emails: int
    failed_emails: int
    dry_run_mode: bool
    email_test_mode: bool
    test_email_address: str
    
    # Campaign Generation & Email Control Center metrics
    todays_campaigns: int = 0
    emails_generated: int = 0
    subscribers_skipped: int = 0
    jobs_selected: int = 0
    smtp_failures: int = 0
    retries: int = 0
    reconciliation_required_records: int = 0

class SystemHealth(BaseModel):
    status: str
    database: str
    supabase_configured: bool
    supabase_status: str
    smtp_configured: bool
    smtp_host: str
    smtp_port: int
    dry_run: bool
    email_test_mode: bool
    version: str

class AuditLogResponse(BaseModel):
    id: int
    actor: str
    action: str
    details: Optional[str] = None
    result: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)

class SettingsUpdate(BaseModel):
    match_threshold: Optional[int] = None
    email_rate_per_minute: Optional[int] = None
    email_max_concurrency: Optional[int] = None
    job_url_verify_ttl_hours: Optional[int] = None
    dry_run: Optional[bool] = None
    email_test_mode: Optional[bool] = None
    test_email_address: Optional[str] = None
    max_campaign_size: Optional[int] = None
    auto_sync_subscribers: Optional[bool] = None
    auto_sync_interval_minutes: Optional[int] = None
