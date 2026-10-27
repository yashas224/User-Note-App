#!/usr/bin/env bash
# Start the FastAPI backend (:8000) and Streamlit frontend (:8501). Ctrl+C stops both.
set -euo pipefail
cd "$(dirname "$0")"

uv run alembic upgrade head

uv run fastapi dev src/user_note/backend/main.py --port 8000 &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null' EXIT

uv run streamlit run src/user_note/frontend/app.py --server.port 8501
