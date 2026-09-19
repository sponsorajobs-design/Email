import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.app.core.config import settings
from backend.app.core.logging import app_logger

def sanitize_human_name(raw_name: Optional[str], email: str = "") -> str:
    """
    Returns a clean human name if valid.
    If the name contains digits, matches email handle, has underscores/dashes,
    or is generic ('Candidate', 'Subscriber', 'Applicant', 'None', 'User'), returns "".
    """
    if not raw_name:
        return ""
    name = raw_name.strip()
    # Check if empty or generic
    if name.lower() in ("candidate", "subscriber", "applicant", "user", "admin", "none", "unknown", "null", "test", "pro candidate"):
        return ""
    # Reject names containing digits (e.g. muhammadnoman1998uk, parameshvadde25, raj sum9)
    if any(ch.isdigit() for ch in name):
        return ""
    # Reject if it matches the email local part (before @)
    if email:
        local_part = email.split("@")[0].lower()
        clean_local = re.sub(r'[\.\_\-]+', '', local_part)
        clean_name = re.sub(r'[\.\_\-\s]+', '', name.lower())
        if clean_name == clean_local or clean_name in clean_local or clean_local in clean_name:
            if len(name.split()) < 2:
                return ""
    # Reject if name has symbols like @, _, /, \
    if re.search(r'[@\/\\_#\*\$\%]', name):
        return ""
    return name.title() if name.islower() or name.isupper() else name

def clean_role_list(raw_roles: List[str]) -> str:
    """
    Cleans, deduplicates, and removes braces/noise from role strings.
    Limits to top 3 clean canonical phrases.
    """
    cleaned = []
    seen = set()
    for r in raw_roles:
        if not r:
            continue
        # Remove curly braces, brackets, parentheses content if it's noise like { HR }
        r_clean = re.sub(r'[\{\}\[\]]', ' ', r)
        # Split on commas or ' or '
        parts = re.split(r'\s*,\s*|\s+or\s+', r_clean, flags=re.IGNORECASE)
        for part in parts:
            p = re.sub(r'\s+', ' ', part).strip()
            if not p or len(p) <= 2 or p.lower() in ('none', 'candidate', 'all', 'all roles', 'any', 'cu'):
                continue
            p_norm = p.lower()
            if p_norm not in seen:
                seen.add(p_norm)
                cleaned.append(p)
    return ", ".join(cleaned[:3])

class SupabaseService:
    """
    Dedicated read-only adapter for production Supabase.
    Strictly prohibits INSERT, UPDATE, DELETE or DDL.
    Provides mock fallback data when credentials are not configured.
    """

    def __init__(self):
        self.url = settings.SUPABASE_URL.strip() if settings.SUPABASE_URL else ""
        self.key = settings.SUPABASE_READONLY_KEY.strip() if settings.SUPABASE_READONLY_KEY else ""
        self.client = None
        self._init_client()

    def _init_client(self):
        if self.url and self.key:
            try:
                from supabase import create_client
                self.client = create_client(self.url, self.key)
                app_logger.info("Supabase client initialized with read-only credentials.")
            except Exception as e:
                app_logger.error(f"Failed to initialize Supabase client: {str(e)}")
                self.client = None
        else:
            app_logger.info("Supabase URL or Key not set. Operating in offline/mock mode.")

    def is_configured(self) -> bool:
        return bool(self.url and self.key and self.client)

    async def test_connection(self) -> Dict[str, Any]:
        """Test read-only connectivity to Supabase."""
        if not self.is_configured():
            return {
                "status": "offline_mode",
                "connected": False,
                "message": "Supabase credentials not configured in .env. Engine using offline mock data adapter."
            }
        try:
            # Check candidate_users or job_alerts or configured table
            table = settings.SUPABASE_SUBSCRIBER_TABLE or "candidate_users"
            res = self.client.table(table).select("id", count="exact").limit(1).execute()
            count = res.count if hasattr(res, "count") else len(res.data)
            return {
                "status": "connected",
                "connected": True,
                "table_tested": table,
                "count": count,
                "message": f"Successfully connected to Supabase table '{table}' with read-only permissions ({count} records available)."
            }
        except Exception as e:
            app_logger.error(f"Supabase connection test failed: {str(e)}")
            return {
                "status": "error",
                "connected": False,
                "error": str(e),
                "message": f"Failed to query Supabase: {str(e)}"
            }

    async def fetch_jobs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch active jobs using read-only queries from local SponsorAJobs database or Supabase."""
        import os
        import sqlite3
        from pathlib import Path
        jobs_db_path = getattr(settings, "JOBS_DB_PATH", r"C:\Users\Sumit Raj\OneDrive\jobs\local.sqlite")
        if os.path.exists(jobs_db_path):
            try:
                # Open with URI mode=ro for strict read-only guarantee
                conn = sqlite3.connect(f"file:{jobs_db_path}?mode=ro", uri=True)
                cur = conn.cursor()
                
                query = """
                    SELECT 
                        j.id,
                        j.source_job_id,
                        j.title, 
                        COALESCE(c.name, 'SponsorAJobs Partner') AS company_name, 
                        COALESCE(j.city, j.location, 'United Kingdom') AS location,
                        UPPER(COALESCE(j.country_code, 'GB')) AS country_code,
                        COALESCE(j.category_id, 'cat_general') AS category_id,
                        COALESCE(j.description_clean, j.description, '') AS description, 
                        COALESCE(j.remote_type, 'on-site') AS remote_type,
                        COALESCE(j.employment_type, 'Full-time') AS employment_type,
                        COALESCE(j.quality_score, 50) AS quality_score,
                        COALESCE(j.is_featured, 0) AS is_featured,
                        j.published_at,
                        j.first_seen_at,
                        COALESCE(j.sponsorship_label, 'Verified Sponsor') AS sponsorship_label,
                        COALESCE(j.sponsorship_score, 50) AS sponsorship_score,
                        j.apply_url, 
                        j.status
                    FROM jobs j
                    LEFT JOIN companies c ON j.company_id = c.id
                    WHERE j.status = 'active'
                """
                if limit:
                    query += f" LIMIT {int(limit)}"
                
                cur.execute(query)
                rows = cur.fetchall()
                conn.close()
                jobs = []
                for r in rows:
                    source_id = str(r[0] or r[1])
                    jobs.append({
                        "source_job_id": source_id,
                        "title": str(r[2] or "Unknown Title"),
                        "company": str(r[3] or "SponsorAJobs Partner"),
                        "location": str(r[4] or "United Kingdom"),
                        "country_code": str(r[5] or "GB").strip().upper(),
                        "category_id": str(r[6] or "").strip(),
                        "description": str(r[7] or ""),
                        "remote_type": str(r[8] or ""),
                        "requirements": "",
                        "skills": "",
                        "experience": "As specified in listing",
                        "employment_type": str(r[9] or "Full-time"),
                        "quality_score": int(r[10] or 50),
                        "is_featured": int(r[11] or 0),
                        "published_at": r[12],
                        "first_seen_at": r[13],
                        "sponsorship_label": str(r[14] or ""),
                        "sponsorship_score": int(r[15] or 50),
                        "application_url": str(r[16] or f"https://sponsorajobs.com/job/{source_id}"),
                        "apply_url": str(r[16] or ""),
                        "source_status": str(r[17] or "active"),
                        "verification_status": "LIVE"
                    })
                return jobs
            except Exception as e:
                app_logger.error(f"Error querying jobs from local.sqlite: {str(e)}")

        # Fallback to Supabase table if local sqlite unavailable
        if self.is_configured():
            try:
                table = settings.SUPABASE_JOB_TABLE or "jobs"
                q = self.client.table(table).select("*")
                if limit:
                    q = q.limit(limit)
                res = q.execute()
                if res.data:
                    return [self._map_job_record(r) for r in res.data]
            except Exception as e:
                app_logger.info(f"Supabase job table query error: {str(e)}")

        if not self.is_configured():
            return self._get_mock_jobs()
        return []

    async def fetch_subscribers(self, limit: int = 5000) -> List[Dict[str, Any]]:
        """Fetch eligible subscribers from Supabase candidate_users and job_alerts."""
        if not self.is_configured():
            return self._get_mock_subscribers()

        try:
            subscribers_by_email: Dict[str, Dict[str, Any]] = {}

            # 1. Try candidate_users from Supabase
            try:
                users_res = self.client.table("candidate_users").select("*").limit(limit).execute()
                for u in (users_res.data or []):
                    email = str(u.get("email") or "").strip().lower()
                    if not email or "@" not in email:
                        continue
                    prof = str(u.get("profession") or "").strip()
                    if prof.lower() in ("candidate", "none", "null"):
                        prof = ""
                    clean_prof = clean_role_list([prof]) if prof else ""

                    loc_raw = str(u.get("target_city") or u.get("location") or "").strip()
                    loc_lower = loc_raw.lower()

                    t_country = str(u.get("target_country") or "ALL").strip().upper()
                    if "united kingdom" in loc_lower or "london" in loc_lower or "uk" in loc_lower.split():
                        t_country = "GB"
                    elif t_country in ("ALL", "", "NONE"):
                        t_country = "ALL"
                    elif t_country == "UNITED KINGDOM":
                        t_country = "GB"
                    elif t_country == "UNITED STATES":
                        t_country = "US"

                    clean_name = sanitize_human_name(u.get("name"), email)

                    subscribers_by_email[email] = {
                        "source_subscriber_id": str(u.get("id") or ""),
                        "name": clean_name,
                        "email": email,
                        "preferred_roles": clean_prof,
                        "location": loc_raw or ("United Kingdom" if t_country == "GB" else ""),
                        "country_code": t_country,
                        "frequency": "daily",
                        "skills": "",
                        "experience_years": 0,
                        "subscription_status": "active" if u.get("is_active", True) else "inactive",
                        "is_unsubscribed": not u.get("is_active", True),
                    }
            except Exception as e:
                app_logger.warning(f"Could not fetch candidate_users: {str(e)}")

            # 2. Try job_alerts from Supabase
            try:
                alerts_res = self.client.table("job_alerts").select("*").limit(limit).execute()
                for a in (alerts_res.data or []):
                    email = str(a.get("email") or "").strip().lower()
                    if not email or "@" not in email:
                        continue
                    kw = str(a.get("keyword") or "").strip()
                    if kw.lower() in ("all", "all roles", "none"):
                        kw = ""
                    clean_kw = clean_role_list([kw]) if kw else ""

                    raw_country = str(a.get("country_code") or "ALL").strip().upper()
                    if raw_country in ("ALL", "", "NONE"):
                        c_code = "ALL"
                    elif raw_country == "UNITED KINGDOM":
                        c_code = "GB"
                    elif raw_country == "UNITED STATES":
                        c_code = "US"
                    else:
                        c_code = raw_country

                    freq = str(a.get("frequency") or "daily").strip().lower()
                    active = bool(a.get("active", 1))

                    if email in subscribers_by_email:
                        existing = subscribers_by_email[email]
                        if clean_kw:
                            merged_roles = clean_role_list([existing["preferred_roles"], clean_kw])
                            existing["preferred_roles"] = merged_roles
                        if c_code != "ALL" and existing.get("country_code") == "ALL":
                            existing["country_code"] = c_code
                    else:
                        # Job alert only - do not derive fake names from email handle!
                        subscribers_by_email[email] = {
                            "source_subscriber_id": str(a.get("id") or ""),
                            "name": "",  # Empty clean name so greeting falls back to 'Dear Candidate,'
                            "email": email,
                            "preferred_roles": clean_kw,
                            "location": c_code if c_code != "ALL" else "",
                            "country_code": c_code,
                            "frequency": freq,
                            "skills": "",
                            "experience_years": 0,
                            "subscription_status": "active" if active else "inactive",
                            "is_unsubscribed": not active,
                        }
            except Exception as e:
                app_logger.warning(f"Could not fetch job_alerts: {str(e)}")

            if subscribers_by_email:
                return list(subscribers_by_email.values())

            # Fallback to configured table if candidate_users / job_alerts weren't found
            table = settings.SUPABASE_SUBSCRIBER_TABLE or "subscribers"
            res = self.client.table(table).select("*").limit(limit).execute()
            raw_data = res.data or []
            return [self._map_subscriber_record(r) for r in raw_data]
        except Exception as e:
            app_logger.error(f"Error fetching subscribers from Supabase: {str(e)}")
            return []

    def _map_job_record(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Map heterogeneous schema columns to standardized job attributes."""
        source_id = str(raw.get("id") or raw.get("job_id") or raw.get("_id") or "")
        title = raw.get("title") or raw.get("job_title") or raw.get("position") or "Unknown Title"
        company = raw.get("company") or raw.get("company_name") or raw.get("employer") or "SponsorAJobs Partner"
        location = raw.get("location") or raw.get("city") or raw.get("job_location") or "United Kingdom"
        description = raw.get("description") or raw.get("job_description") or ""
        requirements = raw.get("requirements") or raw.get("qualifications") or ""
        
        # Skills could be array or comma-separated string
        raw_skills = raw.get("skills") or raw.get("required_skills") or raw.get("skills_needed") or ""
        if isinstance(raw_skills, list):
            skills = ", ".join(str(s) for s in raw_skills)
        else:
            skills = str(raw_skills)

        experience = str(raw.get("experience") or raw.get("experience_required") or raw.get("min_experience") or "2+ years")
        employment_type = raw.get("employment_type") or raw.get("job_type") or "Full-time"
        application_url = raw.get("application_url") or raw.get("apply_url") or raw.get("url") or raw.get("link") or ""
        status = str(raw.get("status") or raw.get("is_active") or "active").lower()
        if status in ("true", "1", "open", "live", "active"):
            status = "active"

        return {
            "source_job_id": source_id,
            "title": title,
            "company": company,
            "location": location,
            "description": str(description),
            "requirements": str(requirements),
            "skills": skills,
            "experience": experience,
            "employment_type": employment_type,
            "application_url": application_url,
            "source_status": status,
        }

    def _map_subscriber_record(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Map heterogeneous schema columns to standardized subscriber attributes."""
        source_id = str(raw.get("id") or raw.get("user_id") or raw.get("subscriber_id") or "")
        email = str(raw.get("email") or raw.get("user_email") or "").strip().lower()
        name = sanitize_human_name(raw.get("name") or raw.get("full_name") or raw.get("first_name"), email)
        
        # Roles
        roles_val = raw.get("preferred_role") or raw.get("preferred_roles") or raw.get("role") or raw.get("target_role") or ""
        if isinstance(roles_val, list):
            preferred_roles = clean_role_list(roles_val)
        else:
            preferred_roles = clean_role_list([str(roles_val)])

        location = raw.get("location") or raw.get("city") or raw.get("preferred_location") or "United Kingdom"
        
        # Skills
        skills_val = raw.get("skills") or raw.get("skills_list") or raw.get("tech_stack") or ""
        if isinstance(skills_val, list):
            skills = ", ".join(str(s) for s in skills_val)
        else:
            skills = str(skills_val)

        # Experience years parsing
        exp_raw = raw.get("experience") or raw.get("experience_years") or raw.get("years_experience") or raw.get("exp") or 0
        exp_years = 0
        if isinstance(exp_raw, int):
            exp_years = exp_raw
        elif isinstance(exp_raw, str):
            digits = re.findall(r"\d+", exp_raw)
            if digits:
                exp_years = int(digits[0])

        status = str(raw.get("subscription_status") or raw.get("status") or "active").lower()
        is_unsub = bool(raw.get("is_unsubscribed") or raw.get("unsubscribed") or raw.get("opt_out") or False)

        return {
            "source_subscriber_id": source_id,
            "name": name,
            "email": email,
            "preferred_roles": preferred_roles,
            "location": location,
            "skills": skills,
            "experience_years": exp_years,
            "subscription_status": status,
            "is_unsubscribed": is_unsub,
        }

    def _get_mock_jobs(self) -> List[Dict[str, Any]]:
        """Realistic mock jobs for offline/first-run demonstration."""
        return [
            {
                "source_job_id": "spj-101",
                "title": "Data Analyst",
                "company": "KPMG UK",
                "location": "London, UK",
                "description": "Visa sponsored Data Analyst role focusing on business intelligence, SQL models, and Power BI dashboards.",
                "requirements": "Proficiency with SQL, Python, Power BI, and 2+ years analytics experience.",
                "skills": "SQL, Python, Power BI, Tableau, Excel",
                "experience": "2+ years",
                "employment_type": "Full-time",
                "application_url": "https://www.google.com",  # Highly reliable URL for tests
                "source_status": "active"
            },
            {
                "source_job_id": "spj-102",
                "title": "Software Engineer",
                "company": "Revolut",
                "location": "London, UK (Hybrid)",
                "description": "Backend software engineer building high-scale financial services with Python, FastAPI, and PostgreSQL.",
                "requirements": "Experience with Python, APIs, distributed systems, Docker.",
                "skills": "Python, FastAPI, Docker, PostgreSQL, AWS",
                "experience": "3+ years",
                "employment_type": "Full-time",
                "application_url": "https://www.revolut.com",
                "source_status": "active"
            },
            {
                "source_job_id": "spj-103",
                "title": "Marketing Executive",
                "company": "Deliveroo",
                "location": "Manchester, UK",
                "description": "Growth and lifecycle marketing executive overseeing CRM campaigns and conversion analytics.",
                "requirements": "Email marketing, HubSpot, Google Analytics, copy creation.",
                "skills": "Email Marketing, HubSpot, SEO, Google Analytics, Copywriting",
                "experience": "2+ years",
                "employment_type": "Full-time",
                "application_url": "https://deliveroo.co.uk",
                "source_status": "active"
            },
            {
                "source_job_id": "spj-104",
                "title": "Cloud DevOps Engineer",
                "company": "Barclays",
                "location": "Northampton, UK",
                "description": "DevOps engineer building Terraform infrastructure and CI/CD automation pipelines with Visa sponsorship.",
                "requirements": "Terraform, Kubernetes, AWS, CI/CD pipelines.",
                "skills": "AWS, Kubernetes, Terraform, Docker, Python, Linux",
                "experience": "4+ years",
                "employment_type": "Full-time",
                "application_url": "https://www.barclays.co.uk",
                "source_status": "active"
            },
            {
                "source_job_id": "spj-105",
                "title": "Expired Test Role",
                "company": "Legacy Corp",
                "location": "Birmingham, UK",
                "description": "This is a closed position with an invalid link.",
                "requirements": "None",
                "skills": "Cobol, Fortran",
                "experience": "10 years",
                "employment_type": "Full-time",
                "application_url": "https://httpstat.us/404",  # Returns 404 for test
                "source_status": "active"
            },
            {
                "source_job_id": "spj-106",
                "title": "Product Manager",
                "company": "Monzo Bank",
                "location": "London, UK (Remote)",
                "description": "Lead cross-functional engineering squads building customer banking journeys.",
                "requirements": "Agile, product strategy, user research, data analysis.",
                "skills": "Product Strategy, Agile, Scrum, Roadmapping, SQL",
                "experience": "3+ years",
                "employment_type": "Full-time",
                "application_url": "https://monzo.com",
                "source_status": "active"
            },
            {
                "source_job_id": "spj-107",
                "title": "Financial Analyst",
                "company": "HSBC UK",
                "location": "London, UK",
                "description": "Corporate finance analyst evaluating commercial banking portfolios and risk models.",
                "requirements": "Financial modeling, Excel, accounting principles, CFA or ACA interest.",
                "skills": "Financial Modeling, Excel, Accounting, Audit, Forecasting",
                "experience": "2+ years",
                "employment_type": "Full-time",
                "application_url": "https://www.hsbc.co.uk",
                "source_status": "active"
            }
        ]

    def _get_mock_subscribers(self) -> List[Dict[str, Any]]:
        """Realistic mock subscribers for offline/first-run demonstration."""
        return [
            {
                "source_subscriber_id": "sub-1001",
                "name": "Priya Sharma",
                "email": "priya.sharma@example.com",
                "preferred_roles": "Data Analyst, BI Analyst",
                "location": "London",
                "skills": "SQL, Python, Power BI, Tableau",
                "experience_years": 3,
                "subscription_status": "active",
                "is_unsubscribed": False
            },
            {
                "source_subscriber_id": "sub-1002",
                "name": "Rahul Verma",
                "email": "rahul.verma@example.com",
                "preferred_roles": "Software Engineer, Backend Developer",
                "location": "London",
                "skills": "Python, FastAPI, Docker, PostgreSQL",
                "experience_years": 4,
                "subscription_status": "active",
                "is_unsubscribed": False
            },
            {
                "source_subscriber_id": "sub-1003",
                "name": "Ananya Patel",
                "email": "ananya.patel@example.com",
                "preferred_roles": "Marketing Executive, Digital Marketer",
                "location": "Manchester",
                "skills": "Email Marketing, HubSpot, SEO, Copywriting",
                "experience_years": 2,
                "subscription_status": "active",
                "is_unsubscribed": False
            },
            {
                "source_subscriber_id": "sub-1004",
                "name": "Vikram Singh",
                "email": "vikram.singh@example.com",
                "preferred_roles": "DevOps Engineer, Cloud Engineer",
                "location": "London",
                "skills": "AWS, Kubernetes, Terraform, Docker, Linux",
                "experience_years": 5,
                "subscription_status": "active",
                "is_unsubscribed": False
            },
            {
                "source_subscriber_id": "sub-1005",
                "name": "David Miller",
                "email": "david.miller@example.com",
                "preferred_roles": "Data Analyst",
                "location": "London",
                "skills": "SQL, Excel",
                "experience_years": 1,
                "subscription_status": "active",
                "is_unsubscribed": True  # Unsubscribed test case
            },
            {
                "source_subscriber_id": "sub-1006",
                "name": "Sophia Taylor",
                "email": "sophia.taylor@example.com",
                "preferred_roles": "Product Manager, Technical Product Manager",
                "location": "London",
                "skills": "Product Strategy, Agile, Scrum, Roadmapping, SQL",
                "experience_years": 4,
                "subscription_status": "active",
                "is_unsubscribed": False
            },
            {
                "source_subscriber_id": "sub-1007",
                "name": "Marcus O'Connor",
                "email": "marcus.oconnor@example.com",
                "preferred_roles": "Financial Analyst, Commercial Finance Analyst",
                "location": "London",
                "skills": "Financial Modeling, Excel, Accounting, Forecasting, Valuation",
                "experience_years": 3,
                "subscription_status": "active",
                "is_unsubscribed": False
            },
            {
                "source_subscriber_id": "sub-1008",
                "name": "Liam Chen",
                "email": "liam.chen@example.com",
                "preferred_roles": "Software Engineer, Full Stack Developer",
                "location": "London",
                "skills": "Python, React, TypeScript, FastAPI, Docker, PostgreSQL",
                "experience_years": 3,
                "subscription_status": "active",
                "is_unsubscribed": False
            }
        ]

supabase_service = SupabaseService()
