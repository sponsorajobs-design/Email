from pathlib import Path
import re
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader
from backend.app.core.config import settings
from backend.app.core.security import generate_unsubscribe_token

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

TEMPLATE_VERSION = "v3.1-recruiter-direct"

class EmailGenerator:
    RECRUITER_NAMES = [
        "Sarah Jenkins",
        "James Wilson",
        "Emma Davies",
        "David Miller",
        "Sophie Clark",
        "Oliver Taylor",
        "Rachel Evans",
        "Alex Morgan"
    ]

    @classmethod
    def get_hr_name(cls, subscriber_id: Optional[int] = None) -> str:
        if subscriber_id is not None:
            return cls.RECRUITER_NAMES[abs(subscriber_id) % len(cls.RECRUITER_NAMES)]
        import random
        return random.choice(cls.RECRUITER_NAMES)

    @staticmethod
    def generate_subject(role_name: str) -> str:
        """
        Generate authentic, direct recruiter subject line:
        'Your profile has been shortlisted for the {ROLE_NAME} position'
        """
        clean_role = (role_name or "Role").strip()
        # Remove trailing parentheses or brackets if present in raw role title
        clean_role = re.sub(r'\s*\([^)]*\)', '', clean_role).strip()
        return f"Your profile has been shortlisted for the {clean_role} position"

    @staticmethod
    def generate_greeting(candidate_name: Optional[str] = None) -> Dict[str, str]:
        """
        Always addresses candidate strictly as 'Dear Candidate,' without personal name.
        """
        return {
            "salutation": "Dear Candidate,",
            "name": "Candidate"
        }

    @staticmethod
    def generate_job_url(source_job_id: Optional[str], fallback_url: Optional[str] = None) -> str:
        """
        Generate job URL: strictly respects custom provided application link/fallback URL,
        or defaults to authoritative SponsorAJobs URL if source_job_id is provided.
        """
        if fallback_url and fallback_url.strip():
            url = fallback_url.strip()
            if not url.startswith("http://") and not url.startswith("https://"):
                url = f"https://{url}"
            return url
        if source_job_id:
            return f"https://sponsorajobs.com/jobs/{source_job_id}"
        return "https://sponsorajobs.com/jobs"

    def render_email(
        self,
        candidate_name: str,
        subscriber_id: int,
        email: str,
        job_title: str,
        company: str,
        location: str = "United Kingdom",
        country_code: str = "GB",
        employment_type: str = "Full-time",
        remote_type: str = "",
        sponsorship_label: str = "",
        description: str = "",
        target_role: Optional[str] = None,
        source_job_id: Optional[str] = None,
        application_url: Optional[str] = None,
        listing_url: Optional[str] = None,
        match_score: int = 0,
        match_reasons: Optional[List[str]] = None,
        experience: str = "",
        custom_subject: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Render HR shortlisting notification email with embedded link."""
        role_display = job_title or target_role or "Role"
        subject = custom_subject.strip() if custom_subject and custom_subject.strip() else self.generate_subject(role_display)
        greeting = self.generate_greeting(candidate_name)

        unsub_token = generate_unsubscribe_token(subscriber_id, email)
        unsubscribe_url = f"{settings.UNSUBSCRIBE_BASE_URL}/{unsub_token}"

        raw_url = application_url or listing_url
        portal_job_url = self.generate_job_url(source_job_id, raw_url)

        template_data = {
            "subject": subject,
            "greeting_salutation": greeting["salutation"],
            "greeting_name": greeting["name"],
            "job_title": job_title,
            "company_name": company or "SponsorAJobs Partner",
            "location": location or "United Kingdom",
            "country_code": (country_code or "GB").upper(),
            "employment_type": employment_type or "Full-time",
            "remote_type": remote_type or "On-site",
            "sponsorship_label": sponsorship_label or "Visa Sponsorship Available",
            "listing_url": portal_job_url,
            "unsubscribe_url": unsubscribe_url,
            "hr_name": self.get_hr_name(subscriber_id),
            "custom_message": custom_message.strip() if custom_message and custom_message.strip() else "",
            "template_version": TEMPLATE_VERSION,
        }

        html_tpl = jinja_env.get_template("email.html")
        text_tpl = jinja_env.get_template("email.txt")

        html_body = html_tpl.render(**template_data)
        text_body = text_tpl.render(**template_data)

        return {
            "subject": subject,
            "html_body": html_body,
            "text_body": text_body,
            "job_url": portal_job_url,
            "template_version": TEMPLATE_VERSION,
            "unsubscribe_token": unsub_token
        }

email_generator = EmailGenerator()
