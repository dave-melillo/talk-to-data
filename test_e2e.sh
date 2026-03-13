#!/bin/bash
# Talk To Data v3 - End-to-End Test Script
# Run this to verify the entire application works

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

pass() {
    echo -e "${GREEN}✓ $1${NC}"
    ((PASSED++))
}

fail() {
    echo -e "${RED}✗ $1${NC}"
    echo -e "${RED}  Error: $2${NC}"
    ((FAILED++))
}

echo "========================================"
echo "Talk To Data v3 - End-to-End Test"
echo "========================================"
echo ""

# Test 1: Check Docker
echo "${YELLOW}Test 1: Docker availability${NC}"
if docker ps >/dev/null 2>&1; then
    pass "Docker is running"
else
    fail "Docker not running" "Start Docker Desktop"
    exit 1
fi

# Test 2: Start PostgreSQL
echo ""
echo "${YELLOW}Test 2: PostgreSQL${NC}"
docker compose up -d db >/dev/null 2>&1
sleep 3
if docker exec ttd-postgres pg_isready -U ttd -d talktodata >/dev/null 2>&1; then
    pass "PostgreSQL is ready"
else
    fail "PostgreSQL not ready" "Check docker compose logs db"
fi

# Test 3: Backend health
echo ""
echo "${YELLOW}Test 3: Backend${NC}"
cd backend
source venv/bin/activate 2>/dev/null || { 
    echo "Setting up venv..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt -q
}

# Run migrations
alembic upgrade head >/dev/null 2>&1
pass "Database migrations complete"

# Start backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
sleep 3

HEALTH=$(curl -s http://127.0.0.1:8000/health 2>/dev/null)
if echo "$HEALTH" | grep -q "ok"; then
    pass "Backend health check"
else
    fail "Backend not responding" "$HEALTH"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Test 4: API endpoints
echo ""
echo "${YELLOW}Test 4: API Endpoints${NC}"

# Sources endpoint
SOURCES=$(curl -s http://127.0.0.1:8000/api/v1/sources/)
if echo "$SOURCES" | grep -q "sources"; then
    pass "GET /api/v1/sources/"
else
    fail "Sources endpoint" "$SOURCES"
fi

# Tables endpoint
TABLES=$(curl -s http://127.0.0.1:8000/api/v1/tables/)
if echo "$TABLES" | grep -q "tables"; then
    pass "GET /api/v1/tables/"
else
    fail "Tables endpoint" "$TABLES"
fi

# Test 5: File upload
echo ""
echo "${YELLOW}Test 5: CSV Upload${NC}"

# Create test CSV
cat > /tmp/test_upload.csv << 'EOF'
customer_id,name,email,total_orders
1,Alice,alice@test.com,10
2,Bob,bob@test.com,5
3,Carol,carol@test.com,15
EOF

# Preview
PREVIEW=$(curl -s -X POST http://127.0.0.1:8000/api/v1/upload/preview \
    -F "file=@/tmp/test_upload.csv")
if echo "$PREVIEW" | grep -q "columns"; then
    pass "POST /api/v1/upload/preview"
else
    fail "Upload preview" "$PREVIEW"
fi

# Upload and normalize
UPLOAD=$(curl -s -X POST http://127.0.0.1:8000/api/v1/normalize/upload-and-normalize \
    -F "file=@/tmp/test_upload.csv" \
    -F "source_name=test_customers")
if echo "$UPLOAD" | grep -q "normalized_name"; then
    pass "POST /api/v1/normalize/upload-and-normalize"
    TABLE_ID=$(echo "$UPLOAD" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
else
    fail "Upload and normalize" "$UPLOAD"
fi

# Test 6: Query data
echo ""
echo "${YELLOW}Test 6: Query Data${NC}"

# Get table data
if [ -n "$TABLE_ID" ]; then
    DATA=$(curl -s "http://127.0.0.1:8000/api/v1/tables/$TABLE_ID/data")
    if echo "$DATA" | grep -q "Alice"; then
        pass "GET /api/v1/tables/{id}/data"
    else
        fail "Get table data" "$DATA"
    fi
fi

# Test 7: SQL Validation
echo ""
echo "${YELLOW}Test 7: SQL Validation${NC}"

# Valid SQL
VALID=$(curl -s -X POST http://127.0.0.1:8000/api/v1/queries/validate \
    -H "Content-Type: application/json" \
    -d '{"sql": "SELECT * FROM test_customers"}')
if echo "$VALID" | grep -q '"valid":true'; then
    pass "Valid SQL accepted"
else
    fail "Valid SQL validation" "$VALID"
fi

# Invalid SQL (DROP)
INVALID=$(curl -s -X POST http://127.0.0.1:8000/api/v1/queries/validate \
    -H "Content-Type: application/json" \
    -d '{"sql": "DROP TABLE test_customers"}')
if echo "$INVALID" | grep -q '"valid":false'; then
    pass "Invalid SQL (DROP) rejected"
else
    fail "DROP should be rejected" "$INVALID"
fi

# Clean up
echo ""
echo "${YELLOW}Cleaning up...${NC}"
kill $BACKEND_PID 2>/dev/null || true
rm /tmp/test_upload.csv 2>/dev/null || true
cd ..

# Summary
echo ""
echo "========================================"
echo "Test Results"
echo "========================================"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
