#!/usr/bin/env bash
# ============================================================
# AIVOA Copilot — Demo Setup & Launch Script
# ============================================================
# Prerequisites:
#   - Python 3.10+
#   - Node.js 18+
#   - MySQL running with a database configured (see .env)
#   - Groq API key in backend/.env
#
# Usage:
#   chmod +x demo.sh
#   ./demo.sh            # Full setup + launch
#   ./demo.sh --quick    # Skip pip/npm install
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "============================================"
echo " AIVOA Copilot — Setup & Launch"
echo "============================================"

# ---- Backend Setup ----
echo ""
echo "[1/5] Setting up backend..."

cd "$BACKEND_DIR"

# Check for .env
if [ ! -f .env ]; then
    echo "  -> No .env found. Copying from .env.example..."
    cp .env.example .env
    echo "  -> IMPORTANT: Edit backend/.env and set your GROQ_API_KEY and DATABASE_URL."
fi

# Install Python dependencies
if [ "${1:-}" != "--quick" ]; then
    echo "  -> Installing Python packages..."
    pip install -r requirements.txt --quiet 2>&1 | tail -1
fi

# Generate sample PDF
echo "  -> Generating sample complaint PDF..."
python tests/generate_sample_pdf.py 2>/dev/null || echo "  -> (fpdf2 not installed, skipping PDF generation)"

# Seed demo data
echo "  -> Seeding database with sample complaints..."
python seed_data.py 2>&1 || echo "  -> (Database not available, skip seeding)"

echo "  -> Backend ready."

# ---- Frontend Setup ----
echo ""
echo "[2/5] Setting up frontend..."

cd "$FRONTEND_DIR"

if [ "${1:-}" != "--quick" ] && [ ! -d "node_modules" ]; then
    echo "  -> Installing npm packages..."
    npm install --quiet 2>&1 | tail -1
fi

echo "  -> Frontend ready."

# ---- Launch ----
echo ""
echo "[3/5] Starting backend server (port 8000)..."
cd "$BACKEND_DIR"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "  -> Backend PID: $BACKEND_PID"

echo ""
echo "[4/5] Starting frontend dev server (port 3000)..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
echo "  -> Frontend PID: $FRONTEND_PID"

# Trap to kill both on exit
trap "echo ''; echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

echo ""
echo "============================================"
echo " Both servers are starting up!"
echo ""
echo " Frontend : http://localhost:3000"
echo " Backend  : http://localhost:8000"
echo " API Docs : http://localhost:8000/docs"
echo ""
echo " Press Ctrl+C to stop both servers."
echo "============================================"
echo ""

wait
