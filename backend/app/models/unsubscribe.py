from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from backend.app.core.database import Base

class Unsubscribe(Base):
    __tablename__ = "unsubscribes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    subscriber_id = Column(Integer, nullable=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    token = Column(String(255), unique=True, index=True, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
