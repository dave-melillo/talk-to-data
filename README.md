# 💬 Talk To Data v3

**Natural Language to SQL** — Ask questions about your data in plain English.

> **📌 Current Version:** v3.0 (FastAPI + Next.js)  
> **Looking for v2 (Streamlit)?** See `archive/v2/` and [migration guide](archive/v2/MIGRATION.md)

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![License](https://img.shields.io/badge/License-MIT-green)

## Quick Start (5 minutes)

### Prerequisites
- Docker
- Python 3.11+
- Node.js 18+
- LLM API key (Anthropic or OpenAI)

### One-Command Setup

```bash
git clone https://github.com/dave-melillo/talk-to-data.git
cd talk-to-data
./setup.sh
```

### Add Your API Key

Edit `backend/.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
# or
OPENAI_API_KEY=sk-xxxxx
```

### Start the App

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:3000**

## Features

- 📤 **Upload CSV/Excel/Parquet** — Auto-normalized to PostgreSQL
- 🧠 **Smart Schema Understanding** — AI generates table/column descriptions
- 📝 **Business Context** — Add glossary, KPIs, and caveats
- 💬 **Natural Language Queries** — Ask questions, get SQL + results
- 📊 **Auto Charts** — Bar, line, pie, scatter (auto-detected)
- 📁 **Export** — CSV, Excel, JSON, clipboard

## Example Queries

After uploading the sample e-commerce data:

- "Who are my top 5 customers by lifetime value?"
- "How many customers signed up each month?"
- "Show me all inactive customers"
- "What's the average order value by city?"

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Next.js UI    │────▶│   FastAPI       │
│   (port 3000)   │     │   (port 8000)   │
└─────────────────┘     └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │   PostgreSQL    │
                        │   (port 5432)   │
                        └─────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React, Tailwind, shadcn/ui, Recharts |
| Backend | FastAPI, SQLAlchemy, Alembic, LiteLLM |
| Database | PostgreSQL 16 |
| LLM | Claude, GPT-4o, Gemini, or Ollama |

## Project Structure

```
talk-to-data/
├── backend/
│   ├── app/
│   │   ├── api/routes/     # API endpoints
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/       # Business logic
│   ├── alembic/            # Database migrations
│   └── tests/              # Pytest tests
├── frontend/
│   ├── app/                # Next.js pages
│   └── components/         # React components
├── examples/               # Sample data
├── setup.sh               # One-command setup
└── docker-compose.yml     # PostgreSQL
```

## API Documentation

Once running, visit: **http://localhost:8000/docs**

## Contributing

PRs welcome! Please run tests before submitting:

```bash
cd backend
pytest
```

## License

MIT
