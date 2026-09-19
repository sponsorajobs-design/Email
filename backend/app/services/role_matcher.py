"""
Role-Based Job Alert Relevance Engine
Deterministic occupational role matching strictly adhering to:
1. Priority 1: DIRECT Normalized Role Match
2. Priority 2: Safe Title / Seniority Variant
3. Priority 3: Curated Occupational Synonym
Generic word protection & category domain guards.
Zero candidate-level scoring.
"""

import re
from typing import Optional, NamedTuple, Set, Dict, List

# Generic occupational words that must NEVER independently create role relevance
GENERIC_WORDS: Set[str] = {
    "manager",
    "engineer",
    "developer",
    "analyst",
    "coordinator",
    "director",
    "officer",
    "specialist",
    "consultant",
    "administrator",
    "lead",
    "head",
    "associate",
    "executive",
    "worker",
    "assistant",
    "designer"
}

# Non-occupational or garbage subscriber inputs that must NEVER produce role matches
NON_OCCUPATIONAL_INPUTS: Set[str] = {
    "student", "no", "other", "none", "na", "n/a", "n a", "unknown", "any", "candidate"
}

# Non-employment / non-job event titles that must NEVER produce matches
NON_EMPLOYMENT_TITLE_KEYWORDS: Set[str] = {
    "guest speaker",
    "guest speakers",
    "voices",
    "sharing event",
    "sharing events",
    "online sharing",
    "volunteer",
    "volunteers",
    "volunteering",
    "unpaid",
    "webinar",
    "podcast",
    "panelist",
    "panelists",
    "study participant",
    "survey participant",
    "mystery shopper",
}

def expand_compound_branches(title: str) -> List[str]:
    """
    Safely expands compound role titles separated by / or | while preserving domain anchors.
    Example: 'BIM Coordinator / Engineer' -> ['BIM Coordinator', 'BIM Engineer']
    Example: 'Civil Engineer / Project Manager' -> ['Civil Engineer', 'Project Manager']
    Example: 'Electrical Engineer / Designer' -> ['Electrical Engineer', 'Electrical Designer']
    """
    raw_branches = [b.strip() for b in re.split(r'\s*[/|]\s*', title) if b.strip()]
    if len(raw_branches) <= 1:
        return [title]

    expanded = []
    first_tokens = raw_branches[0].split()
    domain_prefix = first_tokens[0] if len(first_tokens) >= 2 else ""

    for i, branch in enumerate(raw_branches):
        b_tokens = branch.split()
        if i > 0 and len(b_tokens) == 1 and domain_prefix:
            expanded.append(f"{domain_prefix} {branch}")
        else:
            expanded.append(branch)

    return expanded


# Explicitly permitted seniority modifiers that do not alter the occupational identity
SENIORITY_MODIFIERS: Set[str] = {
    "senior",
    "sr",
    "junior",
    "jr",
    "lead",
    "principal",
    "chief",
    "head of",
    "head",
    "associate",
    "graduate",
    "trainee",
    "entry level",
    "intermediate",
    "mid level",
    "mid",
    "staff",
    "founding",
    "apprentice"
}

# Common abbreviations mapping to canonical occupational phrases
ABBREVIATIONS: Dict[str, str] = {
    "swe": "software engineer",
    "sde": "software development engineer",
    "devops": "devops engineer",
    "sre": "site reliability engineer",
    "pm": "project manager",
    "po": "product owner",
    "ba": "business analyst",
    "da": "data analyst",
    "de": "data engineer",
    "ds": "data scientist",
    "qa": "qa engineer",
    "sdet": "software test engineer",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "hr": "human resources",
    "ta": "talent acquisition",
    "qs": "quantity surveyor"
}

# Curated, occupationally verified synonyms with category guards
# Key: normalized role phrase. Value: list of valid synonym phrases.
CURATED_SYNONYMS: Dict[str, List[str]] = {
    "construction manager": ["site manager", "site agent", "construction site manager", "building site manager"],
    "site manager": ["construction manager", "site agent", "construction site manager"],
    "project manager": ["programme manager", "program manager", "delivery manager", "project delivery manager", "project lead"],
    "programme manager": ["project manager", "program manager", "delivery manager"],
    "program manager": ["programme manager", "project manager", "delivery manager"],
    "delivery manager": ["project manager", "programme manager", "delivery lead"],
    "project coordinator": ["project administrator", "project support officer", "pm support"],
    "project administrator": ["project coordinator", "project support officer"],
    "software engineer": ["software developer", "full stack developer", "backend developer", "frontend developer", "application developer"],
    "software developer": ["software engineer", "full stack developer", "backend developer", "frontend developer", "application developer"],
    "full stack developer": ["full stack engineer"],
    "frontend developer": ["frontend engineer", "front end developer", "ui engineer", "web developer"],
    "backend developer": ["backend engineer", "back end developer", "server engineer"],
    "devops engineer": ["site reliability engineer", "sre", "platform engineer", "cloud infrastructure engineer", "infrastructure engineer"],
    "site reliability engineer": ["devops engineer", "platform engineer", "sre", "cloud engineer"],
    "platform engineer": ["devops engineer", "site reliability engineer", "cloud infrastructure engineer"],
    "data engineer": ["big data engineer", "analytics engineer", "data pipeline engineer"],
    "data analyst": ["business intelligence analyst", "bi analyst", "analytics specialist"],
    "bi analyst": ["data analyst", "business intelligence analyst"],
    "data scientist": ["machine learning engineer", "ml engineer", "ai engineer", "applied scientist"],
    "machine learning engineer": ["data scientist", "ml engineer", "ai engineer"],
    "qa engineer": ["quality assurance engineer", "software tester", "test automation engineer", "sdet"],
    "quality assurance engineer": ["qa engineer", "software tester", "test engineer"],
    "quantity surveyor": ["cost consultant", "cost manager", "commercial manager"],
    "cost consultant": ["quantity surveyor", "cost manager"],
    "business analyst": ["functional analyst", "product analyst", "business systems analyst"],
    "human resources manager": ["hr manager", "people manager", "talent acquisition manager", "people operations manager", "hr business partner"],
    "hr manager": ["human resources manager", "people manager", "people operations manager", "hr business partner"],
    "accountant": ["financial accountant", "management accountant", "chartered accountant"],
    "electrical engineer": ["electrical design engineer", "power systems engineer", "building services electrical engineer"],
    "mechanical engineer": ["mechanical design engineer", "building services mechanical engineer", "hvac engineer"],
    "civil engineer": ["structural engineer", "civil infrastructure engineer", "highways engineer"],
    "structural engineer": ["civil engineer", "civil structural engineer"],
    "nurse": ["registered nurse", "staff nurse", "clinical nurse"],
    "teacher": ["primary teacher", "secondary teacher", "educator", "school teacher"],
}

# Domain category guards for curated synonyms
# Certain synonyms must not cross incompatible domains (e.g. restaurant manager vs construction site manager)
INCOMPATIBLE_DOMAINS: Dict[str, Set[str]] = {
    "construction manager": {"cat_retail_hospitality", "cat_food_services", "cat_culinary", "cat_healthcare"},
    "site manager": {"cat_retail_hospitality", "cat_food_services", "cat_culinary"},
    "project manager": {"cat_healthcare_nursing", "cat_culinary"},
}

class RoleMatchResult(NamedTuple):
    is_relevant: bool
    match_type: str        # 'DIRECT', 'VARIANT', 'SYNONYM', or 'NONE'
    matched_reason: str
    legacy_score: int      # 3 for DIRECT, 2 for VARIANT, 1 for SYNONYM, 0 for NONE (compatibility only)

def clean_and_normalize(text: Optional[str]) -> str:
    """Case, punctuation, and whitespace normalization."""
    if not text:
        return ""
    s = text.lower().strip()
    # Replace punctuation and special characters with spaces
    s = re.sub(r'[\/\\,\-\_\:\;\(\)\[\]\{\}\"\'\|\+\&\@\#\$\%\^\*\.]+', ' ', s)
    # Collapse multiple whitespaces
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def expand_abbreviations(norm_text: str) -> str:
    """Expand recognized standard role abbreviations."""
    words = norm_text.split()
    expanded_words = [ABBREVIATIONS.get(w, w) for w in words]
    return " ".join(expanded_words)

def strip_seniority_modifiers(norm_text: str) -> str:
    """
    Remove known seniority modifiers from a normalized string.
    Only strictly recognized modifiers are stripped.
    """
    text = norm_text
    # Handle multi-word modifiers first
    for mod in ["head of", "entry level", "mid level"]:
        pattern = rf"\b{mod}\b"
        text = re.sub(pattern, "", text)

    words = text.split()
    filtered = [w for w in words if w not in SENIORITY_MODIFIERS]
    return " ".join(filtered).strip()

def has_non_generic_token_overlap(str1: str, str2: str) -> bool:
    """Verify that any token overlap between two phrases contains at least one non-generic occupational term."""
    tokens1 = set(clean_and_normalize(str1).split())
    tokens2 = set(clean_and_normalize(str2).split())
    overlap = tokens1.intersection(tokens2)
    # Filter out stop words and generic words
    stop_words = {"and", "or", "of", "the", "in", "for", "at", "to", "with", "a", "an", "expression", "interest"}
    substantive_overlap = [w for w in overlap if w not in GENERIC_WORDS and w not in stop_words]
    return len(substantive_overlap) > 0

def evaluate_role_relevance(
    subscriber_role: str,
    job_title: str,
    category_id: Optional[str] = None,
    description: Optional[str] = None
) -> RoleMatchResult:
    """
    Evaluates role relevance using the exact hierarchy:
    Priority 1: DIRECT Normalized Role Match
    Priority 2: Safe Title / Seniority Variant
    Priority 3: Curated Occupational Synonym
    Fallback: NOT RELEVANT
    """
    if not subscriber_role or not subscriber_role.strip():
        return RoleMatchResult(
            is_relevant=False,
            match_type="NONE",
            matched_reason="Empty subscriber target role",
            legacy_score=0
        )

    if not job_title or not job_title.strip():
        return RoleMatchResult(
            is_relevant=False,
            match_type="NONE",
            matched_reason="Empty job title",
            legacy_score=0
        )

    norm_sub = clean_and_normalize(subscriber_role)
    norm_job = clean_and_normalize(job_title)

    if not norm_sub or not norm_job:
        return RoleMatchResult(
            is_relevant=False,
            match_type="NONE",
            matched_reason="Normalization produced empty string",
            legacy_score=0
        )

    # Rejection of standalone non-occupational inputs (Student, No, Other, etc.)
    if norm_sub in NON_OCCUPATIONAL_INPUTS:
        return RoleMatchResult(
            is_relevant=False,
            match_type="NONE",
            matched_reason=f"Rejected non-occupational subscriber role input: '{subscriber_role}'",
            legacy_score=0
        )

    # Rejection of standalone generic words without occupational domain qualifier (e.g. Designer, Engineer)
    if norm_sub in GENERIC_WORDS:
        return RoleMatchResult(
            is_relevant=False,
            match_type="NONE",
            matched_reason=f"Rejected standalone generic word without occupational qualifier: '{subscriber_role}'",
            legacy_score=0
        )

    # Rejection of non-employment listings (guest speaker, volunteer, webinar, sharing event, etc.)
    job_lower = (job_title or "").lower()
    for bad_kw in NON_EMPLOYMENT_TITLE_KEYWORDS:
        if bad_kw in job_lower or bad_kw in norm_job:
            return RoleMatchResult(
                is_relevant=False,
                match_type="NONE",
                matched_reason=f"Rejected non-employment listing: found '{bad_kw}' in '{job_title}'",
                legacy_score=0
            )

    # Context-aware compound slash/pipe title handling
    if ("/" in job_title or "|" in job_title) and not ("/" in subscriber_role or "|" in subscriber_role):
        branches = expand_compound_branches(job_title)
        if len(branches) > 1:
            level_map = {"DIRECT": 3, "VARIANT": 2, "SYNONYM": 1, "NONE": 0}
            best_res: Optional[RoleMatchResult] = None
            for branch in branches:
                res = evaluate_role_relevance(subscriber_role, branch, category_id, description)
                if res.is_relevant:
                    if best_res is None or level_map.get(res.match_type, 0) > level_map.get(best_res.match_type, 0):
                        best_res = res
                        if res.match_type == "DIRECT":
                            break
            if best_res and best_res.is_relevant:
                return best_res
            return RoleMatchResult(
                is_relevant=False,
                match_type="NONE",
                matched_reason=f"No compound branch in '{job_title}' matched '{subscriber_role}'",
                legacy_score=0
            )

    # -----------------------------------------------------------------
    # PRIORITY 1: DIRECT NORMALIZED ROLE MATCH
    # -----------------------------------------------------------------
    # Strip parentheticals and company brackets for clean title comparison
    clean_job_no_paren = re.sub(r'\s*\([^)]*\)', '', job_title)
    norm_job_no_paren = clean_and_normalize(clean_job_no_paren)

    exp_sub = expand_abbreviations(norm_sub)
    exp_job = expand_abbreviations(norm_job)
    exp_job_no_paren = expand_abbreviations(norm_job_no_paren)

    base_sub = strip_seniority_modifiers(exp_sub)
    base_job = strip_seniority_modifiers(exp_job)
    has_seniority_difference = (base_sub != exp_sub) or (base_job != exp_job)

    # Exact normalized equality (without seniority difference)
    if (norm_sub == norm_job or exp_sub == exp_job or norm_sub == norm_job_no_paren or exp_sub == exp_job_no_paren) and not has_seniority_difference:
        return RoleMatchResult(
            is_relevant=True,
            match_type="DIRECT",
            matched_reason=f"Exact normalized occupational match: '{subscriber_role}' == '{job_title}'",
            legacy_score=3
        )

    # Direct phrase match without any seniority modifier involvement
    pattern_direct = rf"\b{re.escape(norm_sub)}\b"
    if re.search(pattern_direct, norm_job) and not has_seniority_difference:
        if has_non_generic_token_overlap(norm_sub, norm_job):
            return RoleMatchResult(
                is_relevant=True,
                match_type="DIRECT",
                matched_reason=f"Direct occupational phrase match: '{subscriber_role}' in '{job_title}'",
                legacy_score=3
            )

    # -----------------------------------------------------------------
    # PRIORITY 2: SAFE TITLE / SENIORITY VARIANT
    # -----------------------------------------------------------------

    # The base occupation must be non-empty and must NOT consist solely of generic words
    sub_tokens = [w for w in base_sub.split() if w not in GENERIC_WORDS]
    if base_sub and base_job and len(sub_tokens) > 0:
        # Check if base occupations match exactly
        if base_sub == base_job:
            return RoleMatchResult(
                is_relevant=True,
                match_type="VARIANT",
                matched_reason=f"Seniority variant match on core occupation '{base_sub}' ('{subscriber_role}' vs '{job_title}')",
                legacy_score=2
            )

        # Check if base subscriber occupation is contained as a phrase in base job
        pattern_base = rf"\b{re.escape(base_sub)}\b"
        if re.search(pattern_base, base_job) and has_non_generic_token_overlap(base_sub, base_job):
            return RoleMatchResult(
                is_relevant=True,
                match_type="VARIANT",
                matched_reason=f"Seniority variant phrase match: '{base_sub}' in '{base_job}'",
                legacy_score=2
            )



    # -----------------------------------------------------------------
    # PRIORITY 3: CURATED OCCUPATIONAL SYNONYM
    # -----------------------------------------------------------------
    # Look up base_sub or exp_sub in curated synonym dictionary
    lookup_keys = [base_sub, exp_sub, norm_sub]
    synonyms_to_check: List[str] = []
    for k in lookup_keys:
        if k in CURATED_SYNONYMS:
            synonyms_to_check.extend(CURATED_SYNONYMS[k])

    if synonyms_to_check:
        # Check category guard if defined
        norm_cat = (category_id or "").strip().lower()
        for syn in synonyms_to_check:
            # Check domain incompatibility guard
            for blocked_role, bad_cats in INCOMPATIBLE_DOMAINS.items():
                if (norm_sub == blocked_role or base_sub == blocked_role) and norm_cat in bad_cats:
                    # Domain mismatch - reject synonym match
                    continue

            norm_syn = clean_and_normalize(syn)
            base_syn = strip_seniority_modifiers(norm_syn)

            # Check direct match with synonym
            if norm_syn == norm_job or (base_syn and len(base_syn.split()) >= 2 and base_syn == base_job):
                return RoleMatchResult(
                    is_relevant=True,
                    match_type="SYNONYM",
                    matched_reason=f"Curated occupational synonym match: '{subscriber_role}' -> '{syn}' ('{job_title}')",
                    legacy_score=1
                )

            # Check phrase match with full synonym (e.g., 'project lead' in 'Senior Project Lead')
            pattern_syn = rf"\b{re.escape(norm_syn)}\b"
            if re.search(pattern_syn, norm_job) and has_non_generic_token_overlap(norm_syn, norm_job):
                return RoleMatchResult(
                    is_relevant=True,
                    match_type="SYNONYM",
                    matched_reason=f"Curated occupational synonym phrase match: '{norm_syn}' in '{job_title}'",
                    legacy_score=1
                )

            # Check base phrase match only if base_syn retains at least 2 substantive occupational tokens
            if base_syn and len(base_syn.split()) >= 2:
                pattern_base_syn = rf"\b{re.escape(base_syn)}\b"
                if re.search(pattern_base_syn, base_job) and has_non_generic_token_overlap(base_syn, base_job):
                    return RoleMatchResult(
                        is_relevant=True,
                        match_type="SYNONYM",
                        matched_reason=f"Curated occupational synonym phrase match: '{base_syn}' in '{job_title}'",
                        legacy_score=1
                    )

    # -----------------------------------------------------------------
    # NOT RELEVANT
    # -----------------------------------------------------------------
    # Check if generic words only overlapped
    tokens_sub = set(norm_sub.split())
    tokens_job = set(norm_job.split())
    common_tokens = tokens_sub.intersection(tokens_job)
    if common_tokens:
        reason = f"Rejected generic word overlap only: {common_tokens}"
    else:
        reason = f"No occupational match between '{subscriber_role}' and '{job_title}'"

    return RoleMatchResult(
        is_relevant=False,
        match_type="NONE",
        matched_reason=reason,
        legacy_score=0
    )
