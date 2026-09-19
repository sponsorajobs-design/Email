from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from backend.app.core.database import Base

class EmailComposition(Base):
    __tablename__ = "email_compositions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False)
    queue_id = Column(Integer, ForeignKey("email_queue.id", ondelete="SET NULL"), index=True, nullable=True)
    subscriber_id = Column(Integer, ForeignKey("subscribers.id", ondelete="CASCADE"), index=True, nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    
    recipient = Column(String(255), index=True, nullable=False)
    candidate_name = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=False)
    rendered_html = Column(Text, nullable=False)
    rendered_text = Column(Text, nullable=False)
    template_version = Column(String(50), default="v2.0-role-alert", nullable=False)
    
    role_used = Column(String(255), nullable=True)
    country_filter = Column(String(50), nullable=True)
    frequency = Column(String(50), nullable=True)
    job_url = Column(String(1000), nullable=False)
    
    # Complete decision trace: JSON string containing match type, rank position, score, reasons, excluded alternatives
    decision_trace = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
