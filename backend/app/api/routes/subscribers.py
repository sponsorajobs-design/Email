from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, desc
from backend.app.core.database import get_db
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.match import CandidateJobHistory
from backend.app.models.job import JobSnapshot
from backend.app.models.campaign import Campaign
from backend.app.schemas.subscriber import SubscriberResponse, SubscriberSentEmailHistoryItem

from backend.app.services.categorization_service import categorization_service
from backend.app.schemas.subscriber import SubscriberResponse, SubscriberSentEmailHistoryItem, CategorySummaryResponse
from backend.app.models.match import CandidateJobMatch
from backend.app.core.config import settings

router = APIRouter(prefix="/subscribers", tags=["Subscribers"])

@router.get("/categories", response_model=List[CategorySummaryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Fetch aggregated category metrics for quick filtering and batch campaign launches."""
    # 1. Fetch all subscribers
    subs_res = await db.execute(select(SubscriberSnapshot))
    subscribers = subs_res.scalars().all()

    # 2. Fetch all live verified jobs
    jobs_res = await db.execute(select(JobSnapshot).where(JobSnapshot.source_status == "active"))
    jobs = jobs_res.scalars().all()

    # 3. Fetch sent history pairs
    hist_res = await db.execute(select(CandidateJobHistory.subscriber_id, CandidateJobHistory.job_id))
    sent_pairs = set((row[0], row[1]) for row in hist_res.fetchall())

    # 4. Fetch top matches
    match_res = await db.execute(
        select(CandidateJobMatch).where(CandidateJobMatch.match_score >= settings.MATCH_THRESHOLD)
    )
    matches_by_sub = {}
    for m in match_res.scalars().all():
        if m.subscriber_id not in matches_by_sub or m.match_score > matches_by_sub[m.subscriber_id].match_score:
            matches_by_sub[m.subscriber_id] = m

    live_jobs_map = {j.id: j for j in jobs if j.verification_status in ("LIVE", "REDIRECTED")}

    # Group metrics by category
    summary_map = {}
    for cat in categorization_service.CATEGORIES:
        summary_map[cat] = {
            "category_name": cat,
            "total_candidates": 0,
            "ready_to_send_count": 0,
            "already_sent_count": 0,
            "unsubscribed_count": 0,
            "live_jobs_count": 0
        }

    # Count live jobs per category
    for j in live_jobs_map.values():
        j_cat = categorization_service.categorize_job(j.title, j.requirements, j.skills)
        if j_cat in summary_map:
            summary_map[j_cat]["live_jobs_count"] += 1

    # Count candidate readiness per category
    for s in subscribers:
        cat = categorization_service.categorize_profile(s.preferred_roles, s.skills)
        if cat not in summary_map:
            summary_map[cat] = {
                "category_name": cat,
                "total_candidates": 0,
                "ready_to_send_count": 0,
                "already_sent_count": 0,
                "unsubscribed_count": 0,
                "live_jobs_count": 0
            }
        summary_map[cat]["total_candidates"] += 1

        if s.is_unsubscribed:
            summary_map[cat]["unsubscribed_count"] += 1
        else:
            best_m = matches_by_sub.get(s.id)
            if best_m and best_m.job_id in live_jobs_map:
                if (s.id, best_m.job_id) in sent_pairs:
                    summary_map[cat]["already_sent_count"] += 1
                else:
                    summary_map[cat]["ready_to_send_count"] += 1

    return list(summary_map.values())

@router.get("", response_model=List[SubscriberResponse])
async def list_subscribers(
    search: Optional[str] = Query(None, description="Search by name, email, or role"),
    category: Optional[str] = Query(None, description="Filter by professional category"),
    active_only: bool = Query(True),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = select(SubscriberSnapshot).order_by(SubscriberSnapshot.id.desc())
    if active_only:
        query = query.where(
            SubscriberSnapshot.subscription_status == "active",
            SubscriberSnapshot.is_unsubscribed == False
        )
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                SubscriberSnapshot.name.ilike(pattern),
                SubscriberSnapshot.email.ilike(pattern),
                SubscriberSnapshot.preferred_roles.ilike(pattern)
            )
        )
    res = await db.execute(query)
    all_subscribers = res.scalars().all()

    if category and category.lower() not in ("all", ""):
        target_cat = category.strip().lower()
        subscribers = [
            s for s in all_subscribers
            if categorization_service.categorize_profile(s.preferred_roles, s.skills).lower() == target_cat
        ]
    else:
        subscribers = all_subscribers

    subscribers = subscribers[offset:offset + limit]

    # Pre-fetch sent history aggregates for these subscribers to populate tracking columns
    sub_ids = [s.id for s in subscribers]
    history_map = {}
    sent_pairs = set()
    if sub_ids:
        hist_query = (
            select(
                CandidateJobHistory.subscriber_id,
                func.count(CandidateJobHistory.id).label("sent_count"),
                func.max(CandidateJobHistory.sent_at).label("last_sent")
            )
            .where(CandidateJobHistory.subscriber_id.in_(sub_ids))
            .group_by(CandidateJobHistory.subscriber_id)
        )
        hist_res = await db.execute(hist_query)
        for row in hist_res.all():
            history_map[row.subscriber_id] = {
                "sent_count": row.sent_count,
                "last_sent": row.last_sent
            }

        # Also find the last recommended job title for each
        latest_job_query = (
            select(
                CandidateJobHistory.subscriber_id,
                JobSnapshot.title
            )
            .join(JobSnapshot, CandidateJobHistory.job_id == JobSnapshot.id)
            .where(CandidateJobHistory.subscriber_id.in_(sub_ids))
            .order_by(CandidateJobHistory.sent_at.desc())
        )
        latest_res = await db.execute(latest_job_query)
        for row in latest_res.all():
            if row.subscriber_id in history_map and "last_job" not in history_map[row.subscriber_id]:
                history_map[row.subscriber_id]["last_job"] = row.title

        # Load all sent pairs for sub_ids to calculate readiness
        pairs_res = await db.execute(
            select(CandidateJobHistory.subscriber_id, CandidateJobHistory.job_id)
            .where(CandidateJobHistory.subscriber_id.in_(sub_ids))
        )
        sent_pairs = set((row[0], row[1]) for row in pairs_res.fetchall())

    # Pre-fetch top qualified match for each subscriber to provide all email details in table
    best_matches = {}
    if sub_ids:
        matches_query = (
            select(
                CandidateJobMatch,
                JobSnapshot.source_job_id,
                JobSnapshot.title.label("job_title"),
                JobSnapshot.company.label("company_name"),
                JobSnapshot.verification_status
            )
            .join(JobSnapshot, CandidateJobMatch.job_id == JobSnapshot.id)
            .where(
                CandidateJobMatch.subscriber_id.in_(sub_ids),
                JobSnapshot.source_status == "active",
                JobSnapshot.verification_status == "LIVE"
            )
            .order_by(CandidateJobMatch.match_score.desc())
        )
        m_res = await db.execute(matches_query)
        for m, src_job_id, j_title, comp, ver_status in m_res.all():
            if m.subscriber_id not in best_matches:
                portal_listing_url = f"{settings.SPONSORAJOBS_PORTAL_URL.rstrip('/')}/job/{src_job_id or m.job_id}"
                best_matches[m.subscriber_id] = {
                    "job_id": m.job_id,
                    "job_title": j_title,
                    "company_name": comp,
                    "match_score": m.match_score,
                    "application_url": portal_listing_url,
                    "verification_status": ver_status
                }

    results = []
    for s in subscribers:
        cat = categorization_service.categorize_profile(s.preferred_roles, s.skills)
        if category and category.lower() not in ("all", ""):
            if cat.lower() != category.strip().lower():
                continue

        info = history_map.get(s.id, {})
        m_info = best_matches.get(s.id)

        # Compute Dispatch Readiness & Subject Line Preview
        subject_preview = None
        readiness = "NO_MATCH"
        if s.is_unsubscribed:
            readiness = "UNSUBSCRIBED"
        elif m_info:
            subject_preview = f"Congratulations! Your Profile Has Been Shortlisted for the {m_info['job_title']} Role"
            is_already_sent = (s.id, m_info["job_id"]) in sent_pairs
            is_live_url = m_info["verification_status"] in ("LIVE", "REDIRECTED")
            is_qualified = m_info["match_score"] >= settings.MATCH_THRESHOLD

            if is_already_sent:
                readiness = "ALREADY_SENT"
            elif is_live_url and is_qualified:
                readiness = "READY_TO_SEND"
            else:
                readiness = "NO_MATCH"

        results.append(SubscriberResponse(
            id=s.id,
            source_subscriber_id=s.source_subscriber_id,
            name=s.name,
            email=s.email,
            preferred_roles=s.preferred_roles,
            location=s.location,
            skills=s.skills,
            experience_years=s.experience_years,
            qualification=s.qualification,
            education=s.education,
            job_preferences=s.job_preferences,
            subscription_status=s.subscription_status,
            is_unsubscribed=s.is_unsubscribed,
            created_at=s.created_at,
            total_emails_sent=info.get("sent_count", 0),
            last_email_sent_at=info.get("last_sent"),
            last_recommended_job=info.get("last_job"),
            category=cat,
            best_match_job_id=m_info["job_id"] if m_info else None,
            best_match_job_title=m_info["job_title"] if m_info else None,
            best_match_company=m_info["company_name"] if m_info else None,
            best_match_score=m_info["match_score"] if m_info else None,
            best_match_application_url=m_info["application_url"] if m_info else None,
            best_match_url_status=m_info["verification_status"] if m_info else None,
            email_subject_preview=subject_preview,
            dispatch_readiness=readiness
        ))
    return results

@router.get("/{subscriber_id}/history", response_model=List[SubscriberSentEmailHistoryItem])
async def get_subscriber_history(subscriber_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch complete sent email audit trail for a specific subscriber."""
    query = (
        select(
            CandidateJobHistory,
            JobSnapshot.title.label("job_title"),
            JobSnapshot.company.label("company_name"),
            Campaign.name.label("campaign_name")
        )
        .join(JobSnapshot, CandidateJobHistory.job_id == JobSnapshot.id)
        .outerjoin(Campaign, CandidateJobHistory.campaign_id == Campaign.id)
        .where(CandidateJobHistory.subscriber_id == subscriber_id)
        .order_by(CandidateJobHistory.sent_at.desc())
    )
    res = await db.execute(query)
    rows = res.all()

    items = []
    for hist, j_title, comp_name, camp_name in rows:
        subject = f"Congratulations! Your Profile Has Been Shortlisted for the {j_title} Role"
        items.append(SubscriberSentEmailHistoryItem(
            id=hist.id,
            job_id=hist.job_id,
            job_title=j_title or "Target Role",
            company_name=comp_name or "SponsorAJobs Partner",
            campaign_id=hist.campaign_id,
            campaign_name=camp_name or f"Campaign #{hist.campaign_id}",
            match_score=hist.match_score,
            subject=subject,
            sent_at=hist.sent_at,
            status=hist.email_status or "SENT"
        ))
    return items
