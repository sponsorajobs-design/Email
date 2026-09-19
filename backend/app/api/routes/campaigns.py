import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.database import get_db
from backend.app.models.campaign import Campaign
from backend.app.models.email_queue import EmailQueueItem
from backend.app.models.email_composition import EmailComposition
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.job import JobSnapshot
from backend.app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignPreviewItem,
    CampaignSubscriberItem,
    CampaignCompositionDetail,
    CategoryCampaignRequest,
    SendSelectedRequest,
    AudienceCategory,
    AudienceRecipient,
    CustomPreviewRequest,
    CustomPreviewResponse,
    DirectComposeSendRequest
)
from backend.app.services.campaign_service import campaign_service
from backend.app.services.email_generator import email_generator
from backend.app.services.email_sender import email_sender
from backend.app.services.categorization_service import categorization_service
from backend.app.core.config import settings
from backend.app.core.logging import app_logger, log_audit

router = APIRouter(tags=["Campaigns"])

CATEGORY_CONFIG = {
    "Civil, Construction & Architecture": {"display": "Civil Engineers & Construction", "icon": "🏗️"},
    "Product & Project Management": {"display": "Project & Product Managers", "icon": "📋"},
    "Software & Web Engineering": {"display": "Software & Web Developers", "icon": "💻"},
    "Data & Business Intelligence": {"display": "Data & BI Specialists", "icon": "📊"},
    "Cloud, DevOps & Infrastructure": {"display": "Cloud & DevOps Engineers", "icon": "☁️"},
    "Marketing, Growth & CRM": {"display": "Marketing & Growth", "icon": "📈"},
    "Finance, Accounting & Operations": {"display": "Finance & Operations", "icon": "💰"},
    "Human Resources & Talent": {"display": "Human Resources & Talent", "icon": "👥"},
    "General Professional": {"display": "General Professionals", "icon": "🌐"},
}

@router.get("/campaigns/audience-directory", response_model=List[AudienceCategory])
async def get_audience_directory(db: AsyncSession = Depends(get_db)):
    """
    Returns active subscribers organized by category, with full candidate details
    (names, emails, preferred roles) so the recruiter can select categories and view
    all associated emails with full granular control.
    """
    subs_res = await db.execute(
        select(SubscriberSnapshot).where(SubscriberSnapshot.is_unsubscribed == False)
    )
    subscribers = subs_res.scalars().all()

    grouped: dict[str, list[AudienceRecipient]] = {cat: [] for cat in CATEGORY_CONFIG}

    for sub in subscribers:
        cat = categorization_service.categorize_profile(sub.preferred_roles, sub.skills)
        if cat not in grouped:
            grouped[cat] = []
        
        display_name = (sub.name or "").strip()
        if not display_name:
            # Fallback to local part of email cleanly capitalized
            local_part = sub.email.split("@")[0].replace(".", " ").replace("_", " ").title()
            display_name = local_part if local_part else "Candidate"

        grouped[cat].append(AudienceRecipient(
            id=sub.id,
            name=display_name,
            email=sub.email,
            preferred_roles=sub.preferred_roles or "",
            location=sub.location or sub.country_code or "United Kingdom"
        ))

    result: List[AudienceCategory] = []
    for cat_name, cfg in CATEGORY_CONFIG.items():
        recipients = grouped.get(cat_name, [])
        result.append(AudienceCategory(
            category_name=cat_name,
            display_title=cfg["display"],
            icon=cfg["icon"],
            total_candidates=len(recipients),
            recipients=recipients
        ))

    return result

@router.post("/campaigns/preview-custom", response_model=CustomPreviewResponse)
async def preview_custom_email(payload: CustomPreviewRequest):
    """
    Generates a live, real-time preview of the email with the embedded application link,
    custom job title, company, and optional custom message.
    """
    rendered = email_generator.render_email(
        candidate_name="Candidate",
        subscriber_id=1,
        email="candidate@example.com",
        job_title=payload.job_title or "Position Title",
        company=payload.company_name or "SponsorAJobs Partner",
        location=payload.location or "United Kingdom",
        application_url=payload.job_link or "https://sponsorajobs.com/jobs",
        employment_type=payload.employment_type or "Full-time",
        custom_subject=payload.custom_subject,
        custom_message=payload.custom_message
    )
    return CustomPreviewResponse(
        subject=rendered["subject"],
        html_body=rendered["html_body"],
        text_body=rendered["text_body"],
        job_url=rendered["job_url"]
    )

@router.post("/campaigns/direct-send")
async def direct_send_campaign(
    payload: DirectComposeSendRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Directly compose and dispatch a targeted job alert email campaign embedding the exact provided link.
    Supports instant test sends to the recruiter or batch sending to chosen categories / candidate IDs.
    """
    if not payload.job_title or not payload.job_title.strip():
        raise HTTPException(status_code=400, detail="Job Title is required")
    if not payload.job_link or not payload.job_link.strip():
        raise HTTPException(status_code=400, detail="Job Link URL is required to embed into the email")

    # Format job link cleanly
    job_link = payload.job_link.strip()
    if not job_link.startswith("http://") and not job_link.startswith("https://"):
        job_link = f"https://{job_link}"

    # Handle Test Send
    if payload.is_test_send:
        test_email = (payload.test_recipient or settings.TEST_EMAIL_ADDRESS or settings.FROM_EMAIL).strip()
        rendered = email_generator.render_email(
            candidate_name="Admin Reviewer",
            subscriber_id=99999,
            email=test_email,
            job_title=payload.job_title,
            company=payload.company_name or "SponsorAJobs Partner",
            location=payload.location or "United Kingdom",
            application_url=job_link,
            employment_type=payload.employment_type or "Full-time",
            custom_subject=payload.custom_subject,
            custom_message=payload.custom_message
        )
        send_res = email_sender.send_single_message(
            recipient=test_email,
            subject=rendered["subject"],
            html_body=rendered["html_body"],
            text_body=rendered["text_body"],
            is_test=True
        )
        if not send_res.get("success"):
            raise HTTPException(status_code=500, detail=f"Failed to send test email: {send_res.get('error')}")
        
        return {
            "success": True,
            "mode": "TEST_SEND",
            "recipient": test_email,
            "subject": rendered["subject"],
            "message_id": send_res.get("message_id"),
            "message": f"Test email sent successfully to {test_email}!"
        }

    # Target Audience Selection
    selected_subscribers: List[SubscriberSnapshot] = []
    if payload.selected_subscriber_ids and len(payload.selected_subscriber_ids) > 0:
        res = await db.execute(
            select(SubscriberSnapshot).where(
                SubscriberSnapshot.id.in_(payload.selected_subscriber_ids),
                SubscriberSnapshot.is_unsubscribed == False
            )
        )
        selected_subscribers = res.scalars().all()
    elif payload.selected_categories and len(payload.selected_categories) > 0:
        res = await db.execute(
            select(SubscriberSnapshot).where(SubscriberSnapshot.is_unsubscribed == False)
        )
        all_active = res.scalars().all()
        target_cats = set(payload.selected_categories)
        for s in all_active:
            cat = categorization_service.categorize_profile(s.preferred_roles, s.skills)
            if cat in target_cats:
                selected_subscribers.append(s)
    else:
        # Default to all active subscribers if none explicitly specified
        res = await db.execute(
            select(SubscriberSnapshot).where(SubscriberSnapshot.is_unsubscribed == False)
        )
        selected_subscribers = res.scalars().all()

    if not selected_subscribers:
        raise HTTPException(status_code=400, detail="No active subscribers found for the selected audience.")

    # 1. Create JobSnapshot to guarantee referential integrity
    job = JobSnapshot(
        source_job_id=f"direct-{uuid.uuid4().hex[:8]}",
        title=payload.job_title,
        company=payload.company_name or "SponsorAJobs Partner",
        location=payload.location or "United Kingdom",
        application_url=job_link,
        apply_url=job_link,
        employment_type=payload.employment_type or "Full-time",
        source_status="active",
        verification_status="LIVE",
        published_at=datetime.utcnow(),
        first_seen_at=datetime.utcnow()
    )
    db.add(job)
    await db.flush()

    # 2. Create Campaign Record
    category_summary = ", ".join(payload.selected_categories) if payload.selected_categories else "Custom Selection"
    camp_name = f"Job Alert: {payload.job_title} [{category_summary}] ({datetime.utcnow().strftime('%d %b %H:%M')})"
    campaign = Campaign(
        name=camp_name,
        status="SENDING",
        total_candidates=len(selected_subscribers),
        total_matches=len(selected_subscribers),
        total_queued=len(selected_subscribers),
        total_sent=0,
        total_failed=0,
        total_skipped=0,
        emails_generated=len(selected_subscribers),
        batch_size=len(selected_subscribers),
        match_threshold=70,
        notes=f"Target: {category_summary} | Link: {job_link}",
        created_at=datetime.utcnow(),
        started_at=datetime.utcnow()
    )
    db.add(campaign)
    await db.flush()

    # 3. Stage EmailQueueItems and EmailCompositions
    queued_items: List[EmailQueueItem] = []
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for sub in selected_subscribers:
        rendered = email_generator.render_email(
            candidate_name=sub.name or "Candidate",
            subscriber_id=sub.id,
            email=sub.email,
            job_title=payload.job_title,
            company=payload.company_name or "SponsorAJobs Partner",
            location=payload.location or "United Kingdom",
            application_url=job_link,
            employment_type=payload.employment_type or "Full-time",
            custom_subject=payload.custom_subject,
            custom_message=payload.custom_message
        )

        q_item = EmailQueueItem(
            campaign_id=campaign.id,
            subscriber_id=sub.id,
            job_id=job.id,
            dispatch_date=f"{now_str}#c{campaign.id}#{sub.id}",
            recipient=sub.email,
            candidate_name=sub.name or "Candidate",
            job_title=payload.job_title,
            company_name=payload.company_name or "SponsorAJobs Partner",
            match_score=95,
            subject=rendered["subject"],
            html_body=rendered["html_body"],
            text_body=rendered["text_body"],
            status="PENDING"
        )
        db.add(q_item)
        queued_items.append(q_item)

    await db.flush()

    for q_item, sub in zip(queued_items, selected_subscribers):
        comp = EmailComposition(
            campaign_id=campaign.id,
            queue_id=q_item.id,
            subscriber_id=sub.id,
            job_id=job.id,
            recipient=sub.email,
            candidate_name=sub.name or "Candidate",
            subject=q_item.subject,
            rendered_html=q_item.html_body,
            rendered_text=q_item.text_body,
            template_version="v3.1-recruiter-direct",
            role_used=payload.job_title,
            country_filter="GB",
            frequency=sub.frequency or "DAILY",
            job_url=job_link,
            decision_trace=json.dumps({"trigger": "direct_compose", "categories": payload.selected_categories})
        )
        db.add(comp)

    await db.commit()

    # 4. Dispatch queued items via SMTP
    sent_count = 0
    failed_count = 0
    errors: List[str] = []

    for q_item in queued_items:
        try:
            send_res = email_sender.send_single_message(
                recipient=q_item.recipient,
                subject=q_item.subject,
                html_body=q_item.html_body,
                text_body=q_item.text_body,
                is_test=False
            )
            if send_res.get("success"):
                q_item.status = "SENT"
                q_item.sent_at = datetime.utcnow()
                q_item.message_id = send_res.get("message_id")
                sent_count += 1
            else:
                q_item.status = "FAILED"
                err = send_res.get("error") or "Delivery failed"
                q_item.error_message = err
                failed_count += 1
                errors.append(f"{q_item.recipient}: {err}")
        except Exception as ex:
            q_item.status = "FAILED"
            q_item.error_message = str(ex)
            failed_count += 1
            errors.append(f"{q_item.recipient}: {str(ex)}")

    campaign.total_sent = sent_count
    campaign.total_failed = failed_count
    campaign.status = "COMPLETED" if sent_count > 0 else ("FAILED" if failed_count > 0 else "COMPLETED")
    campaign.completed_at = datetime.utcnow()

    await db.commit()

    log_audit(
        action="DIRECT_CAMPAIGN_DISPATCHED",
        actor="Recruiter",
        details=f"Campaign #{campaign.id} '{payload.job_title}' dispatched: {sent_count} sent, {failed_count} failed"
    )

    return {
        "success": True,
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "job_title": payload.job_title,
        "embedded_link": job_link,
        "total_recipients": len(selected_subscribers),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "errors": errors[:5],
        "message": f"Campaign dispatched! {sent_count} emails delivered successfully via domain SMTP."
    }

@router.get("/campaigns", response_model=List[CampaignResponse])
@router.get("/admin/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Campaign).order_by(Campaign.id.desc()).limit(limit).offset(offset)
    )
    return res.scalars().all()

@router.post("/campaigns", response_model=CampaignResponse)
@router.post("/admin/campaigns", response_model=CampaignResponse)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db)
):
    campaign = await campaign_service.create_and_generate_campaign(
        db=db,
        name=payload.name,
        match_threshold=payload.match_threshold,
        batch_size=payload.batch_size,
        notes=payload.notes,
        category=payload.category
    )
    return campaign

@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
@router.get("/admin/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = res.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.get("/campaigns/{campaign_id}/subscribers", response_model=List[CampaignSubscriberItem])
@router.get("/admin/campaigns/{campaign_id}/subscribers", response_model=List[CampaignSubscriberItem])
@router.get("/campaigns/{campaign_id}/items", response_model=List[CampaignSubscriberItem])
@router.get("/admin/campaigns/{campaign_id}/items", response_model=List[CampaignSubscriberItem])
async def get_campaign_subscribers(
    campaign_id: int,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns individual subscriber rows for a campaign:
    Subscriber -> selected role -> selected job -> email subject -> queue status -> SMTP status.
    """
    query = (
        select(
            EmailQueueItem,
            EmailComposition.id.label("comp_id"),
            EmailComposition.job_url,
            EmailComposition.decision_trace,
            SubscriberSnapshot.preferred_roles,
            SubscriberSnapshot.country_code.label("sub_country"),
            SubscriberSnapshot.frequency.label("sub_frequency"),
            JobSnapshot.source_job_id,
            JobSnapshot.location.label("job_location")
        )
        .outerjoin(EmailComposition, EmailComposition.queue_id == EmailQueueItem.id)
        .outerjoin(SubscriberSnapshot, SubscriberSnapshot.id == EmailQueueItem.subscriber_id)
        .outerjoin(JobSnapshot, JobSnapshot.id == EmailQueueItem.job_id)
        .where(EmailQueueItem.campaign_id == campaign_id)
        .order_by(EmailQueueItem.id.asc())
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(query)
    items = []
    for row in res.all():
        q_item = row[0]
        comp_id = row[1]
        job_url = row[2] or f"https://sponsorajobs.com/jobs/{row[7]}"
        trace_str = row[3]
        pref_roles = row[4]
        sub_country = row[5]
        sub_freq = row[6]
        source_job_id = row[7]
        job_loc = row[8]

        match_type = "DIRECT"
        if trace_str:
            try:
                trace_json = json.loads(trace_str)
                match_type = trace_json.get("match_type", "DIRECT")
            except Exception:
                pass

        items.append(CampaignSubscriberItem(
            queue_id=q_item.id,
            composition_id=comp_id,
            subscriber_id=q_item.subscriber_id,
            subscriber_name=q_item.candidate_name or "Subscriber",
            subscriber_email=q_item.recipient,
            preferred_roles=pref_roles,
            country_code=sub_country,
            frequency=sub_freq,
            job_id=q_item.job_id,
            source_job_id=source_job_id,
            job_title=q_item.job_title or "Opportunity",
            company_name=q_item.company_name or "Partner",
            location=job_loc,
            job_url=job_url,
            email_subject=q_item.subject,
            queue_status=q_item.status,
            smtp_status="SENT" if q_item.status == "SENT" else ("FAILED" if q_item.status == "FAILED" else None),
            message_id=q_item.message_id,
            sent_at=q_item.sent_at,
            error_message=q_item.error_message,
            match_type=match_type
        ))
    return items

@router.get("/campaigns/{campaign_id}/compositions/{composition_id}", response_model=CampaignCompositionDetail)
@router.get("/admin/campaigns/{campaign_id}/compositions/{composition_id}", response_model=CampaignCompositionDetail)
async def get_campaign_composition(
    campaign_id: int,
    composition_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns full permanent email composition record and decision trace for inspection.
    """
    res = await db.execute(
        select(EmailComposition).where(
            EmailComposition.id == composition_id,
            EmailComposition.campaign_id == campaign_id
        )
    )
    comp = res.scalars().first()
    if not comp:
        raise HTTPException(status_code=404, detail="Email composition not found")

    parsed_trace = None
    if comp.decision_trace:
        try:
            parsed_trace = json.loads(comp.decision_trace)
        except Exception:
            parsed_trace = {"raw": comp.decision_trace}

    return CampaignCompositionDetail(
        id=comp.id,
        campaign_id=comp.campaign_id,
        queue_id=comp.queue_id,
        subscriber_id=comp.subscriber_id,
        job_id=comp.job_id,
        recipient=comp.recipient,
        candidate_name=comp.candidate_name,
        subject=comp.subject,
        rendered_html=comp.rendered_html,
        rendered_text=comp.rendered_text,
        template_version=comp.template_version,
        role_used=comp.role_used,
        country_filter=comp.country_filter,
        frequency=comp.frequency,
        job_url=comp.job_url,
        decision_trace=parsed_trace,
        created_at=comp.created_at
    )

@router.get("/campaigns/{campaign_id}/preview", response_model=List[CampaignPreviewItem])
@router.get("/admin/campaigns/{campaign_id}/preview", response_model=List[CampaignPreviewItem])
async def preview_campaign(
    campaign_id: int,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(EmailQueueItem, JobSnapshot.verification_status)
        .join(JobSnapshot, EmailQueueItem.job_id == JobSnapshot.id)
        .where(EmailQueueItem.campaign_id == campaign_id)
        .limit(limit)
    )
    res = await db.execute(query)
    items = []
    for queue_item, url_status in res.all():
        items.append(CampaignPreviewItem(
            queue_id=queue_item.id,
            subscriber_id=queue_item.subscriber_id,
            job_id=queue_item.job_id,
            candidate_name=queue_item.candidate_name or "Candidate",
            candidate_email=queue_item.recipient,
            job_title=queue_item.job_title or "Role",
            company_name=queue_item.company_name or "Company",
            match_score=queue_item.match_score,
            url_status=url_status,
            status=queue_item.status,
            subject=queue_item.subject,
            html_preview=queue_item.html_body
        ))
    return items

@router.post("/campaigns/{campaign_id}/dispatch")
@router.post("/admin/campaigns/{campaign_id}/dispatch")
@router.post("/campaigns/{campaign_id}/send")
@router.post("/admin/campaigns/{campaign_id}/send")
async def dispatch_campaign(
    campaign_id: int,
    batch_limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db)
):
    result = await campaign_service.dispatch_campaign(
        db=db,
        campaign_id=campaign_id,
        batch_limit=batch_limit
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/campaigns/{campaign_id}/items/{queue_id}/send")
@router.post("/admin/campaigns/{campaign_id}/items/{queue_id}/send")
async def send_single_campaign_item(
    campaign_id: int,
    queue_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Send an individual verified email immediately from the preview or table.
    """
    result = await email_sender.send_single_queue_item(db=db, queue_id=queue_id)
    if not result.get("success") and not result.get("already_sent"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send email"))
    return result

@router.post("/campaigns/{campaign_id}/send-selected")
@router.post("/admin/campaigns/{campaign_id}/send-selected")
async def send_selected_campaign_items(
    campaign_id: int,
    payload: SendSelectedRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send an arbitrary subset of verified candidate emails selected by the admin.
    """
    result = await email_sender.send_selected_queue_items(
        db=db,
        queue_ids=payload.queue_ids
    )
    return result

@router.post("/campaigns/{campaign_id}/approve")
@router.post("/admin/campaigns/{campaign_id}/approve")
async def approve_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    result = await campaign_service.approve_campaign(db, campaign_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/campaigns/{campaign_id}/cancel")
@router.post("/admin/campaigns/{campaign_id}/cancel")
async def cancel_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    result = await campaign_service.cancel_campaign(db, campaign_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/campaigns/send-category")
async def send_category_campaign(
    payload: CategoryCampaignRequest,
    db: AsyncSession = Depends(get_db)
):
    from datetime import datetime
    name = f"Alerts: {payload.category} ({datetime.utcnow().strftime('%d %b %H:%M')})"
    campaign = await campaign_service.create_and_generate_campaign(
        db=db,
        name=name,
        match_threshold=payload.match_threshold,
        batch_size=payload.batch_size,
        category=payload.category,
        notes=f"Auto-generated category campaign for {payload.category}"
    )

    sent_result = None
    if payload.auto_send and campaign.total_queued > 0:
        sent_result = await campaign_service.dispatch_campaign(
            db=db,
            campaign_id=campaign.id,
            batch_limit=payload.batch_size or 50
        )

    return {
        "campaign": campaign,
        "sent_result": sent_result,
        "queued": campaign.total_queued,
        "message": f"Successfully created campaign for category '{payload.category}' with {campaign.total_queued} emails queued."
    }
