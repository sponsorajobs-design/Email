from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend.app.models.job import JobSnapshot
from backend.app.services.supabase_service import supabase_service
from backend.app.core.logging import app_logger, log_audit

class JobService:
    async def sync_jobs(self, db: AsyncSession, limit: Optional[int] = None) -> Dict[str, Any]:
        """Fetch all active jobs from SponsorAJobs read-only database and update local SQLite snapshot."""
        raw_jobs = await supabase_service.fetch_jobs(limit=limit)
        synced_count = 0
        updated_count = 0

        # Load existing jobs indexed by source_job_id for fast in-memory lookup
        existing_res = await db.execute(
            select(JobSnapshot.source_job_id, JobSnapshot)
        )
        existing_map = {row[0]: row[1] for row in existing_res.all()}

        new_jobs = []
        for data in raw_jobs:
            source_id = str(data.get("source_job_id", "")).strip()
            if not source_id:
                continue

            pub_date = data.get("published_at")
            if isinstance(pub_date, str):
                try:
                    pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pub_date = datetime.utcnow()
            elif not isinstance(pub_date, datetime):
                pub_date = datetime.utcnow()

            first_seen = data.get("first_seen_at")
            if isinstance(first_seen, str):
                try:
                    first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    first_seen = datetime.utcnow()
            elif not isinstance(first_seen, datetime):
                first_seen = datetime.utcnow()

            existing = existing_map.get(source_id)
            if existing:
                existing.title = data.get("title") or existing.title
                existing.company = data.get("company") or existing.company
                existing.location = data.get("location") or existing.location
                existing.country_code = data.get("country_code") or existing.country_code
                existing.category_id = data.get("category_id") or existing.category_id
                existing.remote_type = data.get("remote_type") or existing.remote_type
                existing.description = data.get("description") or existing.description
                existing.employment_type = data.get("employment_type") or existing.employment_type
                existing.application_url = data.get("application_url") or existing.application_url
                existing.apply_url = data.get("apply_url") or existing.apply_url
                existing.source_status = data.get("source_status") or existing.source_status
                existing.quality_score = data.get("quality_score", existing.quality_score)
                existing.is_featured = data.get("is_featured", existing.is_featured)
                existing.published_at = pub_date
                existing.first_seen_at = first_seen
                existing.sponsorship_label = data.get("sponsorship_label") or existing.sponsorship_label
                existing.sponsorship_score = data.get("sponsorship_score", existing.sponsorship_score)
                updated_count += 1
            else:
                new_job = JobSnapshot(
                    source_job_id=source_id,
                    title=str(data.get("title") or "Unknown Position"),
                    company=str(data.get("company") or "SponsorAJobs Partner"),
                    location=str(data.get("location") or "United Kingdom"),
                    country_code=str(data.get("country_code") or "GB"),
                    category_id=str(data.get("category_id") or "cat_general"),
                    remote_type=str(data.get("remote_type") or ""),
                    description=str(data.get("description") or ""),
                    requirements="",
                    skills="",
                    experience="As specified in listing",
                    employment_type=str(data.get("employment_type") or "Full-time"),
                    application_url=str(data.get("application_url") or ""),
                    apply_url=str(data.get("apply_url") or ""),
                    source_status=str(data.get("source_status") or "active"),
                    quality_score=int(data.get("quality_score") or 50),
                    is_featured=int(data.get("is_featured") or 0),
                    published_at=pub_date,
                    first_seen_at=first_seen,
                    sponsorship_label=str(data.get("sponsorship_label") or "Verified Sponsor"),
                    sponsorship_score=int(data.get("sponsorship_score") or 50),
                    verification_status="LIVE"  # Active source inventory default
                )
                new_jobs.append(new_job)
                synced_count += 1

                if len(new_jobs) >= 500:
                    db.add_all(new_jobs)
                    await db.commit()
                    new_jobs = []

        deactivated_count = 0
        # Safe reconciliation: If performing a full inventory sync (limit is None),
        # any previously active job absent from the authoritative active source inventory
        # must be deactivated so it is excluded from future alert campaigns.
        if limit is None:
            seen_source_ids = set(str(d.get("source_job_id", "")).strip() for d in raw_jobs if d.get("source_job_id"))
            for sid, existing_job in existing_map.items():
                if existing_job.source_status == "active" and sid not in seen_source_ids:
                    existing_job.source_status = "inactive"
                    deactivated_count += 1

        if new_jobs:
            db.add_all(new_jobs)
            await db.commit()
        else:
            await db.commit()

        log_audit(
            actor="admin",
            action="SYNC_JOBS",
            details=f"Synced {synced_count} new jobs, {updated_count} updated jobs, {deactivated_count} deactivated jobs from full active inventory."
        )
        return {
            "synced": synced_count,
            "updated": updated_count,
            "deactivated": deactivated_count,
            "total_processed": len(raw_jobs)
        }

job_service = JobService()
