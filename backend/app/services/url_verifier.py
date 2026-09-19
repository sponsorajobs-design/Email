import re
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from backend.app.models.job import JobSnapshot
from backend.app.core.config import settings
from backend.app.core.logging import verification_logger, log_audit

class URLVerifier:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        }

    @staticmethod
    def is_valid_url_syntax(url: str) -> bool:
        if not url:
            return False
        regex = re.compile(
            r'^(?:http|ftp)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain...
            r'localhost|' # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return re.match(regex, url.strip()) is not None

    async def verify_url(self, url: str) -> Dict[str, Any]:
        """Verify an individual URL with retries, status code analysis, and redirect tracing."""
        cleaned_url = (url or "").strip()
        if not self.is_valid_url_syntax(cleaned_url):
            return {
                "status": "DEAD",
                "http_status": None,
                "message": "Malformed or invalid URL syntax",
                "final_url": cleaned_url
            }

        retries = settings.JOB_URL_VERIFY_MAX_RETRIES
        timeout = settings.JOB_URL_VERIFY_TIMEOUT_SECONDS

        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(
                    headers=self.headers,
                    follow_redirects=True,
                    timeout=timeout,
                    verify=False  # Allow sites with self-signed or transient SSL issues
                ) as client:
                    response = await client.get(cleaned_url)
                    status_code = response.status_code
                    final_url = str(response.url)
                    redirected = str(cleaned_url) != final_url

                    # Check 2xx Success
                    if 200 <= status_code < 300:
                        status = "REDIRECTED" if redirected else "LIVE"
                        msg = f"URL is live (HTTP {status_code})"
                        if redirected:
                            msg += f" redirected to {final_url}"
                        return {
                            "status": status,
                            "http_status": status_code,
                            "message": msg,
                            "final_url": final_url
                        }

                    # Check 404 / 410 Permanent Dead
                    elif status_code in (404, 410):
                        return {
                            "status": "DEAD",
                            "http_status": status_code,
                            "message": f"Page not found / expired (HTTP {status_code})",
                            "final_url": final_url
                        }

                    # Check 403 Forbidden / Cloudflare Bot Protection
                    elif status_code == 403:
                        # 403 often indicates Cloudflare or anti-scraping rather than dead link
                        return {
                            "status": "UNKNOWN",
                            "http_status": status_code,
                            "message": "Access restricted by bot protection or requires browser session (HTTP 403)",
                            "final_url": final_url
                        }

                    # Check 429 Too Many Requests
                    elif status_code == 429:
                        if attempt < retries:
                            await asyncio.sleep(2 * (attempt + 1))
                            continue
                        return {
                            "status": "TEMPORARY_ERROR",
                            "http_status": status_code,
                            "message": "Rate limited by host (HTTP 429)",
                            "final_url": final_url
                        }

                    # 5xx Server Errors
                    elif status_code >= 500:
                        if attempt < retries:
                            await asyncio.sleep(1)
                            continue
                        return {
                            "status": "TEMPORARY_ERROR",
                            "http_status": status_code,
                            "message": f"Server error on destination host (HTTP {status_code})",
                            "final_url": final_url
                        }

                    else:
                        return {
                            "status": "UNKNOWN",
                            "http_status": status_code,
                            "message": f"Unhandled response status (HTTP {status_code})",
                            "final_url": final_url
                        }

            except (httpx.ConnectTimeout, httpx.ReadTimeout):
                if attempt < retries:
                    await asyncio.sleep(1)
                    continue
                return {
                    "status": "TEMPORARY_ERROR",
                    "http_status": None,
                    "message": f"Connection timed out after {timeout}s",
                    "final_url": cleaned_url
                }
            except httpx.ConnectError as e:
                return {
                    "status": "DEAD",
                    "http_status": None,
                    "message": f"DNS resolution or connection failure: {str(e)}",
                    "final_url": cleaned_url
                }
            except Exception as e:
                return {
                    "status": "UNKNOWN",
                    "http_status": None,
                    "message": f"Verification error: {str(e)}",
                    "final_url": cleaned_url
                }

        return {
            "status": "UNKNOWN",
            "http_status": None,
            "message": "Exceeded maximum verification attempts",
            "final_url": cleaned_url
        }

    async def verify_all_pending_jobs(self, db: AsyncSession, force: bool = False) -> Dict[str, Any]:
        """Verify all jobs that have never been checked or whose check has expired beyond TTL."""
        ttl_cutoff = datetime.utcnow() - timedelta(hours=settings.JOB_URL_VERIFY_TTL_HOURS)
        
        query = select(JobSnapshot)
        if not force:
            query = query.where(
                or_(
                    JobSnapshot.verification_status == "UNKNOWN",
                    JobSnapshot.verified_at == None,
                    JobSnapshot.verified_at < ttl_cutoff
                )
            )

        res = await db.execute(query)
        jobs = res.scalars().all()

        verified_count = 0
        live_count = 0
        dead_count = 0
        unknown_count = 0

        for job in jobs:
            result = await self.verify_url(job.application_url)
            job.verification_status = result["status"]
            job.verification_http_status = result["http_status"]
            job.verification_message = result["message"]
            job.final_url = result.get("final_url")
            job.verified_at = datetime.utcnow()

            verified_count += 1
            if result["status"] in ("LIVE", "REDIRECTED"):
                live_count += 1
            elif result["status"] == "DEAD":
                dead_count += 1
            else:
                unknown_count += 1

            verification_logger.info(
                f"Job ID={job.id} | Title='{job.title}' | Status={result['status']} | HTTP={result['http_status']}"
            )

        await db.commit()
        log_audit(
            actor="admin",
            action="VERIFY_URLS",
            details=f"Verified {verified_count} jobs: {live_count} LIVE/REDIRECTED, {dead_count} DEAD, {unknown_count} UNKNOWN/TEMP_ERROR"
        )

        return {
            "total_verified": verified_count,
            "live": live_count,
            "dead": dead_count,
            "unknown": unknown_count
        }

url_verifier = URLVerifier()
