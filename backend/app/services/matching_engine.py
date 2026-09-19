"""
Role-Based Matching Engine
Replaces legacy candidate profile scoring with deterministic occupational role relevance.
Populates categorical match details and legacy compatibility scores.
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.models.match import CandidateJobMatch
from backend.app.core.config import settings
from backend.app.core.logging import matching_logger, log_audit
from backend.app.services.role_matcher import evaluate_role_relevance, RoleMatchResult

class MatchingEngine:
    """
    Evaluates role-based job relevance for subscribers.
    Categorical output: DIRECT, VARIANT, SYNONYM, or NONE.
    """

    def calculate_match(
        self,
        candidate: SubscriberSnapshot,
        job: JobSnapshot
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calculates role relevance between subscriber target roles and job listing.
        Returns legacy_score (3=DIRECT, 2=VARIANT, 1=SYNONYM, 0=NONE) and detailed breakdown.
        """
        # Geo eligibility gate
        sub_country = (candidate.country_code or "ALL").strip().upper()
        cand_loc = (candidate.location or "").strip().lower()
        job_country = (job.country_code or "GB").strip().upper()

        # If subscriber is in UK, strictly enforce GB jobs
        if ("united kingdom" in cand_loc or "uk" in cand_loc.split() or sub_country == "GB") and job_country != "GB":
            return 0, {
                "is_relevant": False,
                "match_type": "NONE",
                "reasons": [f"Country mismatch: subscriber requires UK/GB, job is '{job_country}'"],
                "role_score": 0,
                "legacy_score": 0
            }

        # If subscriber country is not ALL, must match job country
        if sub_country != "ALL" and sub_country != job_country:
            return 0, {
                "is_relevant": False,
                "match_type": "NONE",
                "reasons": [f"Country mismatch: subscriber requires '{sub_country}', job is '{job_country}'"],
                "role_score": 0,
                "legacy_score": 0
            }

        # Non-employment title gate
        from backend.app.services.role_matcher import NON_EMPLOYMENT_TITLE_KEYWORDS
        j_title_lower = (job.title or "").lower()
        for bad_kw in NON_EMPLOYMENT_TITLE_KEYWORDS:
            if bad_kw in j_title_lower:
                return 0, {
                    "is_relevant": False,
                    "match_type": "NONE",
                    "reasons": [f"Non-employment listing rejected: found '{bad_kw}' in '{job.title}'"],
                    "role_score": 0,
                    "legacy_score": 0
                }

        # URL / Status eligibility gate
        if job.verification_status in ("DEAD", "TEMPORARY_ERROR"):
            return 0, {
                "is_relevant": False,
                "match_type": "NONE",
                "reasons": [f"Job URL status ineligible ({job.verification_status})"],
                "role_score": 0,
                "legacy_score": 0
            }

        # Expiration eligibility gate
        if (job.source_status or "").strip().lower() in ("expired", "inactive", "closed"):
            return 0, {
                "is_relevant": False,
                "match_type": "NONE",
                "reasons": [f"Job is expired/inactive (status: '{job.source_status}')"],
                "role_score": 0,
                "legacy_score": 0
            }

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        if job.closing_date is not None:
            c_date = job.closing_date.replace(tzinfo=None) if job.closing_date.tzinfo else job.closing_date
            if c_date <= now_utc:
                return 0, {
                    "is_relevant": False,
                    "match_type": "NONE",
                    "reasons": [f"Job has expired on {job.closing_date}"],
                    "role_score": 0,
                    "legacy_score": 0
                }

        sub_roles = candidate.preferred_roles or ""
        # Handle "All Roles" subscription
        if not sub_roles.strip() or sub_roles.strip().lower() in ("all", "all roles"):
            return 1, {
                "is_relevant": True,
                "match_type": "ALL_ROLES",
                "reasons": ["Subscriber selected All Roles (no role restriction)"],
                "role_score": 1,
                "legacy_score": 1
            }

        # Check each target role against job title
        role_candidates = [r.strip() for r in sub_roles.split(",") if r.strip()]
        best_result: Optional[RoleMatchResult] = None

        for role_phrase in role_candidates:
            res = evaluate_role_relevance(
                subscriber_role=role_phrase,
                job_title=job.title,
                category_id=job.category_id,
                description=job.description
            )
            if res.is_relevant:
                if best_result is None or res.legacy_score > best_result.legacy_score:
                    best_result = res
                    if res.match_type == "DIRECT":
                        break  # Highest possible level reached

        if best_result and best_result.is_relevant:
            return best_result.legacy_score, {
                "is_relevant": True,
                "match_type": best_result.match_type,
                "reasons": [best_result.matched_reason],
                "role_score": best_result.legacy_score,
                "legacy_score": best_result.legacy_score
            }

        return 0, {
            "is_relevant": False,
            "match_type": "NONE",
            "reasons": [f"No occupational match for roles: {role_candidates} in '{job.title}'"],
            "role_score": 0,
            "legacy_score": 0
        }

    async def run_matching_cycle(self, db: AsyncSession, threshold: int = None) -> Dict[str, Any]:
        """Run role-relevance evaluation across active subscribers and eligible active jobs."""
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        sub_res = await db.execute(
            select(SubscriberSnapshot).where(
                SubscriberSnapshot.subscription_status == "active",
                SubscriberSnapshot.is_unsubscribed == False
            )
        )
        candidates = sub_res.scalars().all()

        job_res = await db.execute(
            select(JobSnapshot).where(
                JobSnapshot.source_status == "active",
                JobSnapshot.source_status.notin_(["expired", "inactive", "closed"]),
                JobSnapshot.verification_status.in_(["LIVE", "REDIRECTED", "UNKNOWN", "UNVERIFIED"]),
                or_(JobSnapshot.closing_date.is_(None), JobSnapshot.closing_date > now_utc)
            )
        )
        raw_jobs = job_res.scalars().all()
        from backend.app.services.role_matcher import NON_EMPLOYMENT_TITLE_KEYWORDS
        jobs = [j for j in raw_jobs if not any(bad_kw in (j.title or "").lower() for bad_kw in NON_EMPLOYMENT_TITLE_KEYWORDS)]
        gb_jobs = [j for j in jobs if (j.country_code or "GB").upper() == "GB"]

        # Clear existing matches
        await db.execute(delete(CandidateJobMatch))
        await db.commit()

        # Build token index over eligible jobs for rapid candidate retrieval
        from backend.app.services.campaign_service import extract_job_tokens, extract_role_query_tokens
        import asyncio

        token_to_jobs: Dict[str, List[JobSnapshot]] = {}
        for j in jobs:
            j_tokens = extract_job_tokens(j.title or "")
            for tok in j_tokens:
                if tok not in token_to_jobs:
                    token_to_jobs[tok] = []
                token_to_jobs[tok].append(j)

        total_evaluations = 0
        qualifying_matches = 0
        match_batch = []

        for idx, candidate in enumerate(candidates):
            # Yield to event loop periodically to prevent starving HTTP requests
            if idx % 20 == 0:
                await asyncio.sleep(0)

            sub_roles = (candidate.preferred_roles or "").strip()
            cand_loc = (candidate.location or "").lower()
            if "united kingdom" in cand_loc or "uk" in cand_loc.split() or candidate.country_code == "GB":
                cand_pool_source = gb_jobs
            else:
                cand_pool_source = jobs

            if not sub_roles or sub_roles.lower() in ("all", "all roles"):
                eval_jobs = cand_pool_source[:50]
            else:
                candidate_job_map: Dict[int, JobSnapshot] = {}
                for role_phrase in [r.strip() for r in sub_roles.split(",") if r.strip()]:
                    q_tokens = extract_role_query_tokens(role_phrase)
                    for tok in q_tokens:
                        for matched_job in token_to_jobs.get(tok, []):
                            candidate_job_map[matched_job.id] = matched_job
                eval_jobs = list(candidate_job_map.values())

            for job in eval_jobs:
                total_evaluations += 1
                score, details = self.calculate_match(candidate, job)

                if details.get("is_relevant"):
                    qualifying_matches += 1
                    match_record = CandidateJobMatch(
                        subscriber_id=candidate.id,
                        job_id=job.id,
                        match_score=score,
                        role_score=score,
                        skills_score=0,
                        experience_score=0,
                        location_score=0,
                        recency_score=0,
                        match_reasons="\n".join(details.get("reasons", [])),
                        matched_skills="",
                        unmatched_requirements=""
                    )
                    match_batch.append(match_record)

                    if len(match_batch) >= 500:
                        db.add_all(match_batch)
                        await db.commit()
                        match_batch = []
                        await asyncio.sleep(0)

        if match_batch:
            db.add_all(match_batch)
            await db.commit()

        log_audit(
            actor="admin",
            action="RUN_MATCHING",
            details=f"Evaluated {total_evaluations} pairs across {len(candidates)} subscribers and {len(jobs)} eligible jobs. Found {qualifying_matches} relevant matches."
        )

        return {
            "candidates_count": len(candidates),
            "jobs_count": len(jobs),
            "total_evaluations": total_evaluations,
            "qualifying_matches": qualifying_matches,
            "threshold_used": 1
        }

matching_engine = MatchingEngine()

