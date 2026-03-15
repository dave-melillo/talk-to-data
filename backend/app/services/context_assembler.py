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


def format_conversation_history(history: list[dict]) -> str:
    """
    Format recent conversation history for inclusion in the LLM prompt.

    Provides context so the LLM can resolve references like 'that', 'those',
    'filter it', etc. to previous queries.
    """
    if not history:
        return ""

    lines = ["## Conversation Context",
             "The user has asked these questions previously in this session:"]
    for i, entry in enumerate(history, 1):
        status = "succeeded" if entry.get("success", True) else "failed"
        lines.append(f"{i}. Q: '{entry['question']}' → SQL that {status}")
        # Include the SQL so the LLM can reference columns/tables
        sql_preview = entry.get("sql", "")
        if sql_preview:
            lines.append(f"   SQL: {sql_preview}")

    lines.append("")
    lines.append(
        "When the user says 'that', 'those', 'filter it', 'add to it', etc., "
        "they are referring to the previous query context."
    )
    return "\n".join(lines)


def format_prompt(context: dict[str, str]) -> str:
    """
    Format the assembled context into a prompt for the LLM.
    """
    conversation_section = context.get("conversation_history", "")
    conversation_block = f"\n\n{conversation_section}" if conversation_section else ""

    return f"""{context['schema']}

{context['business_context']}

{context['examples']}{conversation_block}

---

## User Question
"{context['question']}"

## Instructions
Generate a PostgreSQL query to answer the user's question.

Rules:
1. Use ONLY SELECT statements (no INSERT/UPDATE/DELETE)
2. Reference only tables and columns that exist in the schema
3. Use table aliases (e.g., "orders o") for complex queries
4. Include a brief SQL comment explaining the logic
5. Format the SQL with proper indentation
6. If the question is ambiguous, make reasonable assumptions and note them in comments
7. If the user refers to a previous query ('that', 'those', 'filter it'), use the conversation context to understand what they mean

Generate the SQL query:
"""


def assemble_query_prompt(
    db: Session,
    question: str,
    tables: list[Table] | None = None,
    conversation_history: list[dict] | None = None,
) -> str:
    """
    Main entry point: assemble context and format as prompt.
    """
    context = assemble_context(db, question, tables)
    if conversation_history:
        context["conversation_history"] = format_conversation_history(
            conversation_history
        )
    return format_prompt(context)
