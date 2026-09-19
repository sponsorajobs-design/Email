from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.database import get_db
from backend.app.models.match import CandidateJobMatch
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.schemas.match import CandidateJobMatchResponse
from backend.app.services.matching_engine import matching_engine

router = APIRouter(prefix="/matching", tags=["Matching"])

@router.post("/run")
async def run_matching(
    threshold: Optional[int] = Query(None, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    result = await matching_engine.run_matching_cycle(db, threshold=threshold)
    return {"message": "Matching evaluation completed", "result": result}

@router.get("/matches", response_model=List[CandidateJobMatchResponse])
async def list_matches(
    min_score: int = Query(0, ge=0, le=100),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    # Join with subscribers and jobs to provide full candidate/job names in response
    query = (
        select(
            CandidateJobMatch,
            SubscriberSnapshot.name.label("candidate_name"),
            SubscriberSnapshot.email.label("candidate_email"),
            JobSnapshot.title.label("job_title"),
            JobSnapshot.company.label("company_name")
        )
        .join(SubscriberSnapshot, CandidateJobMatch.subscriber_id == SubscriberSnapshot.id)
        .join(JobSnapshot, CandidateJobMatch.job_id == JobSnapshot.id)
        .where(CandidateJobMatch.match_score >= min_score)
        .order_by(CandidateJobMatch.match_score.desc())
        .limit(limit)
        .offset(offset)
    )

    res = await db.execute(query)
    results = []
    for row in res.all():
        match_obj, cand_name, cand_email, j_title, comp_name = row
        results.append(CandidateJobMatchResponse(
            id=match_obj.id,
            subscriber_id=match_obj.subscriber_id,
            job_id=match_obj.job_id,
            candidate_name=cand_name,
            candidate_email=cand_email,
            job_title=j_title,
            company_name=comp_name,
            match_score=match_obj.match_score,
            role_score=match_obj.role_score,
            skills_score=match_obj.skills_score,
            experience_score=match_obj.experience_score,
            location_score=match_obj.location_score,
            recency_score=match_obj.recency_score,
            match_reasons=match_obj.match_reasons,
            matched_skills=match_obj.matched_skills,
            unmatched_requirements=match_obj.unmatched_requirements,
            created_at=match_obj.created_at
        ))
    return results
