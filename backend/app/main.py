from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.core.logging import app_logger

# Import route modules
from backend.app.api.routes import (
    health,
    dashboard,
    sync,
    jobs,
    subscribers,
    matching,
    campaigns,
    email,
    unsubscribe,
    audit,
    settings as settings_route
)
import asyncio
from datetime import datetime
from backend.app.core.database import AsyncSessionLocal
from backend.app.services.subscriber_service import subscriber_service

last_auto_sync_at = None

async def auto_sync_worker():
    global last_auto_sync_at
    while True:
        try:
            await asyncio.sleep(15)
            if settings.AUTO_SYNC_SUBSCRIBERS:
                interval_secs = max(30, settings.AUTO_SYNC_INTERVAL_MINUTES * 60)
                now = datetime.utcnow()
                if last_auto_sync_at is None or (now - last_auto_sync_at).total_seconds() >= interval_secs:
                    app_logger.info("Auto-sync: Checking for new subscribers from Supabase...")
                    async with AsyncSessionLocal() as db:
                        try:
                            result = await subscriber_service.sync_subscribers(db)
                            last_auto_sync_at = datetime.utcnow()
                            app_logger.info(f"Auto-sync completed: {result['synced']} new, {result['updated']} updated")
                        except Exception as err:
                            app_logger.error(f"Auto-sync error during execution: {err}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            app_logger.error(f"Auto-sync worker unexpected exception: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("Initializing local database schema...")
    await init_db()
    app_logger.info("Local database initialized successfully.")
    worker_task = asyncio.create_task(auto_sync_worker())
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    app_logger.info("Shutting down local engine.")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan
)

# Local CORS Policy (Permits React frontend on Vite port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers under /api
app.include_router(health.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(subscribers.router, prefix="/api")
app.include_router(matching.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")
app.include_router(email.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(settings_route.router, prefix="/api")

# Unsubscribe routes (public root & api)
app.include_router(unsubscribe.router)

@app.get("/health")
async def root_health():
    return {"status": "healthy", "service": "SponsorAJobs Email Hub"}

@app.get("/")
async def root():
    from fastapi.responses import HTMLResponse
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SponsorAJobs Engine</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0a0f1d; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .card { background: #111827; padding: 40px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); max-width: 500px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
            h1 { font-size: 24px; color: #38bdf8; margin-bottom: 8px; }
            p { color: #94a3b8; font-size: 14px; line-height: 1.6; margin-bottom: 24px; }
            .btn { display: inline-block; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; margin: 6px; }
            .btn-primary { background: #2563eb; color: white; }
            .btn-secondary { background: rgba(255,255,255,0.1); color: #f8fafc; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🎯 SponsorAJobs Engine</h1>
            <p>The backend API service is running locally on port 8000.</p>
            <div>
                <a href="http://localhost:5173" class="btn btn-primary">Open Admin Dashboard (Port 5173) &rarr;</a>
                <a href="/docs" class="btn btn-secondary">API Swagger Docs (/docs)</a>
            </div>
        </div>
    </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
