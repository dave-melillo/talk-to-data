# Talk To Data v3 - Validation Guide

## Quick Start

```bash
# 1. Start PostgreSQL
docker compose up -d db

# 2. Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY or OPENAI_API_KEY

# 3. Run migrations
alembic upgrade head

# 4. Start backend
uvicorn app.main:app --reload
# API running at http://localhost:8000

# 5. Start frontend (new terminal)
cd frontend
npm install
npm run dev
# UI running at http://localhost:3000
```

## Test Data

Use the Chinook sample database (music store data):
- Download: https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite

Or use this sample CSV for quick testing:

**customers.csv**
```csv
customer_id,name,email,city,total_orders,lifetime_value
1,Alice Smith,alice@example.com,NYC,15,2500.00
2,Bob Johnson,bob@example.com,LA,8,1200.00
3,Carol Williams,carol@example.com,Chicago,22,4500.00
4,Dave Brown,dave@example.com,Miami,5,800.00
5,Eve Davis,eve@example.com,Seattle,30,6000.00
```

**orders.csv**
```csv
order_id,customer_id,order_date,total,status
1,1,2024-01-15,150.00,completed
2,1,2024-02-20,200.00,completed
3,2,2024-01-22,100.00,completed
4,3,2024-03-01,500.00,completed
5,3,2024-03-05,300.00,pending
```

---

## Acceptance Criteria Checklist

### Must Have (Ship Blockers)

- [ ] **Upload CSV file, auto-normalize to PostgreSQL**
  - Go to Upload tab
  - Upload customers.csv
  - Verify preview shows correct columns/types
  - Click "Upload and Import"
  - Confirm success message

- [ ] **Auto-generate DATA SEMANTIC**
  - After upload, call: `POST /api/v1/semantic/{table_id}/generate`
  - Check table description and column descriptions are generated

- [ ] **Accept BIZ SEMANTIC from user**
  - Call: `POST /api/v1/biz-semantic/{table_id}/glossary`
  - Body: `{"terms": {"high_value": "lifetime_value > 2000"}}`
  - Verify it persists

- [ ] **Generate SQL from natural language**
  - In Chat tab, ask: "Who are my top 5 customers by lifetime value?"
  - Verify SQL is generated and displayed

- [ ] **Validate SQL for safety (SELECT only)**
  - Call: `POST /api/v1/queries/validate`
  - Body: `{"sql": "DROP TABLE customers"}`
  - Verify it's rejected with BLOCKED_KEYWORD error

- [ ] **Execute query and display results in table**
  - Query should execute automatically
  - Results displayed in table format
  - Verify row count shown

- [ ] **Single LLM provider working**
  - Verify queries generate with Claude (or GPT-4o if configured)

### Should Have

- [ ] **Auto-detect chart type for output**
  - Query: "Show me monthly order totals"
  - Verify chart appears (should auto-detect line chart for time series)

- [ ] **Export results (CSV and Excel)**
  - Click Export dropdown
  - Download CSV
  - Verify file contains correct data

- [ ] **Query history with recall**
  - Make several queries
  - Call: `GET /api/v1/queries/history/recent`
  - Verify queries are logged

### Edge Cases

- [ ] **Malformed CSV handling**
  - Upload a broken CSV (missing columns, bad encoding)
  - Verify helpful error message, not crash

- [ ] **Empty query handling**
  - Submit empty question
  - Verify graceful handling

- [ ] **SQL generation failure**
  - Ask something impossible: "What's the weather?"
  - Verify helpful error message

---

## API Endpoints to Test

| Method | Endpoint | Test |
|--------|----------|------|
| GET | `/health` | Returns `{"status": "ok"}` |
| GET | `/api/v1/health` | Returns DB status |
| POST | `/api/v1/upload/preview` | Preview file before import |
| POST | `/api/v1/normalize/upload-and-normalize` | One-step upload + normalize |
| GET | `/api/v1/tables/` | List all tables |
| POST | `/api/v1/semantic/{id}/generate` | Generate DATA SEMANTIC |
| POST | `/api/v1/queries/generate` | NL to SQL |
| POST | `/api/v1/queries/validate` | Validate SQL safety |

---

## Known Limitations (v3.0)

1. Single-tenant only (no auth)
2. Max 100MB file upload
3. PostgreSQL only (no external DB connections yet)
4. No scheduled reports
5. No voice input

---

## Validation Result

| Criterion | Pass/Fail | Notes |
|-----------|-----------|-------|
| CSV upload + normalize | | |
| DATA SEMANTIC generation | | |
| BIZ SEMANTIC user input | | |
| NL to SQL generation | | |
| SQL safety validation | | |
| Query execution + display | | |
| Chart auto-detection | | |
| Export (CSV/Excel/JSON) | | |
| Query history | | |
| Error handling | | |

**Overall:** [ ] PASS / [ ] FAIL

**Validator:** _______________
**Date:** _______________
