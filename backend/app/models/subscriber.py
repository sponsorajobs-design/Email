from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from backend.app.core.database import Base

class SubscriberSnapshot(Base):
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_subscriber_id = Column(String(255), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    preferred_roles = Column(Text, nullable=True)  # JSON or comma-separated
    location = Column(String(255), nullable=True)
    country_code = Column(String(10), default="ALL", index=True)
    frequency = Column(String(50), default="daily")
    skills = Column(Text, nullable=True)  # JSON or comma-separated
    experience_years = Column(Integer, default=0)
    qualification = Column(String(255), nullable=True)
    education = Column(String(255), nullable=True)
    job_preferences = Column(Text, nullable=True)
    subscription_status = Column(String(50), default="active")
    is_unsubscribed = Column(Boolean, default=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
