# Migration Guide: v2 → v3

## Overview
Talk To Data v3 is a complete rewrite with a modern architecture:

| Aspect | v2 (Streamlit) | v3 (FastAPI + Next.js) |
|--------|----------------|------------------------|
| Frontend | Streamlit (`app.py`) | Next.js 14 + React |
| Backend | Embedded in Streamlit | FastAPI (separate service) |
| Database | In-memory SQLite | PostgreSQL (persistent) |
| LLM | Direct API calls | LiteLLM (multi-provider) |
| Deployment | `streamlit run app.py` | Docker Compose |

## What Changed

### Architecture
- **Separated concerns:** Frontend (Next.js) and Backend (FastAPI) are now separate services
- **Persistent storage:** PostgreSQL instead of temporary SQLite
- **API-first:** All functionality exposed via REST API
- **Query history:** All queries are logged for recall and improvement

### Features Added (v3)
- ✅ **DATA SEMANTIC layer** - Auto-generated table/column descriptions
- ✅ **BIZ SEMANTIC layer** - User-provided business context (glossary, KPIs, caveats)
- ✅ **Query history** - Search and recall previous queries
- ✅ **SQL validation** - Safety checks before execution
- ✅ **Multi-table normalization** - Better CSV import with foreign keys
- ✅ **Chart auto-detection** - Smarter visualization selection

### Features Removed (v3)
- ❌ **Streamlit UI** - Replaced with Next.js (modern, faster)
- ❌ **SQLite** - Replaced with PostgreSQL (production-ready)
- ❌ **Semantic config upload** - Now managed via API, not file upload

## Migration Steps

### If You Were Using v2 CSV Upload
1. Keep your CSV files
2. Follow v3 setup in main README
3. Upload CSVs via the new Upload tab
4. Generate DATA SEMANTIC for each table
5. Optionally add BIZ SEMANTIC via API

### If You Were Using v2 with Custom Database
v3 currently only supports CSV upload → PostgreSQL normalization.

**Workaround:** Export your database tables to CSV, then upload to v3.

**Future:** v3 will support direct database connections (planned for v3.2).

### If You Had Custom Semantic Configs (YAML)
Convert your v2 YAML configs to v3 BIZ SEMANTIC via API:

**v2 Config:**
```yaml
glossary:
  active_customer: "Customer with order in last 90 days"
kpis:
  total_revenue: "SUM(order_total) WHERE status = 'completed'"
```

**v3 API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/biz-semantic/{table_id}/glossary \
  -H "Content-Type: application/json" \
  -d '{
    "glossary": {
      "active_customer": "Customer with order in last 90 days"
    },
    "kpis": {
      "total_revenue": "SUM(order_total) WHERE status = 'completed'"
    }
  }'
```

## Running v2 (Legacy)

If you need to run v2 for any reason:

```bash
cd archive/v2
python -m venv venv
source venv/bin/activate
pip install -r requirements-v2.txt
streamlit run app.py
```

**Note:** v2 is no longer maintained. Please migrate to v3.

## Need Help?

Open an issue: https://github.com/dave-melillo/talk-to-data/issues
