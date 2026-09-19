from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from backend.app.core.database import Base

class EmailQueueItem(Base):
    __tablename__ = "email_queue"
    __table_args__ = (
        UniqueConstraint('subscriber_id', 'dispatch_date', name='uq_subscriber_dispatch_date'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False)
    subscriber_id = Column(Integer, ForeignKey("subscribers.id", ondelete="CASCADE"), index=True, nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    
    # Calendar-day enforcement invariant (Format: YYYY-MM-DD in UTC)
    dispatch_date = Column(String(10), index=True, nullable=False)
    
    recipient = Column(String(255), index=True, nullable=False)
    candidate_name = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    company_name = Column(String(255), nullable=True)
    match_score = Column(Integer, default=0)

    subject = Column(String(500), nullable=False)
    html_body = Column(Text, nullable=False)
    text_body = Column(Text, nullable=False)
    
    status = Column(String(50), default="PENDING", index=True)  # PENDING, SENDING, SENT, FAILED, SKIPPED, CANCELLED, REQUIRES_RECONCILIATION
    skip_reason = Column(String(100), nullable=True)
    reconciliation_status = Column(String(50), nullable=True)
    
    attempts = Column(Integer, default=0)
    scheduled_at = Column(DateTime, default=datetime.utcnow)
    locked_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    message_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
