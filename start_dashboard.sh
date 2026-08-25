#!/bin/bash
# One-command launcher for macOS/Linux -- Mac equivalent of start_dashboard.bat.
# First-time setup only: python3 -m venv .venv && source .venv/bin/activate &&
# pip install -r requirements.txt && (cd dashboard && npm install)
cd "$(dirname "$0")"

if [ ! -f ".venv/bin/uvicorn" ]; then
    echo "No .venv found. Run this first:"
    echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
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
open http://localhost:5173 2>/dev/null || xdg-open http://localhost:5173 2>/dev/null

echo ""
echo "Both servers running. Press Ctrl+C here to stop both."
wait
