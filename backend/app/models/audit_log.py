from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from backend.app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    actor = Column(String(100), default="admin", nullable=False)
    action = Column(String(100), index=True, nullable=False)  # SYNC_JOBS, SYNC_SUBSCRIBERS, VERIFY_URLS, RUN_MATCHING, etc.
    details = Column(Text, nullable=True)
    result = Column(String(50), default="SUCCESS")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
