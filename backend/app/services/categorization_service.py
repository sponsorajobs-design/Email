import re
from typing import List, Dict, Any, Optional

class CategorizationService:
    """
    Categorizes job seekers and opportunities into standard professional domains
    based on roles, skills, and titles.
    """

    CATEGORIES = [
        "Data & Business Intelligence",
        "Software & Web Engineering",
        "Cloud, DevOps & Infrastructure",
        "Civil, Construction & Architecture",
        "Marketing, Growth & CRM",
        "Product & Project Management",
        "Finance, Accounting & Operations",
        "Human Resources & Talent",
    ]

    CATEGORY_KEYWORDS = {
        "Data & Business Intelligence": [
            "data", "analyst", "analytics", "bi", "business intelligence",
            "sql", "power bi", "tableau", "data engineer", "data scientist",
            "machine learning", "etl", "bigquery", "snowflake", "excel"
        ],
        "Software & Web Engineering": [
            "software", "developer", "frontend", "backend", "programmer", "coder",
            "full stack", "fullstack", "react", "node", "fastapi", "django",
            "python", "java", "c#", ".net", "golang", "mobile", "ios", "android",
            "web", "typescript", "javascript", "api", "postgresql", "software engineer",
            "web engineer", "firmware", "embedded"
        ],
        "Cloud, DevOps & Infrastructure": [
            "devops", "cloud", "infrastructure", "sre", "reliability",
            "aws", "azure", "gcp", "kubernetes", "terraform", "docker",
            "ci/cd", "sysadmin", "linux", "platform engineer", "network engineer"
        ],
        "Civil, Construction & Architecture": [
            "civil", "structural", "construction", "site manager", "site supervisor",
            "quantity surveyor", "surveyor", "architect", "architecture", "bim",
            "cad", "autocad", "revit", "contract administrator", "estimator", "mep",
            "building", "site engineer", "civil engineer", "structural engineer"
        ],
        "Marketing, Growth & CRM": [
            "marketing", "growth", "crm", "hubspot", "seo", "sem",
            "digital marketing", "copywriting", "content", "social media",
            "campaigns", "email marketing", "branding"
        ],
        "Product & Project Management": [
            "product manager", "project manager", "scrum", "agile",
            "product owner", "program manager", "delivery manager"
        ],
        "Finance, Accounting & Operations": [
            "finance", "financial", "accountant", "accounting", "audit",
            "payroll", "banking", "operations", "tax", "bookkeeper"
        ],
        "Human Resources & Talent": [
            "hr", "human resources", "recruiter", "talent acquisition",
            "people ops", "recruitment", "talent"
        ]
    }

    def categorize_profile(self, roles: Optional[str], skills: Optional[str] = None) -> str:
        """
        Determines the best category for a candidate based on preferred roles and skills.
        Defaults to 'Software & Web Engineering' or 'General Professional' if unmatched.
        """
        text = f"{roles or ''} {skills or ''}".lower()
        if not text.strip():
            return "General Professional"

        scores = {cat: 0 for cat in self.CATEGORIES}

        # Role text has higher weight than skills
        role_lower = (roles or "").lower()
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                # Check keyword in roles (weight 3)
                if kw in role_lower:
                    scores[cat] += 3
                # Check keyword in general text (weight 1)
                elif kw in text:
                    scores[cat] += 1

        best_category, max_score = max(scores.items(), key=lambda x: x[1])
        if max_score > 0:
            return best_category

        return "General Professional"

    def categorize_job(self, title: Optional[str], requirements: Optional[str] = None, skills: Optional[str] = None) -> str:
        """Determines the category for a job posting."""
        text = f"{title or ''} {requirements or ''} {skills or ''}".lower()
        title_lower = (title or "").lower()

        scores = {cat: 0 for cat in self.CATEGORIES}
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in title_lower:
                    scores[cat] += 4
                elif kw in text:
                    scores[cat] += 1

        best_category, max_score = max(scores.items(), key=lambda x: x[1])
        if max_score > 0:
            return best_category

        return "General Professional"

categorization_service = CategorizationService()
