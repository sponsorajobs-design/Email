@echo off
echo =====================================================================
echo Starting SponsorAJobs Matching & Email Engine (Backend API)
echo =====================================================================
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo Error: Python virtual environment not found in .venv.
    echo Please run: python -m venv .venv ^&^& .venv\Scripts\pip install -r backend\requirements.txt
    pause
    exit /b 1
)

set PYTHONPATH=.
echo Starting FastAPI on http://127.0.0.1:8000 ...
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
pause
