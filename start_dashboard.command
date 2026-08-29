#!/bin/bash
# Double-clickable launcher for macOS -- Finder runs .command files in
# Terminal automatically, unlike .sh files (which just open in a text editor).
# First-time setup only: python3 -m venv .venv && source .venv/bin/activate &&
# pip install -r requirements.txt && (cd dashboard && npm install)
cd "$(dirname "$0")"

if [ ! -f ".venv/bin/uvicorn" ]; then
    echo "No .venv found. Run this first, in Terminal:"
    echo "  cd \"$(pwd)\""
    echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    echo "  cd dashboard && npm install"
    read -p "Press Enter to close this window..."
    exit 1
fi

echo "Starting API server..."
.venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 &
API_PID=$!

echo "Starting dashboard dev server..."
(cd dashboard && npm run dev) &
DASHBOARD_PID=$!

trap "echo 'Stopping...'; kill $API_PID $DASHBOARD_PID 2>/dev/null" EXIT INT TERM

sleep 4
open http://localhost:5173

echo ""
echo "Both servers running. Close this window (or press Ctrl+C) to stop both."
wait
