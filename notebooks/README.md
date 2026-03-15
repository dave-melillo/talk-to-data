# 📓 Talk To Data - Jupyter Notebook Edition

**Natural Language → SQL** in a single, teachable notebook.

## Quick Start

### Option 1: Google Colab (No Setup)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dave-melillo/talk-to-data/blob/main/notebooks/talk_to_data.ipynb)

1. Click the badge above
2. Add your OpenAI API key when prompted
3. Run all cells

### Option 2: Local Jupyter

```bash
# Clone the repo
git clone https://github.com/dave-melillo/talk-to-data.git
cd talk-to-data/notebooks

# Install dependencies
pip install pandas openai pyyaml jupyter

# Set your API key
export OPENAI_API_KEY="sk-..."

# Launch notebook
jupyter notebook talk_to_data.ipynb
```

## What's Inside

| Cell | Component | Description |
|------|-----------|-------------|
| 1 | **Data Ingestion** | Load CSV, Excel, or connect to databases |
| 2 | **Data Semantic** | AI auto-generates schema understanding |
| 3 | **Biz Semantic** | You provide glossary, KPIs, business rules |
| 4 | **Reference Queries** | Few-shot SQL examples for better accuracy |
| 5 | **Query Engine** | Combines all context → generates SQL |
| 6 | **Execute & Display** | Runs SQL, shows results |

## Sample Data

Included in `sample_data/`:

- `customers.csv` - 20 customers with name, email, location
- `orders.csv` - 40 orders with status and totals
- `products.csv` - 15 products with categories and pricing
- `order_items.csv` - Line items linking orders to products

## Key Concepts

### Data Semantic (AI-Generated)

The AI analyzes your data and generates schema understanding:

```yaml
tables:
  customers:
    description: "Customer records with contact info"
    columns:
      customer_id:
        description: "Unique customer identifier"
        type: "integer"
```

### Business Semantic (User-Provided)

You provide domain knowledge:

```yaml
glossary:
  churned_customer: "No orders in 90 days"
  high_value: "Lifetime revenue > $500"

kpis:
  revenue: "SUM(total) WHERE status='completed'"
```

### Reference Queries

Example question → SQL pairs teach the AI your patterns:

```python
{
    "question": "Top 10 customers by revenue",
    "sql": "SELECT customer_id, SUM(total)..."
}
```

## Supported Data Sources

- **CSV/Excel**: `pd.read_csv()`, `pd.read_excel()`
- **SQLite**: Built-in via `sqlite3`
- **PostgreSQL/MySQL**: Via SQLAlchemy
- **DuckDB**: For large datasets (Parquet, etc.)

## Customization

### Change LLM Provider

```python
# OpenAI (default)
from openai import OpenAI
client = OpenAI(api_key="...")
MODEL = "gpt-4o"

# Anthropic
from anthropic import Anthropic
client = Anthropic(api_key="...")
MODEL = "claude-3-5-sonnet-20241022"
```

### Add More Tables

```python
tables["new_table"] = pd.read_csv("new_data.csv")
```

### Customize Business Rules

Edit the `biz_semantic` string to add your glossary and KPIs.

## Why a Notebook?

| Benefit | Description |
|---------|-------------|
| **Teachable** | Each cell = one concept |
| **Book-ready** | Can walk through step by step |
| **Interactive** | Modify and re-run cells |
| **No infrastructure** | No servers, Docker, deploys |
| **Debuggable** | See exactly what AI generates |
| **Portable** | Share .ipynb file, runs anywhere |

## Related

- [Full Talk To Data App](../README.md) - FastAPI + Next.js version
- [Talk To Data Blog Post](#) - Detailed walkthrough

## License

MIT
