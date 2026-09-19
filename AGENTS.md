# Strict Project Boundary & Isolation Rules

## Permanent Rule: STRICT EMAIL MARKETING WORKSPACE ISOLATION

1. **Email Marketing Scope ONLY**:
   - This workspace (`c:\Users\Sumit Raj\OneDrive\email marketing`) is STRICTLY dedicated to the **Email Marketing & Local Candidate Matching Engine**.
   - NEVER touch, inspect, query, reference, or start any other project (such as `jobs`, Next.js web application, or other folders).
   - Do NOT inspect or return ports/links belonging to other directories or projects.

2. **Local Ports & Endpoints**:
   - **Frontend**: Vite Local Admin running at `http://localhost:5173` (from `frontend/`)
   - **Backend**: FastAPI Local API running at `http://localhost:8000` (from `backend/`, docs at `http://localhost:8000/docs`)

3. **Production Isolation**:
   - Strictly follow `ISOLATION.md`.
   - Never run mutating queries on production Supabase.
   - All email marketing data stays in local SQLite (`./data/sponsorajobs_local.db`).
