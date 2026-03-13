#!/bin/bash
# Talk To Data v3 - One-Command Setup
# Usage: ./setup.sh

set -e

echo "🚀 Talk To Data v3 Setup"
echo "========================"

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker required. Install from https://docker.com"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3.11+ required"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ Node.js 18+ required"; exit 1; }

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "${YELLOW}Step 1/5: Starting PostgreSQL...${NC}"
docker compose up -d db
sleep 3

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
for i in {1..30}; do
    if docker exec ttd-postgres pg_isready -U ttd -d talktodata >/dev/null 2>&1; then
        echo "${GREEN}✓ PostgreSQL ready${NC}"
        break
    fi
    sleep 1
done

echo ""
echo "${YELLOW}Step 2/5: Setting up backend...${NC}"
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install dependencies
pip install --upgrade pip wheel setuptools -q
pip install -r requirements.txt -q
echo "${GREEN}✓ Backend dependencies installed${NC}"

# Setup .env if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "${YELLOW}⚠️  Edit backend/.env and add your API key:${NC}"
    echo "   ANTHROPIC_API_KEY=sk-ant-..."
    echo "   or OPENAI_API_KEY=sk-..."
fi

# Run migrations
alembic upgrade head
echo "${GREEN}✓ Database migrations complete${NC}"

cd ..

echo ""
echo "${YELLOW}Step 3/5: Setting up frontend...${NC}"
cd frontend
npm install --silent
echo "${GREEN}✓ Frontend dependencies installed${NC}"
cd ..

echo ""
echo "${YELLOW}Step 4/5: Loading example data...${NC}"
# Load example data via API (backend must be running)
cd backend
source venv/bin/activate

# Start backend temporarily to load data
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
sleep 3

# Load example CSV
curl -s -X POST http://127.0.0.1:8000/api/v1/normalize/upload-and-normalize \
  -F "file=@../examples/sample_ecommerce.csv" \
  -F "source_name=Sample E-Commerce Data" > /dev/null 2>&1 && echo "${GREEN}✓ Example data loaded${NC}" || echo "${YELLOW}⚠️ Example data load skipped (add API key first)${NC}"

# Stop temporary backend
kill $BACKEND_PID 2>/dev/null || true
cd ..

echo ""
echo "${YELLOW}Step 5/5: Setup complete!${NC}"
echo ""
echo "=========================================="
echo "${GREEN}🎉 Talk To Data is ready!${NC}"
echo "=========================================="
echo ""
echo "To start the application:"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd backend"
echo "    source venv/bin/activate"
echo "    uvicorn app.main:app --reload"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd frontend"
echo "    npm run dev"
echo ""
echo "Then open: http://localhost:3000"
echo ""
echo "⚠️  Don't forget to add your API key to backend/.env!"
echo ""
