"""
Context assembler for the query engine.

Combines DATA SEMANTIC, BIZ SEMANTIC, and reference QUERIES into
a single context window for the LLM.

Includes:
- Schema description
- Business context
- Example queries (few-shot learning)
- Query-specific instructions
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models.table import Table
from app.services.biz_semantic import format_biz_semantic_for_context
from app.services.data_semantic import generate_schema_summary


def assemble_context(
    db: Session,
    question: str,
    tables: list[Table] | None = None,
    include_examples: bool = True,
    max_context_tokens: int = 6000,
) -> dict[str, str]:
    """
    Assemble context for the query engine.
    
    Returns components that can be formatted into the prompt.
    """
    if tables is None:
        tables = db.query(Table).all()
    
    # Schema section
    schema = generate_schema_summary(db, tables)
    
    # Business context section
    biz_context = ""
    for table in tables:
        if table.biz_semantic:
            biz_context += format_biz_semantic_for_context(table.biz_semantic)
    
    # Example queries (if available)
    examples = ""
    if include_examples:
        examples = generate_example_queries()
    
    # Truncate if too long
    # Approximation: 4 chars per token (rough estimate)
    total_chars = len(schema) + len(biz_context) + len(examples)
    max_chars = max_context_tokens * 4
    
    if total_chars > max_chars:
        # Priority: schema > biz context > examples
        if len(schema) > max_chars * 0.5:
            # Truncate schema by selecting only most relevant tables
            schema = schema[: int(max_chars * 0.5)]
        remaining = max_chars - len(schema)
        if len(biz_context) > remaining * 0.5:
            biz_context = biz_context[: int(remaining * 0.5)]
        remaining -= len(biz_context)
        if len(examples) > remaining:
            examples = examples[:remaining]
    
    return {
        "schema": schema,
        "business_context": biz_context,
        "examples": examples,
        "question": question,
    }


def generate_example_queries() -> str:
    """Generate example queries for few-shot learning."""
    return """## Example Queries

### Example 1: Count with filter
**Question:** How many orders were placed last month?
**SQL:**
```sql
SELECT COUNT(*) AS order_count
FROM orders
WHERE created_at >= DATE_TRUNC('month', NOW() - INTERVAL '1 month')
  AND created_at < DATE_TRUNC('month', NOW());
```

### Example 2: Aggregation with join
**Question:** What are the top 5 customers by revenue?
**SQL:**
```sql
SELECT 
    c.customer_id,
    c.name,
    SUM(o.total) AS total_revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.name
ORDER BY total_revenue DESC
LIMIT 5;
```

### Example 3: Date filtering
**Question:** Show me all orders from Q1 2024
**SQL:**
```sql
SELECT *
FROM orders
WHERE created_at >= '2024-01-01'
  AND created_at < '2024-04-01'
ORDER BY created_at DESC;
```

### Example 4: Grouping with multiple metrics
**Question:** What's the monthly order count and revenue for 2024?
**SQL:**
```sql
SELECT 
    DATE_TRUNC('month', created_at) AS month,
    COUNT(*) AS order_count,
    SUM(total) AS revenue
FROM orders
WHERE created_at >= '2024-01-01'
  AND created_at < '2025-01-01'
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month;
```

"""


def format_prompt(context: dict[str, str]) -> str:
    """
    Format the assembled context into a prompt for the LLM.
    """
    error_section = ""
    if context.get("error_context"):
        error_section = f"""
## Previous Attempt Failed
The previously generated SQL failed with the following error:
{context['error_context']}

Please fix the issue and generate a corrected query.

"""

    return f"""{context['schema']}

{context['business_context']}

{context['examples']}

---

## User Question
"{context['question']}"
{error_section}
## Instructions
Generate a PostgreSQL query to answer the user's question.

Rules:
1. Use ONLY SELECT statements (no INSERT/UPDATE/DELETE)
2. Reference only tables and columns that exist in the schema
3. Use table aliases (e.g., "orders o") for complex queries
4. Include a brief SQL comment explaining the logic
5. Format the SQL with proper indentation
6. If the question is ambiguous, make reasonable assumptions and note them in comments

Generate the SQL query:
"""


def assemble_query_prompt(
    db: Session,
    question: str,
    tables: list[Table] | None = None,
    error_context: str | None = None,
) -> str:
    """
    Main entry point: assemble context and format as prompt.
    """
    context = assemble_context(db, question, tables)
    if error_context:
        context["error_context"] = error_context
    return format_prompt(context)
