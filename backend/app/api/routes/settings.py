from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.schemas.stats import SettingsUpdate
from backend.app.core.logging import log_audit

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("")
async def get_settings():
    return {
        "app_env": settings.APP_ENV,
        "match_threshold": settings.MATCH_THRESHOLD,
        "role_match_weight": settings.ROLE_MATCH_WEIGHT,
        "skills_match_weight": settings.SKILLS_MATCH_WEIGHT,
        "experience_match_weight": settings.EXPERIENCE_MATCH_WEIGHT,
        "location_match_weight": settings.LOCATION_MATCH_WEIGHT,
        "recency_match_weight": settings.RECENCY_MATCH_WEIGHT,
        "dry_run": settings.DRY_RUN,
        "email_test_mode": settings.EMAIL_TEST_MODE,
        "test_email_address": settings.TEST_EMAIL_ADDRESS,
        "email_rate_per_minute": settings.EMAIL_RATE_PER_MINUTE,
        "email_max_concurrency": settings.EMAIL_MAX_CONCURRENCY,
        "email_max_retries": settings.EMAIL_MAX_RETRIES,
        "job_url_verify_ttl_hours": settings.JOB_URL_VERIFY_TTL_HOURS,
        "max_campaign_size": settings.MAX_CAMPAIGN_SIZE,
        "smtp_host": settings.SMTP_HOST,
        "smtp_port": settings.SMTP_PORT,
        "smtp_username": settings.SMTP_USERNAME,
        "from_name": settings.FROM_NAME,
        "from_email": settings.FROM_EMAIL,
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_READONLY_KEY),
        "supabase_subscriber_table": settings.SUPABASE_SUBSCRIBER_TABLE,
        "supabase_job_table": settings.SUPABASE_JOB_TABLE,
        "auto_sync_subscribers": settings.AUTO_SYNC_SUBSCRIBERS,
        "auto_sync_interval_minutes": settings.AUTO_SYNC_INTERVAL_MINUTES
    }

@router.post("")
async def update_settings(payload: SettingsUpdate):
    updates = []
    if payload.match_threshold is not None:
        settings.MATCH_THRESHOLD = payload.match_threshold
        updates.append(f"match_threshold={payload.match_threshold}")
    if payload.email_rate_per_minute is not None:
        settings.EMAIL_RATE_PER_MINUTE = payload.email_rate_per_minute
        updates.append(f"rate_per_min={payload.email_rate_per_minute}")
    if payload.email_max_concurrency is not None:
        settings.EMAIL_MAX_CONCURRENCY = payload.email_max_concurrency
        updates.append(f"max_concurrency={payload.email_max_concurrency}")
    if payload.job_url_verify_ttl_hours is not None:
        settings.JOB_URL_VERIFY_TTL_HOURS = payload.job_url_verify_ttl_hours
        updates.append(f"url_ttl_hours={payload.job_url_verify_ttl_hours}")
    if payload.dry_run is not None:
        settings.DRY_RUN = payload.dry_run
        updates.append(f"dry_run={payload.dry_run}")
    if payload.email_test_mode is not None:
        settings.EMAIL_TEST_MODE = payload.email_test_mode
        updates.append(f"email_test_mode={payload.email_test_mode}")
    if payload.test_email_address is not None:
        settings.TEST_EMAIL_ADDRESS = payload.test_email_address
        updates.append(f"test_email={payload.test_email_address}")
    if payload.max_campaign_size is not None:
        settings.MAX_CAMPAIGN_SIZE = payload.max_campaign_size
        updates.append(f"max_campaign_size={payload.max_campaign_size}")
    if payload.auto_sync_subscribers is not None:
        settings.AUTO_SYNC_SUBSCRIBERS = payload.auto_sync_subscribers
        updates.append(f"auto_sync_subscribers={payload.auto_sync_subscribers}")
    if payload.auto_sync_interval_minutes is not None:
        settings.AUTO_SYNC_INTERVAL_MINUTES = payload.auto_sync_interval_minutes
        updates.append(f"auto_sync_interval_minutes={payload.auto_sync_interval_minutes}")

    log_audit(
        actor="admin",
        action="UPDATE_SETTINGS",
        details=", ".join(updates)
    )
    return {"message": "Settings updated successfully", "updates": updates}
