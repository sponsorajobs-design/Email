from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from backend.app.core.database import Base

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="DRAFT", index=True)  # DRAFT, GENERATING, READY, APPROVED, SENDING, COMPLETED, CANCELLED, FAILED
    
    total_candidates = Column(Integer, default=0)
    total_matches = Column(Integer, default=0)
    total_queued = Column(Integer, default=0)
    total_sent = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    total_skipped = Column(Integer, default=0)
    
    emails_generated = Column(Integer, default=0)
    no_eligible_job_count = Column(Integer, default=0)
    frequency_blocked_count = Column(Integer, default=0)
    deduplicated_count = Column(Integer, default=0)
    
    batch_size = Column(Integer, default=25)
    match_threshold = Column(Integer, default=70)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
