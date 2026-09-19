import asyncio
import sys
sys.path.insert(0, r'c:\Users\Sumit Raj\OneDrive\email marketing')

from backend.app.core.database import AsyncSessionLocal
from backend.app.services.job_service import job_service

async def main():
    async with AsyncSessionLocal() as db:
        print("Starting full active job inventory synchronization...")
        result = await job_service.sync_jobs(db)
        print("Sync result:", result)

if __name__ == "__main__":
    asyncio.run(main())
