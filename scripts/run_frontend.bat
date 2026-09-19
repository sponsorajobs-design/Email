@echo off
echo =====================================================================
echo Starting SponsorAJobs Local Admin Dashboard (Vite Frontend)
echo =====================================================================
cd /d "%~dp0\..\frontend"

echo Starting Vite dev server on http://localhost:5173 ...
npm run dev
pause
