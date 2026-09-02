@echo off
setlocal enabledelayedexpansion
title APIx - launcher
cd /d "%~dp0"

REM A fresh shell may not have Git or Node on PATH, so put them there for
REM this window only -- nothing permanent is changed on the machine.
set "PATH=C:\Program Files\Git\cmd;C:\Program Files\nodejs;%PATH%"

echo ==========================================================
echo   APIx - Real-time Airfare Price Index
echo ==========================================================
echo.

REM ---------------------------------------------------------------- update --
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [skip] Not a git checkout - running the code that is here.
  goto run
)

for /f "delims=" %%i in ('git rev-parse HEAD') do set "BEFORE=%%i"

REM Edits to tracked files would turn a pull into a merge and could lose
REM them, so we leave the folder alone in that case. Untracked files are
REM ignored on purpose -- a stray download sitting in the folder does not
REM block a pull, and treating it as "dirty" would quietly stop updates.
for /f "delims=" %%i in ('git status --porcelain --untracked-files^=no') do set "DIRTY=1"
if defined DIRTY (
  echo [skip] You have uncommitted edits here, so nothing was pulled.
  echo        Commit them first if you want the latest code.
  goto run
)

echo Checking GitHub for updates...
git pull --ff-only
if errorlevel 1 (
  echo [warn] Could not pull - offline, or no access to the repo.
  echo        Starting with the code already on this machine.
  goto run
)

for /f "delims=" %%i in ('git rev-parse HEAD') do set "AFTER=%%i"
if "!BEFORE!"=="!AFTER!" (
  echo Already up to date.
  goto run
)

echo.
echo Downloaded new changes. Checking if anything needs installing...

REM Only reinstall when the dependency files actually changed -- doing it
REM every launch would add minutes for nothing.
git diff --name-only !BEFORE! !AFTER! | findstr /c:"requirements.txt" >nul
if not errorlevel 1 (
  echo   - Python packages changed, installing...
  .venv\Scripts\python.exe -m pip install -q -r requirements.txt
)

git diff --name-only !BEFORE! !AFTER! | findstr /c:"dashboard/package.json" >nul
if not errorlevel 1 (
  echo   - Dashboard packages changed, installing...
  pushd dashboard
  call npm install
  popd
)

:run
echo.

REM ------------------------------------------------------------ first run --
REM A teammate who has only cloned has none of this yet, so set it up rather
REM than failing with instructions they would have to follow by hand.
if not exist ".venv\Scripts\python.exe" (
  echo.
  echo First run - creating the Python environment ^(about 3 minutes^)...
  py -3.13 -m venv .venv
  if errorlevel 1 (
    echo   Python 3.13 not found, using the default Python...
    py -3 -m venv .venv
  )
  .venv\Scripts\python.exe -m pip install --upgrade pip -q
  .venv\Scripts\python.exe -m pip install -q -r requirements.txt
  echo   Python environment ready.
)

if not exist "dashboard\node_modules" (
  echo.
  echo First run - installing dashboard packages ^(about 2 minutes^)...
  pushd dashboard
  call npm install
  popd
)

REM ------------------------------------------------------------- database --
if not exist "apix.db" (
  echo.
  echo ==========================================================
  echo   No database found. Building it now - takes 5-10 minutes.
  echo   This only happens once on a new machine.
  echo ==========================================================
  echo.
  .venv\Scripts\python.exe -m scripts.seed_demo_data
  echo.
)

REM ---------------------------------------------------- stop old servers --
REM Restarting from clean guarantees the running server is the code we just
REM pulled, rather than whatever was started hours ago.
echo Stopping anything already using ports 8000 and 5173...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -EA SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -EA SilentlyContinue }"

REM -------------------------------------------------------- start servers --
echo Starting API server...
start "APIx - API server (leave this open)" cmd /k ".venv\Scripts\uvicorn.exe api.main:app --reload --host 0.0.0.0"

echo Starting dashboard...
start "APIx - Dashboard (leave this open)" cmd /k "cd dashboard && npm run dev"

REM ------------------------------------------------------------- open it --
echo Waiting for the dashboard to come up...
set TRIES=0
:wait
set /a TRIES+=1
timeout /t 1 /nobreak >nul
curl -s -o nul http://localhost:5173 2>nul
if not errorlevel 1 goto ready
if !TRIES! lss 45 goto wait
echo [warn] Dashboard is taking a while. Opening the browser anyway -
echo        refresh the page in a few seconds if it looks blank.

:ready
start http://localhost:5173

echo.
echo ==========================================================
echo   Running. Two windows opened - leave them both open.
echo   Site:  http://localhost:5173
echo   API :  http://localhost:8000/docs
echo   This window can be closed.
echo ==========================================================
timeout /t 8 /nobreak >nul
