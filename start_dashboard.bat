@echo off
cd /d "%~dp0"
set PATH=C:\Program Files\nodejs;%PATH%

echo Starting API server...
start "APIx - API server (leave this open)" cmd /k ".venv\Scripts\uvicorn.exe api.main:app --reload --host 0.0.0.0"

echo Starting dashboard dev server...
start "APIx - Dashboard (leave this open)" cmd /k "cd dashboard && npm run dev"

echo Waiting for servers to start...
timeout /t 5 /nobreak >nul

start http://localhost:5173

echo.
echo Two windows just opened - one for the API, one for the dashboard.
echo Leave both running. This window can be closed.
pause
