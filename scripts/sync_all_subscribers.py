import asyncio
import sys
sys.path.insert(0, r'c:\Users\Sumit Raj\OneDrive\email marketing')

from backend.app.core.database import AsyncSessionLocal
from backend.app.services.subscriber_service import subscriber_service

async def main():
    async with AsyncSessionLocal() as db:
        print("Starting subscriber synchronization...")
        result = await subscriber_service.sync_subscribers(db)
        print("Subscriber sync result:", result)

if __name__ == "__main__":
    asyncio.run(main())
