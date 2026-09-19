from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.services.supabase_service import supabase_service
from backend.app.services.email_sender import email_sender
from backend.app.schemas.stats import SystemHealth

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("", response_model=SystemHealth)
async def get_health(db: AsyncSession = Depends(get_db)):
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    supa_status = "connected" if supabase_service.is_configured() else "offline_mode"
    smtp_configured = email_sender.is_smtp_configured()

    return SystemHealth(
        status="healthy" if db_status == "ok" else "degraded",
        database=db_status,
        supabase_configured=supabase_service.is_configured(),
        supabase_status=supa_status,
        smtp_configured=smtp_configured,
        smtp_host=settings.SMTP_HOST,
        smtp_port=settings.SMTP_PORT,
        dry_run=settings.DRY_RUN,
        email_test_mode=settings.EMAIL_TEST_MODE,
        version="1.0.0"
    )
