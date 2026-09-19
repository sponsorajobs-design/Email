from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.database import get_db
from backend.app.models.email_queue import EmailQueueItem
from backend.app.schemas.email_queue import EmailQueueResponse, TestEmailRequest
from backend.app.services.email_generator import email_generator
from backend.app.services.email_sender import email_sender

router = APIRouter(prefix="/email", tags=["Email"])

@router.post("/test")
async def send_test_email(payload: TestEmailRequest):
    reasons_list = [r.strip() for r in (payload.match_reasons or "").split("\n") if r.strip()]
    rendered = email_generator.render_email(
        candidate_name=payload.candidate_name,
        subscriber_id=9999,
        email=payload.recipient,
        job_title=payload.job_title,
        company=payload.company_name,
        location=payload.location,
        experience=payload.experience,
        employment_type="Full-time",
        match_score=94,
        match_reasons=reasons_list,
        application_url=payload.application_url
    )

    result = email_sender.send_single_message(
        recipient=payload.recipient,
        subject=rendered["subject"],
        html_body=rendered["html_body"],
        text_body=rendered["text_body"],
        is_test=True
    )
    return {
        "message": "Test email triggered",
        "result": result,
        "subject": rendered["subject"]
    }

@router.get("/queue", response_model=List[EmailQueueResponse])
async def list_email_queue(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = select(EmailQueueItem).order_by(EmailQueueItem.id.desc())
    if status:
        query = query.where(EmailQueueItem.status == status.upper())
    query = query.limit(limit).offset(offset)
    res = await db.execute(query)
    return res.scalars().all()
