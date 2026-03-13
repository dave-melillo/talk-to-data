#!/bin/bash
# Talk To Data v3 - Start Script
# Starts both backend and frontend

set -e

# Check if setup has been run
if [ ! -d "backend/venv" ]; then
    echo "❌ Run ./setup.sh first"
    exit 1
fi

# Start PostgreSQL if not running
docker compose up -d db 2>/dev/null || true

echo "🚀 Starting Talk To Data..."
echo ""

# Start backend in background
echo "Starting backend on http://127.0.0.1:8000..."
cd backend
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend
sleep 2

# Start frontend
echo "Starting frontend on http://localhost:3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Both servers running!"
echo ""
echo "   Backend:  http://127.0.0.1:8000/docs"
echo "   Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

# Wait
wait
