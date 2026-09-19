from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.services.supabase_service import supabase_service
from backend.app.services.subscriber_service import subscriber_service
from backend.app.services.job_service import job_service

router = APIRouter(prefix="/sync", tags=["Synchronization"])

@router.post("/test-connection")
async def test_supabase_connection():
    return await supabase_service.test_connection()

@router.post("/subscribers")
async def trigger_subscriber_sync(db: AsyncSession = Depends(get_db)):
    result = await subscriber_service.sync_subscribers(db)
    return {"message": "Subscriber sync completed", "result": result}

@router.post("/jobs")
async def trigger_job_sync(db: AsyncSession = Depends(get_db)):
    result = await job_service.sync_jobs(db)
    return {"message": "Job sync completed", "result": result}
