import re
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.subscriber import SubscriberSnapshot
from backend.app.models.unsubscribe import Unsubscribe
from backend.app.services.supabase_service import supabase_service
from backend.app.core.logging import app_logger, log_audit

class SubscriberService:
    @staticmethod
    def normalize_tokens(text: Optional[str]) -> List[str]:
        if not text:
            return []
        parts = re.split(r"[,;|/]+", text)
        return [p.strip().lower() for p in parts if p.strip()]

    @staticmethod
    def is_valid_email(email: str) -> bool:
        if not email or "@" not in email:
            return False
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email.strip()))

    async def sync_subscribers(self, db: AsyncSession) -> Dict[str, Any]:
        """Fetch subscribers from Supabase read-only adapter and update local SQLite snapshot."""
        raw_subscribers = await supabase_service.fetch_subscribers()
        synced_count = 0
        updated_count = 0
        invalid_count = 0

        # Pre-fetch existing unsubscribe tokens to respect local opt-outs
        unsub_res = await db.execute(select(Unsubscribe.email))
        local_unsub_emails = set(row[0].lower() for row in unsub_res.fetchall())

        for data in raw_subscribers:
            email = str(data.get("email") or "").strip().lower()
            if not self.is_valid_email(email):
                invalid_count += 1
                continue

            is_unsubscribed = data.get("is_unsubscribed", False) or (email in local_unsub_emails)

            # Check if exists in local snapshot
            res = await db.execute(
                select(SubscriberSnapshot).where(SubscriberSnapshot.email == email)
            )
            existing = res.scalars().first()

            if existing:
                existing.name = data.get("name") or ""
                existing.preferred_roles = data.get("preferred_roles") or ""
                existing.location = data.get("location") or existing.location
                existing.country_code = data.get("country_code") or existing.country_code or "ALL"
                existing.frequency = data.get("frequency") or existing.frequency or "daily"
                existing.skills = data.get("skills") or existing.skills
                existing.experience_years = data.get("experience_years", existing.experience_years)
                existing.subscription_status = data.get("subscription_status", existing.subscription_status)
                existing.is_unsubscribed = is_unsubscribed
                updated_count += 1
            else:
                new_sub = SubscriberSnapshot(
                    source_subscriber_id=str(data.get("source_subscriber_id", "")),
                    name=str(data.get("name") or ""),
                    email=email,
                    preferred_roles=str(data.get("preferred_roles") or ""),
                    location=str(data.get("location") or ""),
                    country_code=str(data.get("country_code") or "ALL"),
                    frequency=str(data.get("frequency") or "daily"),
                    skills=str(data.get("skills") or ""),
                    experience_years=int(data.get("experience_years") or 0),
                    subscription_status=str(data.get("subscription_status") or "active"),
                    is_unsubscribed=is_unsubscribed
                )
                db.add(new_sub)
                synced_count += 1

        await db.commit()
        log_audit(
            actor="admin",
            action="SYNC_SUBSCRIBERS",
            details=f"Synced {synced_count} new, {updated_count} updated, {invalid_count} invalid emails."
        )
        return {
            "synced": synced_count,
            "updated": updated_count,
            "invalid": invalid_count,
            "total_processed": len(raw_subscribers)
        }

subscriber_service = SubscriberService()
