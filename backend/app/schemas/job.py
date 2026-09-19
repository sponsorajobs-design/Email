from pydantic import BaseModel, HttpUrl, ConfigDict
from typing import Optional, List
from datetime import datetime

class JobBase(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    skills: Optional[str] = None
    experience: Optional[str] = None
    employment_type: Optional[str] = None
    application_url: str

class JobCreate(JobBase):
    source_job_id: str
    source_status: Optional[str] = "active"

class JobResponse(JobBase):
    id: int
    source_job_id: str
    source_status: Optional[str] = None
    verification_status: str
    verification_http_status: Optional[int] = None
    verification_message: Optional[str] = None
    final_url: Optional[str] = None
    verified_at: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class JobVerificationResult(BaseModel):
    job_id: int
    url: str
    status: str
    http_status: Optional[int] = None
    message: Optional[str] = None
    final_url: Optional[str] = None
