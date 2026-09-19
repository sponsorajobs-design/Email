# Architectural & Production Isolation Guarantee

## Objective & Scope

This document establishes the hard boundary and isolation rules between the **SponsorAJobs Local Candidate Matching & Personalized Email Engine** and the existing production SponsorAJobs web application, Vercel infrastructure, and Supabase production database.

---

## 1. Zero Vercel Coupling

- **No Deployment to Vercel**: This project does not contain any Vercel configuration (`vercel.json`, Next.js middleware, edge runtime functions).
- **No Production Codebase Mutation**: The existing web application codebase is untouched. This engine is housed in an independent local directory (`email marketing`).
- **No Shared Build Pipelines**: There are no shared CI/CD pipelines, GitHub Actions, or Vercel hooks linking this project to production.

---

## 2. Strictly Read-Only Supabase Connection

- **Principle of Least Privilege**: The application only uses `SELECT` queries to retrieve active jobs and subscriber records from Supabase.
- **Prohibited Operations**: Under no circumstances does this application execute `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, or schema DDL commands against the production Supabase database.
- **Enforced in Code**: The `SupabaseService` adapter is strictly read-only. Mutating calls are actively prohibited and verified via automated test suites (`test_readonly_protection.py`).
- **Offline / Mock Mode**: If Supabase credentials are missing or disconnected, the engine seamlessly utilizes a local mock dataset without attempting remote connection.

---

## 3. Dedicated Local Database

- **Separate SQLite Database**: All local snapshots, candidate-job match history, campaigns, email queues, unsubscribe tokens, and audit logs reside in `./data/sponsorajobs_local.db`.
- **Portability**: Database access is abstracted via SQLAlchemy 2.0 ORM, allowing local migration to a standalone local PostgreSQL instance in the future without altering application logic.
- **No Upstream Replication**: Changes to local records never sync back or pollute production database tables.

---

## 4. Controlled Outbound SMTP Boundary

- **Local SMTP Worker**: Emails are delivered directly from the local worker through port 587 using STARTTLS to the designated mail server (`mail.sponsorajobs.com`).
- **Safety Overrides**:
  - `DRY_RUN=true`: When enabled, emails are queued and marked, but zero network packets are sent over SMTP.
  - `EMAIL_TEST_MODE=true`: Redirects all outgoing candidate emails to a single `TEST_EMAIL_ADDRESS` while retaining the original candidate recipient header in the body for testing.
- **Credential Protection**: SMTP passwords and API secrets are read strictly from local environment variables, never logged, and never returned in API responses to the browser.

---

## Summary Checklist

| Dimension | Production System | Local Matching & Email Engine |
| :--- | :--- | :--- |
| **Hosting** | Vercel (Production) | Localhost (`127.0.0.1:8000` & `5173`) |
| **Supabase Access** | Read / Write | **Strictly Read-Only** (`SELECT` only) |
| **Database Storage** | Production Supabase | Local SQLite (`./data/sponsorajobs_local.db`) |
| **Email Delivery** | None / Existing Site | Dedicated Local Worker (STARTTLS 587) |
| **Codebase Location** | Separate Repository | `email marketing` (Independent) |
