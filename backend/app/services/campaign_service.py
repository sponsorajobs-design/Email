"""
Campaign Service
Orchestrates role-based job alert campaign generation enforcing:
1. MAXIMUM 1 JOB IN 1 EMAIL PER SUBSCRIBER PER UTC CALENDAR DAY
2. Complete active job inventory evaluation
3. Country filtering ('ALL' preserves all jobs; specific country filters jobs.country_code)
4. Deterministic single-job selection hierarchy (Relevance -> Freshness -> Quality -> Created -> source_job_id)
5. Zero irrelevant filler jobs (0 relevant jobs -> 0 queued emails)
6. Permanent subscriber-job deduplication (failed or delivered pairs never re-queued as new alerts)
7. Full email composition persistence with decision trace ("WHY THIS JOB?")
8. Safe review before dispatch (campaign staged in READY status, sent only on explicit dispatch)
"""

import json
import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.exc import IntegrityError
from backend.app.models.campaign import Campaign
from backend.app.models.email_queue import EmailQueueItem
from backend.app.models.email_composition import EmailComposition
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.models.match import CandidateJobHistory
from backend.app.models.unsubscribe import Unsubscribe
from backend.app.services.email_generator import email_generator
from backend.app.services.role_matcher import (
    evaluate_role_relevance,
    RoleMatchResult,
    clean_and_normalize,
    expand_abbreviations,
    strip_seniority_modifiers,
    expand_compound_branches,
    GENERIC_WORDS,
    NON_OCCUPATIONAL_INPUTS,
    CURATED_SYNONYMS,
)
from backend.app.core.config import settings
from backend.app.core.logging import app_logger, log_audit

def extract_job_tokens(title: str) -> Set[str]:
    """Extract occupational word tokens from job title and its compound branches."""
    tokens = set()
    for branch in expand_compound_branches(title):
        clean_no_paren = re.sub(r'\s*\([^)]*\)', '', branch)
        norm = clean_and_normalize(branch)
        norm_no_paren = clean_and_normalize(clean_no_paren)
        exp = expand_abbreviations(norm)
        base = strip_seniority_modifiers(exp)
        for s in (norm, norm_no_paren, exp, base):
            for w in s.split():
                tokens.add(w)
    return tokens

def extract_role_query_tokens(role: str) -> Set[str]:
    """Extract substantive query tokens for a subscriber preferred role and its curated synonyms."""
    norm_sub = clean_and_normalize(role)
    if not norm_sub or norm_sub in NON_OCCUPATIONAL_INPUTS or norm_sub in GENERIC_WORDS:
        return set()
    exp_sub = expand_abbreviations(norm_sub)
    base_sub = strip_seniority_modifiers(exp_sub)

    q_tokens = set()
    for s in (norm_sub, exp_sub, base_sub):
        for w in s.split():
            q_tokens.add(w)

    lookup_keys = [base_sub, exp_sub, norm_sub]
    for k in lookup_keys:
        if k in CURATED_SYNONYMS:
            for syn in CURATED_SYNONYMS[k]:
                norm_syn = clean_and_normalize(syn)
                base_syn = strip_seniority_modifiers(norm_syn)
                for s in (norm_syn, base_syn):
                    for w in s.split():
                        q_tokens.add(w)

    non_generic = q_tokens - GENERIC_WORDS
    return non_generic if non_generic else q_tokens

class CampaignService:
    _lock = asyncio.Lock()
    _is_generating = False
    _recent_generations: Dict[str, float] = {}

    @staticmethod
    def get_current_utc_date() -> str:
        """Returns the authoritative system-wide UTC calendar date (YYYY-MM-DD)."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    async def create_and_generate_campaign(
        self,
        db: AsyncSession,
        name: str,
        batch_size: Optional[int] = None,
        notes: Optional[str] = None,
        dry_run: bool = False,
        **kwargs
    ) -> Campaign:
        """
        Generates role-based job alert campaign items strictly enforcing:
        - One job in one email per subscriber per UTC calendar day.
        - Deterministic single-job ranking hierarchy.
        - Permanent subscriber-job deduplication.
        - Country and URL eligibility gating.
        - Full email composition records with decision traces.
        """
        # Guard: In-memory concurrency protection
        if self._is_generating:
            raise HTTPException(
                status_code=409,
                detail="A campaign generation is currently in progress. Please wait for it to complete."
            )

        # Guard: In-memory recent name check (within 60s)
        now_ts = datetime.utcnow().timestamp()
        if name in self._recent_generations and (now_ts - self._recent_generations[name]) < 60.0:
            raise HTTPException(
                status_code=409,
                detail=f"Campaign '{name}' was already created recently. Please refresh to view."
            )

        # Guard: Database in-progress GENERATING state
        recent_generating_res = await db.execute(
            select(Campaign).where(Campaign.status == "GENERATING")
        )
        if recent_generating_res.scalars().first():
            raise HTTPException(
                status_code=409,
                detail="A campaign is currently being generated. Please wait for it to finish."
            )

        # Guard: Accidental duplicate submission within last 60 seconds
        recent_cutoff = datetime.utcnow() - timedelta(seconds=60)
        recent_same_name = await db.execute(
            select(Campaign).where(
                Campaign.name == name,
                Campaign.created_at >= recent_cutoff
            )
        )
        if recent_same_name.scalars().first():
            raise HTTPException(
                status_code=409,
                detail=f"Campaign '{name}' was already created recently. Please refresh to view."
            )

        async with self._lock:
            self._is_generating = True
            try:
                return await self._execute_create_and_generate(
                    db=db,
                    name=name,
                    batch_size=batch_size,
                    notes=notes,
                    dry_run=dry_run,
                    **kwargs
                )
            except Exception as e:
                await db.rollback()
                log_audit(
                    actor="admin",
                    action="CAMPAIGN_FAILED",
                    result="FAILURE",
                    details=f"Campaign generation failed: {str(e)}"
                )
                raise
            finally:
                self._is_generating = False

    async def _execute_create_and_generate(
        self,
        db: AsyncSession,
        name: str,
        batch_size: Optional[int] = None,
        notes: Optional[str] = None,
        dry_run: bool = False,
        **kwargs
    ) -> Campaign:
        current_utc_date = self.get_current_utc_date()
        limit_size = min(batch_size or settings.DEFAULT_BATCH_SIZE, settings.MAX_CAMPAIGN_SIZE)

        campaign = Campaign(
            name=name,
            status="GENERATING",
            batch_size=limit_size,
            match_threshold=1,
            notes=notes or f"Role alert campaign for UTC date {current_utc_date}"
        )
        db.add(campaign)
        await db.flush()

        log_audit(
            actor="admin",
            action="CAMPAIGN_CREATED",
            details=f"Created campaign '{name}' (ID {campaign.id}) for UTC date {current_utc_date}."
        )

        # 1. Fetch active subscribers
        sub_res = await db.execute(
            select(SubscriberSnapshot).where(
                SubscriberSnapshot.subscription_status == "active"
            )
        )
        candidates = sub_res.scalars().all()

        # 2. Load unsubscribes
        unsub_res = await db.execute(select(Unsubscribe.email))
        unsub_emails = set(row[0].lower() for row in unsub_res.fetchall())

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        # 3. Load daily dispatch check: subscribers who already have an email queued/sent for today (UTC)
        today_queue_res = await db.execute(
            select(EmailQueueItem.subscriber_id).where(
                EmailQueueItem.dispatch_date == current_utc_date
            )
        )
        already_served_today: Set[int] = set(row[0] for row in today_queue_res.fetchall())

        # 4. Load permanent subscriber-job history & existing queue (burned pairs)
        hist_res = await db.execute(select(CandidateJobHistory.subscriber_id, CandidateJobHistory.job_id))
        burned_pairs: Set[Tuple[int, int]] = set((row[0], row[1]) for row in hist_res.fetchall())

        queue_pairs_res = await db.execute(select(EmailQueueItem.subscriber_id, EmailQueueItem.job_id))
        for row in queue_pairs_res.fetchall():
            burned_pairs.add((row[0], row[1]))

        # Load last successful dispatch per subscriber for weekly frequency gating
        last_sent_res = await db.execute(
            select(
                CandidateJobHistory.subscriber_id,
                func.max(CandidateJobHistory.sent_at)
            ).where(
                CandidateJobHistory.email_status == "SENT"
            ).group_by(CandidateJobHistory.subscriber_id)
        )
        last_sent_map: Dict[int, datetime] = {row[0]: row[1] for row in last_sent_res.fetchall()}

        queue_sent_res = await db.execute(
            select(
                EmailQueueItem.subscriber_id,
                func.max(EmailQueueItem.sent_at)
            ).where(
                EmailQueueItem.status == "SENT"
            ).group_by(EmailQueueItem.subscriber_id)
        )
        for s_id, q_sent in queue_sent_res.fetchall():
            if q_sent:
                prev = last_sent_map.get(s_id)
                if prev is None or q_sent > prev:
                    last_sent_map[s_id] = q_sent

        # Load last processing point for instant subscribers (to detect newly arrived jobs)
        last_processed_res = await db.execute(
            select(
                CandidateJobHistory.subscriber_id,
                func.max(CandidateJobHistory.created_at)
            ).group_by(CandidateJobHistory.subscriber_id)
        )
        last_processed_map: Dict[int, datetime] = {row[0]: row[1] for row in last_processed_res.fetchall()}

        # 5. Fetch complete active eligible job inventory
        # HARD ELIGIBILITY RULE:
        # A job MUST NOT be selected, queued, composed, or sent if the job has expired.
        # - source_status must not be expired, inactive, or closed
        # - closing_date (if present) must be strictly in the future (> now_utc)
        # - published_at must not be future-dated (published_at <= now_utc)
        # - Permitted URL statuses: LIVE, REDIRECTED, UNKNOWN, UNVERIFIED (TEMPORARY_ERROR and DEAD excluded)
        job_res = await db.execute(
            select(JobSnapshot).where(
                JobSnapshot.source_status == "active",
                JobSnapshot.source_status.notin_(["expired", "inactive", "closed"]),
                JobSnapshot.verification_status.in_(["LIVE", "REDIRECTED", "UNKNOWN", "UNVERIFIED"]),
                or_(JobSnapshot.published_at.is_(None), JobSnapshot.published_at <= now_utc),
                or_(JobSnapshot.closing_date.is_(None), JobSnapshot.closing_date > now_utc)
            )
        )
        all_jobs_raw: List[JobSnapshot] = job_res.scalars().all()

        # In-memory defensive verification: check exact timestamp against current UTC time
        from backend.app.services.role_matcher import NON_EMPLOYMENT_TITLE_KEYWORDS
        all_jobs: List[JobSnapshot] = []
        for j in all_jobs_raw:
            s_stat = (j.source_status or "").strip().lower()
            if s_stat in ("expired", "inactive", "closed"):
                continue
            exp_date = j.closing_date
            if exp_date is not None:
                exp_naive = exp_date.replace(tzinfo=None) if exp_date.tzinfo else exp_date
                if exp_naive <= now_utc:
                    continue
            j_title_lower = (j.title or "").lower()
            if any(bad_kw in j_title_lower for bad_kw in NON_EMPLOYMENT_TITLE_KEYWORDS):
                continue
            all_jobs.append(j)

        # Pre-index jobs by country for high-performance evaluation
        jobs_by_country: Dict[str, List[JobSnapshot]] = {}
        # Inverted index of jobs by token per country for role candidate lookup
        country_token_index: Dict[str, Dict[str, List[JobSnapshot]]] = {}
        all_token_index: Dict[str, List[JobSnapshot]] = {}

        for j in all_jobs:
            c_code = (j.country_code or "GB").strip().upper()
            jobs_by_country.setdefault(c_code, []).append(j)
            j_tokens = extract_job_tokens(j.title)
            c_idx = country_token_index.setdefault(c_code, {})
            for t in j_tokens:
                c_idx.setdefault(t, []).append(j)
                all_token_index.setdefault(t, []).append(j)

        total_queued = 0
        total_skipped = 0
        no_eligible_job_count = 0
        frequency_blocked_count = 0
        deduplicated_count = 0

        # Mapping for relevance level ordinal sorting
        # DIRECT (3) > VARIANT (2) > SYNONYM (1) > ALL_ROLES (0)
        level_map = {"DIRECT": 3, "VARIANT": 2, "SYNONYM": 1, "ALL_ROLES": 0}

        # Cache for role evaluation results per (target_role, job_id) across candidates
        role_eval_cache: Dict[Tuple[str, int], RoleMatchResult] = {}

        # Bulk persistence accumulators
        pending_queue_items: List[EmailQueueItem] = []
        pending_compositions_data: List[Dict[str, Any]] = []
        pending_history_entries: List[CandidateJobHistory] = []

        for sub in candidates:
            if total_queued >= limit_size:
                break

            # Quality Check 1: Unsubscribe
            if sub.is_unsubscribed or sub.email.lower() in unsub_emails:
                total_skipped += 1
                continue

            # Quality Check 2A: One job per subscriber per UTC calendar day (all frequencies)
            if sub.id in already_served_today:
                total_skipped += 1
                frequency_blocked_count += 1
                continue

            sub_freq = (sub.frequency or "daily").strip().lower()

            # Quality Check 2B: Weekly frequency check
            # - First-ever eligible dispatch = allowed
            # - Otherwise allowed only when last SUCCESSFUL dispatch is >= 7 days ago
            if sub_freq == "weekly":
                last_sent = last_sent_map.get(sub.id)
                if last_sent is not None:
                    last_sent_naive = last_sent.replace(tzinfo=None) if last_sent.tzinfo else last_sent
                    days_since_dispatch = (now_utc - last_sent_naive).total_seconds() / 86400.0
                    if days_since_dispatch < 7.0:
                        total_skipped += 1
                        frequency_blocked_count += 1
                        continue

            sub_country = (sub.country_code or "ALL").strip().upper()
            sub_loc = (sub.location or "").strip().lower()
            # If subscriber is in UK or country is GB, strictly enforce GB jobs!
            if "united kingdom" in sub_loc or "london" in sub_loc or "uk" in sub_loc.split() or sub_country == "GB":
                effective_country = "GB"
            else:
                effective_country = sub_country

            sub_roles_raw = (sub.preferred_roles or "").strip()
            is_all_roles = not sub_roles_raw or sub_roles_raw.lower() in ("all", "all roles")
            target_role_list = [r.strip() for r in sub_roles_raw.split(",") if r.strip()] if not is_all_roles else []

            # Filter candidate pool using effective country and inverted token index
            if is_all_roles:
                candidate_pool = all_jobs if effective_country == "ALL" else jobs_by_country.get(effective_country, [])
            else:
                sub_query_tokens: Set[str] = set()
                for target_role in target_role_list:
                    sub_query_tokens.update(extract_role_query_tokens(target_role))

                if not sub_query_tokens:
                    total_skipped += 1
                    no_eligible_job_count += 1
                    continue

                idx_source = all_token_index if effective_country == "ALL" else country_token_index.get(effective_country, {})
                candidate_jobs_set: Set[JobSnapshot] = set()
                for t in sub_query_tokens:
                    matched_jobs = idx_source.get(t)
                    if matched_jobs:
                        candidate_jobs_set.update(matched_jobs)

                candidate_pool = list(candidate_jobs_set)

            if not candidate_pool:
                total_skipped += 1
                no_eligible_job_count += 1
                continue

            # Quality Check 2C: Instant frequency check
            # Instant subscribers only consider NEW matching jobs that became available since previous processing point
            if sub_freq == "instant":
                last_proc = last_processed_map.get(sub.id)
                if last_proc is not None:
                    last_proc_naive = last_proc.replace(tzinfo=None) if last_proc.tzinfo else last_proc
                    new_jobs_only = []
                    for j in candidate_pool:
                        j_time = j.published_at or j.created_at or j.first_seen_at
                        j_time_naive = j_time.replace(tzinfo=None) if j_time and j_time.tzinfo else j_time
                        if j_time_naive and j_time_naive > last_proc_naive:
                            new_jobs_only.append(j)
                    candidate_pool = new_jobs_only
                    if not candidate_pool:
                        total_skipped += 1
                        no_eligible_job_count += 1
                        continue

            eligible_candidate_jobs: List[Tuple[int, JobSnapshot, str]] = []
            burned_match_count = 0

            for job in candidate_pool:
                # Role Relevance Check:
                if is_all_roles:
                    # All Roles subscriber: job qualifies with level 0
                    if (sub.id, job.id) in burned_pairs:
                        burned_match_count += 1
                        continue
                    eligible_candidate_jobs.append((0, job, "All Roles (no occupational restriction)"))
                else:
                    best_match_level = -1
                    best_reason = ""
                    for target_role in target_role_list:
                        cache_key = (target_role, job.id)
                        if cache_key in role_eval_cache:
                            match_res = role_eval_cache[cache_key]
                        else:
                            match_res = evaluate_role_relevance(
                                subscriber_role=target_role,
                                job_title=job.title,
                                category_id=job.category_id,
                                description=job.description
                            )
                            role_eval_cache[cache_key] = match_res

                        if match_res.is_relevant:
                            lvl = level_map.get(match_res.match_type, 0)
                            if lvl > best_match_level:
                                best_match_level = lvl
                                best_reason = match_res.matched_reason
                                if match_res.match_type == "DIRECT":
                                    break

                    if best_match_level > 0:
                        # Deduplication Check: Permanent subscriber-job exclusion
                        if (sub.id, job.id) in burned_pairs:
                            burned_match_count += 1
                            continue
                        eligible_candidate_jobs.append((best_match_level, job, best_reason))

            # If 0 relevant jobs: SEND ZERO (never send an irrelevant filler job!)
            if not eligible_candidate_jobs:
                total_skipped += 1
                if burned_match_count > 0:
                    deduplicated_count += 1
                else:
                    no_eligible_job_count += 1
                continue

            # Deterministic Single-Job Ranking Hierarchy:
            # 1. Relevance Level DESC (DIRECT=3 > VARIANT=2 > SYNONYM=1 > ALL_ROLES=0)
            # 2. Freshness DESC (published_at DESC capped to current UTC time)
            # 3. Quality DESC (quality_score DESC)
            # 4. Created Time DESC (created_at DESC)
            # 5. Deterministic Final Tie-Breaker ASC (source_job_id ASC)
            def job_ranking_key(item: Tuple[int, JobSnapshot, str]):
                lvl, j, _ = item
                raw_pub = j.published_at.timestamp() if j.published_at else (j.created_at.timestamp() if j.created_at else 0.0)
                pub_ts = min(raw_pub, now_utc.timestamp())
                q_score = j.quality_score if j.quality_score is not None else 50
                crt_ts = j.created_at.timestamp() if j.created_at else 0.0
                s_id = str(j.source_job_id or "")
                return (-lvl, -pub_ts, -q_score, -crt_ts, s_id)

            eligible_candidate_jobs.sort(key=job_ranking_key)
            top_level, selected_job, top_reason = eligible_candidate_jobs[0]

            match_type_label = (
                "DIRECT" if top_level == 3 else (
                    "VARIANT" if top_level == 2 else (
                        "SYNONYM" if top_level == 1 else "ALL ROLES"
                    )
                )
            )

            # Decision trace recording ("WHY THIS JOB?")
            decision_trace_data = {
                "subscriber": {
                    "id": sub.id,
                    "email": sub.email,
                    "role": sub_roles_raw or "All Roles",
                    "country": sub_country,
                    "frequency": sub_freq
                },
                "selected_job": {
                    "id": selected_job.id,
                    "source_job_id": selected_job.source_job_id,
                    "title": selected_job.title,
                    "company": selected_job.company,
                    "location": selected_job.location,
                    "country_code": selected_job.country_code or "GB",
                    "published_at": selected_job.published_at.isoformat() if selected_job.published_at else None,
                    "quality_score": selected_job.quality_score
                },
                "match_type": match_type_label,
                "ranking_position": 1,
                "total_eligible_jobs_found": len(eligible_candidate_jobs),
                "match_reason": top_reason,
                "excluded_alternatives": [
                    {
                        "job_id": alt_j.id,
                        "source_job_id": alt_j.source_job_id,
                        "title": alt_j.title,
                        "company": alt_j.company,
                        "match_type": "DIRECT" if alt_lvl == 3 else ("VARIANT" if alt_lvl == 2 else ("SYNONYM" if alt_lvl == 1 else "ALL ROLES")),
                        "reason": "Ranked lower in deterministic relevance/freshness hierarchy"
                    }
                    for alt_lvl, alt_j, _ in eligible_candidate_jobs[1:6]
                ]
            }

            if not dry_run:
                # Render single-job email
                target_role_display = sub_roles_raw if not is_all_roles else "All"
                rendered = email_generator.render_email(
                    candidate_name=sub.name,
                    subscriber_id=sub.id,
                    email=sub.email,
                    job_title=selected_job.title,
                    company=selected_job.company,
                    location=selected_job.location,
                    country_code=selected_job.country_code or "GB",
                    employment_type=selected_job.employment_type or "Full-time",
                    remote_type=selected_job.remote_type or "On-site",
                    sponsorship_label=selected_job.sponsorship_label or "Verified Visa Sponsor",
                    description=selected_job.description or "",
                    target_role=target_role_display,
                    source_job_id=selected_job.source_job_id,
                    match_score=top_level,
                    match_reasons=[top_reason]
                )

                queue_item = EmailQueueItem(
                    campaign_id=campaign.id,
                    subscriber_id=sub.id,
                    job_id=selected_job.id,
                    recipient=sub.email,
                    candidate_name=sub.name,
                    job_title=selected_job.title,
                    company_name=selected_job.company,
                    match_score=top_level,
                    subject=rendered["subject"],
                    html_body=rendered["html_body"],
                    text_body=rendered["text_body"],
                    dispatch_date=current_utc_date,
                    status="PENDING"
                )
                comp_dict = {
                    "campaign_id": campaign.id,
                    "subscriber_id": sub.id,
                    "job_id": selected_job.id,
                    "recipient": sub.email,
                    "candidate_name": sub.name,
                    "subject": rendered["subject"],
                    "rendered_html": rendered["html_body"],
                    "rendered_text": rendered["text_body"],
                    "template_version": rendered.get("template_version", "v2.0-role-alert"),
                    "role_used": sub_roles_raw or "All Roles",
                    "country_filter": sub_country,
                    "frequency": sub_freq,
                    "job_url": rendered["job_url"],
                    "decision_trace": json.dumps(decision_trace_data)
                }
                hist_entry = CandidateJobHistory(
                    subscriber_id=sub.id,
                    job_id=selected_job.id,
                    match_score=top_level,
                    email_status="PENDING",
                    campaign_id=campaign.id,
                    sent_at=None
                )
                pending_queue_items.append(queue_item)
                pending_compositions_data.append(comp_dict)
                pending_history_entries.append(hist_entry)

            # Mark served today and burn pair
            already_served_today.add(sub.id)
            burned_pairs.add((sub.id, selected_job.id))
            total_queued += 1

        # Bulk persist accumulated records in single transaction
        if not dry_run and pending_queue_items:
            db.add_all(pending_queue_items)
            await db.flush()  # Populates queue_item.id for all items in 1 batch round-trip

            compositions = []
            for q_item, comp_dict in zip(pending_queue_items, pending_compositions_data):
                comp_dict["queue_id"] = q_item.id
                compositions.append(EmailComposition(**comp_dict))

            db.add_all(compositions)
            db.add_all(pending_history_entries)

        campaign.total_candidates = len(candidates)
        campaign.total_matches = total_queued
        campaign.total_queued = total_queued
        campaign.emails_generated = total_queued
        campaign.total_skipped = total_skipped
        campaign.no_eligible_job_count = no_eligible_job_count
        campaign.frequency_blocked_count = frequency_blocked_count
        campaign.deduplicated_count = deduplicated_count
        campaign.status = "READY"

        if not dry_run:
            await db.commit()
        else:
            await db.rollback()

        log_audit(
            actor="admin",
            action="CAMPAIGN_GENERATED",
            details=(
                f"Campaign '{name}' (ID {campaign.id}): Generated {total_queued} emails, "
                f"skipped {total_skipped} (No eligible job: {no_eligible_job_count}, "
                f"Frequency blocked: {frequency_blocked_count}, Deduplicated: {deduplicated_count})."
            )
        )
        self._recent_generations[name] = datetime.utcnow().timestamp()
        return campaign

    async def approve_campaign(self, db: AsyncSession, campaign_id: int) -> Dict[str, Any]:
        """Admin gate: Explicitly approve a READY campaign for sending."""
        res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = res.scalars().first()
        if not campaign:
            return {"error": "Campaign not found"}

        if campaign.status != "READY":
            return {"error": f"Cannot approve campaign in status '{campaign.status}'"}

        campaign.status = "APPROVED"
        await db.commit()
        log_audit(
            actor="admin",
            action="APPROVE_CAMPAIGN",
            details=f"Campaign '{campaign.name}' (ID {campaign.id}) approved for transmission."
        )
        return {"status": "APPROVED", "campaign_id": campaign.id}

    async def dispatch_campaign(
        self,
        db: AsyncSession,
        campaign_id: int,
        batch_limit: int = 50
    ) -> Dict[str, Any]:
        """
        Controlled campaign dispatch:
        Transmits generated campaign queue records through the production SMTP queue.
        """
        from backend.app.services.email_sender import email_sender

        res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = res.scalars().first()
        if not campaign:
            return {"error": "Campaign not found"}

        if campaign.status not in ("READY", "APPROVED", "DISPATCHING", "SENDING"):
            return {"error": f"Cannot dispatch campaign in status '{campaign.status}'. Must be READY or APPROVED."}

        log_audit(
            actor="admin",
            action="CAMPAIGN_DISPATCHED",
            details=f"Admin initiated dispatch for Campaign '{campaign.name}' (ID {campaign.id})."
        )

        result = await email_sender.process_campaign_queue(
            db=db,
            campaign_id=campaign_id,
            batch_limit=batch_limit
        )
        return result

    async def cancel_campaign(self, db: AsyncSession, campaign_id: int) -> Dict[str, Any]:
        """Cancel an existing campaign and cancel any pending queue items."""
        res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = res.scalars().first()
        if not campaign:
            return {"error": "Campaign not found"}

        campaign.status = "CANCELLED"

        # Cancel pending emails
        q_res = await db.execute(
            select(EmailQueueItem).where(
                EmailQueueItem.campaign_id == campaign_id,
                EmailQueueItem.status.in_(["PENDING", "SENDING"])
            )
        )
        for item in q_res.scalars().all():
            item.status = "CANCELLED"

        await db.commit()
        log_audit(
            actor="admin",
            action="CANCEL_CAMPAIGN",
            details=f"Campaign '{campaign.name}' (ID {campaign.id}) was cancelled by administrator."
        )
        return {"status": "CANCELLED", "campaign_id": campaign.id}

campaign_service = CampaignService()
