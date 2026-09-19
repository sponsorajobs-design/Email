import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General App Config
    APP_ENV: str = "development"
    APP_NAME: str = "SponsorAJobs Local Candidate Matching & Email Engine"
    API_PORT: int = 8000
    API_HOST: str = "127.0.0.1"
    SECRET_KEY: str = "sponsorajobs-local-secret-change-in-production-random-key-32chars"
    ADMIN_PASSWORD_HASH: str = ""
    SYSTEM_TIMEZONE: str = "UTC"

    # Local SQLite DB
    LOCAL_DATABASE_URL: str = "sqlite+aiosqlite:///./data/sponsorajobs_local.db"

    # Production Supabase Connection (Read-Only)
    SUPABASE_URL: str = ""
    SUPABASE_READONLY_KEY: str = ""
    SUPABASE_SUBSCRIBER_TABLE: str = "candidate_users"
    SUPABASE_JOB_TABLE: str = "jobs"
    JOBS_DB_PATH: str = r"C:\Users\Sumit Raj\OneDrive\jobs\local.sqlite"

    # SMTP Credentials & Configuration
    SMTP_HOST: str = "mail.sponsorajobs.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "hr@sponsorajobs.com"
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    FROM_NAME: str = "SponsorAJobs"
    FROM_EMAIL: str = "hr@sponsorajobs.com"

    # Safety & Dry-Run Modes
    DRY_RUN: bool = True
    EMAIL_TEST_MODE: bool = True
    TEST_EMAIL_ADDRESS: str = "test-admin@sponsorajobs.com"

    # Matching Weights & Threshold
    MATCH_THRESHOLD: int = 70
    ROLE_MATCH_WEIGHT: int = 35
    SKILLS_MATCH_WEIGHT: int = 30
    EXPERIENCE_MATCH_WEIGHT: int = 20
    LOCATION_MATCH_WEIGHT: int = 10
    RECENCY_MATCH_WEIGHT: int = 5

    # URL Verification
    JOB_URL_VERIFY_TTL_HOURS: int = 6
    JOB_URL_VERIFY_TIMEOUT_SECONDS: int = 10
    JOB_URL_VERIFY_MAX_RETRIES: int = 2

    # Email Delivery Rate Control
    EMAIL_RATE_PER_MINUTE: int = 10
    EMAIL_MAX_CONCURRENCY: int = 2
    EMAIL_MAX_RETRIES: int = 3

    # Campaign Size & Batching
    MAX_CAMPAIGN_SIZE: int = 100
    DEFAULT_BATCH_SIZE: int = 25

    # Unsubscribe
    UNSUBSCRIBE_BASE_URL: str = "http://127.0.0.1:8000/unsubscribe"

    # Auto-Sync Background Scheduler for Subscribers
    AUTO_SYNC_SUBSCRIBERS: bool = False
    AUTO_SYNC_INTERVAL_MINUTES: int = 15

    # Portal & Website URLs
    SPONSORAJOBS_PORTAL_URL: str = "https://sponsorajobs.com"

settings = Settings()
