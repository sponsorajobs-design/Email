from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.database import get_db
from backend.app.models.job import JobSnapshot
from backend.app.schemas.job import JobResponse
from backend.app.services.url_verifier import url_verifier

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by verification status (LIVE, DEAD, etc.)"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = select(JobSnapshot).order_by(JobSnapshot.id.desc())
    if status:
        query = query.where(JobSnapshot.verification_status == status.upper())
    query = query.limit(limit).offset(offset)
    
    res = await db.execute(query)
    return res.scalars().all()

@router.post("/verify")
async def verify_job_links(
    force: bool = Query(False, description="Force re-verification of already verified jobs"),
    db: AsyncSession = Depends(get_db)
):
    result = await url_verifier.verify_all_pending_jobs(db, force=force)
    return {"message": "Job verification cycle finished", "result": result}
