# Talk To Data v3 - Backend

FastAPI backend for the Talk To Data natural language to SQL system.

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (or use Docker)

### Option 1: Docker (Recommended)

```bash
# From project root
docker compose up -d db

# Run migrations
cd backend
pip install -r requirements.txt
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### Option 2: Local PostgreSQL

```bash
# Create database
createdb talktodata

# Setup environment
cd backend
cp .env.example .env
# Edit .env with your database URL

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Quick health check |
| GET | `/api/v1/health` | Detailed health with DB status |
| GET | `/api/v1/sources` | List data sources |
| GET | `/api/v1/tables` | List tables |
| GET | `/api/v1/queries/history` | Query history |

Full API docs: http://localhost:8000/docs

## Project Structure

```
backend/
├── app/
│   ├── api/routes/     # API endpoints
│   ├── core/           # Config, database
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic schemas
│   └── services/       # Business logic
├── alembic/            # Database migrations
├── tests/              # Pytest tests
└── requirements.txt
```

## Testing

```bash
pytest
```

## Database Schema

- **ttd_sources** - Data sources (CSV uploads, DB connections)
- **ttd_tables** - Normalized tables with metadata
- **ttd_relationships** - Table relationships (auto-detected + user-confirmed)
- **ttd_query_history** - Query audit log
