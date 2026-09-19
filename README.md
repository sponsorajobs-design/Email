# SponsorAJobs Local Candidate Matching & Personalized Email Engine

A standalone, locally running matching and email delivery engine for SponsorAJobs.

This system connects **read-only** to your existing SponsorAJobs Supabase database, synchronizes live jobs and subscribers into an isolated local SQLite database, deterministically matches candidates to eligible jobs, verifies that job application URLs are live, generates personalized emails with dynamic subjects and honest shortlist disclaimers, and sends them through your configured SMTP server with strict safety controls (Dry-Run, Single-Address Test Mode, Rate Limiting, and Concurrency Controls).

---

## Key Features

1. **Strict Production Isolation**: Completely isolated local application (`localhost`). Never deploys to Vercel, never writes to production Supabase tables, never touches production website code.
2. **Deterministic Matching Engine**: Configurable 100-point scoring algorithm (Role 35%, Skills 30%, Experience 20%, Location 10%, Recency 5%) with transparent match reasons.
3. **Async URL Verification**: Proactively verifies that external job application links return valid HTTP status codes (following redirects, flagging dead links, caching results with TTL) so candidates never receive dead links.
4. **Duplicate & Unsubscribe Protection**: Prevents duplicate sends to the same candidate for the same job via `candidate_job_history` and enforces instant unsubscribe exclusion.
5. **Dynamic & Honest Email Personalization**:
   - Subject: `Congratulations! Your Profile Has Been Shortlisted for the [JOB TITLE] Role`
   - Content: Clearly distinguishes a SponsorAJobs algorithm match from an employer selection, preserving brand trust while achieving high candidate engagement.
6. **Robust Controlled Delivery**:
   - **Dry-Run Mode (`DRY_RUN=true`)**: Process matching and queues without sending real emails.
   - **Test Mode (`EMAIL_TEST_MODE=true`)**: Safely redirect all candidate emails to an administrator test address.
   - **Rate Limiting**: Configurable messages per minute and max concurrency.
   - **Crash Recovery**: Idempotent queue execution resumes safely after interruption without resending.
7. **Modern Admin Dashboard**: Full React + TypeScript + Vite dashboard with statistics, sync controls, URL verification badges, matching explorer, campaign preview/approval, live email preview modal, and queue monitor.

---

## Quick Start Guide

### Prerequisites
- Python 3.12+ (Python 3.14 supported)
- Node.js 18+ and npm

### 1. Environment Configuration
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Ensure safety switches are initially enabled:
```env
DRY_RUN=true
EMAIL_TEST_MODE=true
TEST_EMAIL_ADDRESS=your-test-email@example.com
```

### 2. Backend Setup
Create and activate virtual environment, then install dependencies:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

### 3. Frontend Setup
Navigate to the frontend directory and install dependencies:
```powershell
cd frontend
npm install
cd ..
```

### 4. Running the Application
You can run both services easily:
- **Start Backend**: Run `.\scripts\run_backend.bat` (serves FastAPI at `http://127.0.0.1:8000`)
- **Start Frontend**: Run `.\scripts\run_frontend.bat` (serves Vite Admin at `http://localhost:5173`)
- **Run Tests**: Run `.\scripts\run_tests.bat`

---

## Safety Progression Model

Follow this step-by-step verification pipeline:
1. **Stage 1 (Dry Run)**: Run Supabase Sync &rarr; Job URL Verification &rarr; Matching &rarr; Generate Campaign in `DRY_RUN=true`.
2. **Stage 2 (Preview & Single Test Email)**: Review generated emails in the preview modal &rarr; click **[Send Test Email]** to confirm appearance in your inbox.
3. **Stage 3 (Controlled Batch)**: Select a batch of 10 candidates &rarr; review matching reasons &rarr; click **[Approve & Send]** in `EMAIL_TEST_MODE=true`.
4. **Stage 4 (Full Campaign)**: Verify logs in `logs/email.log` &rarr; toggle `DRY_RUN=false` and `EMAIL_TEST_MODE=false` in `.env` only when confident.

---

## Project Structure
```text
email marketing/
├── .env.example            # Environment configuration template
├── .gitignore              # Standard exclusions
├── README.md               # Operating guide
├── ISOLATION.md            # Production boundary guarantee
├── SUPABASE_SCHEMA_MAPPING.md # Dynamic schema adapter docs
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI entrypoint & middleware
│   │   ├── core/           # Config, logging, security
│   │   ├── models/         # SQLAlchemy 2.0 SQLite models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Supabase, URL verifier, matching, email generator, SMTP
│   │   ├── templates/      # Jinja2 HTML and plain-text email templates
│   │   └── api/routes/     # REST route handlers
│   ├── tests/              # 20+ automated pytest test cases
│   └── requirements.txt    # Python dependencies
├── frontend/               # React + TypeScript + Vite admin UI
├── scripts/                # Launchers & backup script
├── data/                   # Local SQLite database (sponsorajobs_local.db)
└── logs/                   # application.log, email.log, audit.log
```
