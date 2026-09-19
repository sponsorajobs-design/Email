from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend.app.core.database import get_db
from backend.app.models.unsubscribe import Unsubscribe
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.core.logging import app_logger, log_audit

router = APIRouter(tags=["Unsubscribe"])

@router.get("/api/unsubscribes")
async def list_unsubscribes(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Unsubscribe).order_by(Unsubscribe.id.desc()).limit(limit).offset(offset)
    )
    return res.scalars().all()

from backend.app.core.security import generate_unsubscribe_token

@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def process_unsubscribe(token: str, db: AsyncSession = Depends(get_db)):
    """Public unsubscribe link rendering a clean, respectful confirmation page."""
    # Check if this token was already recorded in Unsubscribe
    res = await db.execute(select(Unsubscribe).where(Unsubscribe.token == token))
    unsub = res.scalars().first()

    target_email = unsub.email if unsub else None

    # If no existing Unsubscribe record, find matching subscriber by token
    if not target_email:
        all_subs = (await db.execute(select(SubscriberSnapshot))).scalars().all()
        for s in all_subs:
            if generate_unsubscribe_token(s.id, s.email) == token:
                target_email = s.email
                s.is_unsubscribed = True
                break

    if target_email:
        await db.execute(
            update(SubscriberSnapshot)
            .where(SubscriberSnapshot.email == target_email)
            .values(is_unsubscribed=True)
        )
        if not unsub:
            unsub = Unsubscribe(
                email=target_email,
                token=token,
                reason="User clicked unsubscribe link in email"
            )
            db.add(unsub)
    else:
        if not unsub:
            unsub = Unsubscribe(
                email=f"optout-{token[:8]}@unsubscribed.local",
                token=token,
                reason="User clicked unsubscribe link in email"
            )
            db.add(unsub)

    await db.commit()

    log_audit(
        actor="subscriber",
        action="UNSUBSCRIBE",
        details=f"Token {token} processed."
    )

    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Unsubscribed - SponsorAJobs</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; color: #1e293b; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .card { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.06); max-width: 480px; text-align: center; border: 1px solid #e2e8f0; }
            h1 { font-size: 22px; color: #0f172a; margin-bottom: 12px; }
            p { font-size: 15px; color: #64748b; line-height: 1.6; margin-bottom: 24px; }
            .badge { display: inline-block; background: #ecfdf5; color: #059669; padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 13px; margin-bottom: 16px; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="badge">Preferences Updated</div>
            <h1>Unsubscribed Successfully</h1>
            <p>You have been safely unsubscribed from SponsorAJobs job recommendation emails. You will not receive further automated opportunity notifications from this system.</p>
        </div>
    </body>
    </html>
    """
