@echo off
echo =====================================================================
echo Running SponsorAJobs Test Suite (pytest)
echo =====================================================================
cd /d "%~dp0\.."

set PYTHONPATH=.
.\.venv\Scripts\python -m pytest backend\tests -v
pause
