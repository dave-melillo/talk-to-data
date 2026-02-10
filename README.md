# 💬 Talk To Data

**Natural Language to SQL** — Ask questions about your data in plain English.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## What is this?

Talk To Data is a local, database-agnostic tool that converts natural language questions into SQL queries. It works with any SQL database and uses a semantic layer to understand your data context.

**Example:**
```
Question: "Which artists have the most albums?"

Generated SQL:
SELECT ar.Name, COUNT(al.AlbumId) as album_count 
FROM artists ar 
LEFT JOIN albums al ON ar.ArtistId = al.ArtistId 
GROUP BY ar.ArtistId, ar.Name 
ORDER BY album_count DESC
```

## Features

- 🔌 **Database Agnostic** — Works with PostgreSQL, MySQL, SQLite, Snowflake, and more
- 🧠 **Smart Schema Introspection** — Automatically understands your tables and relationships
- 📝 **Semantic Layer** — Add business context with YAML configuration
- 🎯 **Reference Queries** — Few-shot learning with example SQL
- 🖥️ **Demo UI** — Streamlit app for easy demonstrations
- ✅ **SQL Validation** — Safety checks before execution

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your API key

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### 3. Run the demo

```bash
streamlit run app.py
```

The app will open with the Chinook music store database pre-loaded.

## How It Works

```
┌──────────────────────────────────────────────────────┐
│                   Natural Language                    │
│            "Who are the top customers?"              │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│                  Schema Introspector                  │
│         Extract tables, columns, relationships        │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│                   Semantic Layer                      │
│      Business terms, descriptions, examples          │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│                   SQL Generator                       │
│            Claude LLM + structured prompt             │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│                    Valid SQL                          │
│  SELECT c.FirstName, SUM(i.Total) FROM customers...  │
└──────────────────────────────────────────────────────┘
```

## Semantic Configuration

Create a YAML file to add business context:

```yaml
database: my_database
description: "E-commerce platform with orders, products, and customers"

tables:
  orders:
    description: "Customer purchase orders"
    columns:
      order_id: "Unique order identifier"
      total: "Order total in USD"
    business_terms:
      - "purchase" = "order"
      - "revenue" = "total"

reference_queries:
  - question: "What's the total revenue?"
    sql: "SELECT SUM(total) as revenue FROM orders"
```

## Project Structure

```
talk-to-data/
├── app.py                    # Streamlit demo UI
├── requirements.txt          # Python dependencies
├── talk_to_data/
│   ├── introspector.py       # Schema extraction
│   ├── semantic.py           # YAML config loading
│   ├── generator.py          # LLM SQL generation
│   └── executor.py           # Query execution
├── config/
│   └── chinook.yaml          # Demo semantic config
└── data/
    └── chinook.db            # Demo SQLite database
```

## Using with Your Database

1. **Connect** — Change the connection string in the sidebar
2. **Configure** — Create a semantic YAML for your schema (optional but recommended)
3. **Ask** — Type questions in plain English
4. **Execute** — Review the SQL and run it

### Connection String Examples

```
# PostgreSQL
postgresql://user:password@localhost:5432/mydb

# MySQL
mysql+pymysql://user:password@localhost:3306/mydb

# SQLite
sqlite:///path/to/database.db

# Snowflake
snowflake://user:password@account/database/schema
```

## Limitations

- Read-only queries (SELECT only for safety)
- Works best with well-structured relational data
- Complex analytical queries may need refinement
- Semantic layer improves accuracy significantly

## License

MIT

## Author

Dave Melillo — [DataDeck Consulting](https://datadeck.io)
