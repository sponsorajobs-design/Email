from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from backend.app.core.config import settings

# Ensure data directory exists
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

engine = create_async_engine(
    settings.LOCAL_DATABASE_URL,
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    import backend.app.models  # Ensure all models are registered on Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # SQLite schema migration helper for campaigns table
        def add_missing_columns(sync_conn):
            from sqlalchemy import inspect, text
            inspector = inspect(sync_conn)
            cols = [c["name"] for c in inspector.get_columns("campaigns")]
            needed = [
                ("emails_generated", "INTEGER DEFAULT 0"),
                ("no_eligible_job_count", "INTEGER DEFAULT 0"),
                ("frequency_blocked_count", "INTEGER DEFAULT 0"),
                ("deduplicated_count", "INTEGER DEFAULT 0"),
            ]
            for col_name, col_type in needed:
                if col_name not in cols:
                    sync_conn.execute(text(f"ALTER TABLE campaigns ADD COLUMN {col_name} {col_type}"))
                    
        await conn.run_sync(add_missing_columns)
