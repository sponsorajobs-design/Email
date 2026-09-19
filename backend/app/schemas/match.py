from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class MatchScoreBreakdown(BaseModel):
    total_score: int
    role_score: int
    skills_score: int
    experience_score: int
    location_score: int
    recency_score: int
    reasons: List[str]
    matched_skills: List[str]
    unmatched_requirements: List[str]

class CandidateJobMatchResponse(BaseModel):
    id: int
    subscriber_id: int
    job_id: int
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    match_score: int
    role_score: int
    skills_score: int
    experience_score: int
    location_score: int
    recency_score: int
    match_reasons: Optional[str] = None
    matched_skills: Optional[str] = None
    unmatched_requirements: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
