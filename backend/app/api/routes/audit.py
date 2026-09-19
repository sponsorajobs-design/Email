import re
from pathlib import Path
from fastapi import APIRouter, Depends, Query
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.database import get_db
from backend.app.models.audit_log import AuditLog
from backend.app.schemas.stats import AuditLogResponse
from backend.app.core.logging import LOGS_DIR

router = APIRouter(prefix="/audit-logs", tags=["Audit"])

@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    # Try querying the DB table first
    res = await db.execute(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(limit).offset(offset)
    )
    logs = res.scalars().all()
    if logs:
        return [
            AuditLogResponse(
                id=l.id,
                actor=l.actor,
                action=l.action,
                details=l.details,
                result=l.result,
                created_at=l.created_at.strftime("%Y-%m-%d %H:%M:%S") if l.created_at else ""
            )
            for l in logs
        ]

    # Fallback: Parse logs/audit.log if DB records haven't been committed yet
    log_file = LOGS_DIR / "audit.log"
    if not log_file.exists():
        return []

    results = []
    lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    for idx, line in enumerate(reversed(lines)):
        if "ACTOR=" in line and "ACTION=" in line:
            # Format: 2026-09-11 13:01:36 [INFO] [audit] ACTOR=admin | ACTION=SYNC_SUBSCRIBERS | RESULT=SUCCESS | DETAILS=...
            parts = line.split(" | ")
            time_part = line[:19]
            actor = "admin"
            action = "AUDIT"
            result = "SUCCESS"
            details = ""

            for p in parts:
                if "ACTOR=" in p:
                    actor = p.split("ACTOR=")[-1].strip()
                elif "ACTION=" in p:
                    action = p.split("ACTION=")[-1].strip()
                elif "RESULT=" in p:
                    result = p.split("RESULT=")[-1].strip()
                elif "DETAILS=" in p:
                    details = p.split("DETAILS=")[-1].strip()

            results.append(AuditLogResponse(
                id=idx + 1,
                actor=actor,
                action=action,
                details=details,
                result=result,
                created_at=time_part
            ))
            if len(results) >= limit:
                break

    return results
