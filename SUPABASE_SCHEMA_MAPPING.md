# Supabase Schema Mapping & Field Adapter Specification

## Overview

The SponsorAJobs Local Candidate Matching & Email Engine communicates with the production Supabase database through a dynamic adapter layer. This design ensures that regardless of the exact naming convention in Supabase (e.g., `role` vs `job_title`, `experience_years` vs `exp`, `skills` as JSON array vs comma-separated text), the local engine normalizes the data into standard internal models.

---

## 1. Subscriber Table Mapping (`SUPABASE_SUBSCRIBER_TABLE`)

Default table name: `subscribers` (configurable via `SUPABASE_SUBSCRIBER_TABLE` in `.env`).

| Standard Engine Field | Expected Supabase Column Names (Fallback Order) | Data Type | Notes & Normalization |
| :--- | :--- | :--- | :--- |
| `source_subscriber_id` | `id`, `user_id`, `subscriber_id` | `string` / `integer` | Primary identifier in Supabase |
| `name` | `name`, `full_name`, `first_name` | `string` | Defaults to "Candidate" if blank |
| `email` | `email`, `user_email` | `string` | Strict RFC 5322 validation |
| `preferred_roles` | `preferred_role`, `preferred_roles`, `role`, `target_role` | `array` or `string` | Normalized to lowercase token list |
| `location` | `location`, `city`, `preferred_location`, `country` | `string` | Normalized city/country string |
| `skills` | `skills`, `skills_list`, `tech_stack` | `array` or `string` | Split on commas, lowercase tokens |
| `experience_years` | `experience`, `experience_years`, `years_experience`, `exp` | `integer` or `string` | Parsed numeric integer (e.g. "3-5 years" &rarr; 3) |
| `job_preferences` | `job_preferences`, `preferences` | `json` or `string` | Full-time, remote, visa requirements |
| `subscription_status` | `subscription_status`, `status`, `is_active` | `string` or `boolean` | Must indicate active subscriber |
| `is_unsubscribed` | `is_unsubscribed`, `unsubscribed`, `opt_out` | `boolean` | Excluded immediately if true |

---

## 2. Job Listings Table Mapping (`SUPABASE_JOB_TABLE`)

Default table name: `jobs` (configurable via `SUPABASE_JOB_TABLE` in `.env`).

| Standard Engine Field | Expected Supabase Column Names (Fallback Order) | Data Type | Notes & Normalization |
| :--- | :--- | :--- | :--- |
| `source_job_id` | `id`, `job_id` | `string` / `integer` | Primary identifier in Supabase |
| `title` | `title`, `job_title`, `position` | `string` | Dynamic token in subject line |
| `company` | `company`, `company_name`, `employer` | `string` | Displayed in email card |
| `location` | `location`, `city`, `job_location` | `string` | City / Remote status |
| `description` | `description`, `job_description`, `summary` | `string` | Job summary & context |
| `requirements` | `requirements`, `qualifications` | `string` / `array` | Required qualifications |
| `skills` | `skills`, `required_skills`, `skills_needed` | `array` or `string` | Normalized list of required skills |
| `experience` | `experience`, `experience_required`, `min_experience` | `string` / `integer` | Min experience years or label |
| `employment_type` | `employment_type`, `job_type`, `type` | `string` | Full-time, Contract, etc. |
| `application_url` | `application_url`, `apply_url`, `url`, `link` | `string` | **Subject to async URL verification** |
| `status` | `status`, `is_active`, `state` | `string` or `boolean` | Must indicate live/active |
| `closing_date` | `closing_date`, `expires_at`, `deadline` | `timestamp` | Verified not in the past |

---

## 3. Graceful Missing Field Handling

If a field is missing from a record:
- **Missing candidate email or job title/URL**: Record is flagged with a structured skip reason (`INVALID_EMAIL`, `MISSING_JOB_URL`, `MISSING_JOB_TITLE`).
- **Missing candidate experience**: Defaults to 0 years; experience score weighted accordingly.
- **Missing skills**: Defaults to empty array; match score computed purely on role, location, and recency.
- **Missing closing date**: Assumed active unless URL verification or status check indicates dead.
