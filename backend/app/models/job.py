from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from backend.app.core.database import Base

class JobSnapshot(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_job_id = Column(String(255), index=True, nullable=False)
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)  # Comma-separated or JSON list
    experience = Column(String(100), nullable=True)
    employment_type = Column(String(100), nullable=True)
    application_url = Column(String(1000), nullable=False)
    apply_url = Column(String(1000), nullable=True)
    source_status = Column(String(50), default="active")
    
    # Occupational & Filter Metadata
    country_code = Column(String(10), index=True, nullable=True)
    category_id = Column(String(50), index=True, nullable=True)
    remote_type = Column(String(50), nullable=True)
    quality_score = Column(Integer, nullable=True)
    is_featured = Column(Integer, default=0)
    published_at = Column(DateTime, nullable=True, index=True)
    first_seen_at = Column(DateTime, nullable=True)
    sponsorship_label = Column(String(100), nullable=True)
    sponsorship_score = Column(Integer, nullable=True)
    
    # URL Verification Fields
    verification_status = Column(String(50), default="UNKNOWN", index=True)
    verification_http_status = Column(Integer, nullable=True)
    verification_message = Column(Text, nullable=True)
    final_url = Column(String(1000), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    closing_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
