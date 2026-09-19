from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from backend.app.core.database import Base

class CandidateJobMatch(Base):
    __tablename__ = "candidate_job_matches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    subscriber_id = Column(Integer, ForeignKey("subscribers.id", ondelete="CASCADE"), index=True, nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    match_score = Column(Integer, nullable=False)
    role_score = Column(Integer, default=0)
    skills_score = Column(Integer, default=0)
    experience_score = Column(Integer, default=0)
    location_score = Column(Integer, default=0)
    recency_score = Column(Integer, default=0)
    
    match_reasons = Column(Text, nullable=True)  # JSON or newline-separated
    matched_skills = Column(Text, nullable=True)  # JSON or comma-separated
    unmatched_requirements = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("subscriber_id", "job_id", name="uq_subscriber_job_match"),
    )

class CandidateJobHistory(Base):
    __tablename__ = "candidate_job_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    subscriber_id = Column(Integer, ForeignKey("subscribers.id", ondelete="CASCADE"), index=True, nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    match_score = Column(Integer, nullable=False)
    email_status = Column(String(50), default="SENT")  # SENT, SKIPPED, FAILED
    campaign_id = Column(Integer, nullable=True, index=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("subscriber_id", "job_id", name="uq_candidate_job_history"),
    )
