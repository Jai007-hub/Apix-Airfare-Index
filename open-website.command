#!/bin/bash
# macOS one-click launcher -- the twin of OPEN-WEBSITE.bat.
#
# Pulls the latest code, installs anything new, restarts both servers from
# clean, and opens the site. Finder runs .command files in Terminal on a
# double-click (unlike .sh, which opens in a text editor).
#
# Gatekeeper may block the first double-click ("unidentified developer") --
# right-click the file and choose Open instead; that only needs doing once.
cd "$(dirname "$0")" || exit 1

echo "=========================================================="
echo "  APIx - Real-time Airfare Price Index"
echo "=========================================================="
echo

# ------------------------------------------------------------------ update --
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    # Edits to tracked files would turn a pull into a merge and could lose
    # them, so leave the folder alone in that case. Untracked files are
    # ignored on purpose -- a stray download sitting here does not block a
    # pull, and treating it as "dirty" would quietly stop updates forever.
    if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
        echo "[skip] You have uncommitted edits here, so nothing was pulled."
        echo "       Commit them first if you want the latest code."
    else
        BEFORE=$(git rev-parse HEAD)
        echo "Checking GitHub for updates..."
        if git pull --ff-only; then
            AFTER=$(git rev-parse HEAD)
            if [ "$BEFORE" = "$AFTER" ]; then
                echo "Already up to date."
            else
                echo
                echo "Downloaded new changes. Checking if anything needs installing..."
                CHANGED=$(git diff --name-only "$BEFORE" "$AFTER")
                # Only reinstall when the dependency files actually changed --
                # doing it every launch would add minutes for nothing.
                if echo "$CHANGED" | grep -q "requirements.txt"; then
                    echo "  - Python packages changed, installing..."
                    .venv/bin/python -m pip install -q -r requirements.txt
                fi
                if echo "$CHANGED" | grep -q "dashboard/package.json"; then
                    echo "  - Dashboard packages changed, installing..."
                    (cd dashboard && npm install)
                fi
            fi
        else
            echo "[warn] Could not pull - offline, or no access to the repo."
            echo "       Starting with the code already on this machine."
        fi
    fi
else
    echo "[skip] Not a git checkout - running the code that is here."
fi
echo

# --------------------------------------------------------------- first run --
if [ ! -f ".venv/bin/uvicorn" ]; then
    echo "No Python environment found. Set it up first, in Terminal:"
    echo "  cd \"$(pwd)\""
    echo "  python3 -m venv .venv"
    echo "  .venv/bin/python -m pip install -r requirements.txt"
    echo "  cd dashboard && npm install"
    read -r -p "Press Enter to close this window..."
    exit 1
fi

if [ ! -d "dashboard/node_modules" ]; then
    echo "Installing dashboard packages (first run)..."
    (cd dashboard && npm install)
fi

if [ ! -f "apix.db" ]; then
    echo
    echo "=========================================================="
    echo "  No database found. Building it now - takes 5-10 minutes."
    echo "  This only happens once on a new machine."
    echo "=========================================================="
    echo
    .venv/bin/python -m scripts.seed_demo_data
    echo
fi

# ---------------------------------------------------------- stop old servers --
# Restarting from clean guarantees the running server is the code we just
# pulled, rather than whatever was started hours ago.
echo "Stopping anything already using ports 8000 and 5173..."
lsof -ti tcp:8000 -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null
lsof -ti tcp:5173 -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null

# -------------------------------------------------------------- start them --
echo "Starting API server..."
.venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 &
API_PID=$!

echo "Starting dashboard..."
(cd dashboard && npm run dev) &
DASHBOARD_PID=$!

trap 'echo; echo "Stopping both servers..."; kill $API_PID $DASHBOARD_PID 2>/dev/null' EXIT INT TERM

# ----------------------------------------------------------------- open it --
echo "Waiting for the dashboard to come up..."
for _ in $(seq 1 45); do
    if curl -s -o /dev/null http://localhost:5173; then
        break
    fi
    sleep 1
done

open http://localhost:5173 2>/dev/null || xdg-open http://localhost:5173 2>/dev/null

echo
echo "=========================================================="
echo "  Running."
echo "  Site:  http://localhost:5173"
echo "  API :  http://localhost:8000/docs"
echo "  Keep this window open. Ctrl+C here stops both servers."
echo "=========================================================="
wait
