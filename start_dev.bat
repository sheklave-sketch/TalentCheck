@echo off
echo Starting TalentCheck development servers...

:: Start API (run from talentcheck root so relative imports in api/ work)
start "TalentCheck API" cmd /k "cd /d %~dp0 && python -m uvicorn api.main:app --reload --port 8000"

:: Start Web
start "TalentCheck Web" cmd /k "cd /d %~dp0 && cd web && npm run dev"

echo.
echo API: http://localhost:8000
echo Web: http://localhost:3000
echo Docs: http://localhost:8000/docs
echo.
