"""
Context assembler for the query engine.

Combines DATA SEMANTIC, BIZ SEMANTIC, and reference QUERIES into
a single context window for the LLM.

Includes:
- Schema description
- Business context
- Example queries (few-shot learning)
- Query-specific instructions

NOTE: Uses SEMANTIC truncation — drops entire tables, never truncates mid-structure.
"""

from typing import Any
import re

from sqlalchemy.orm import Session

from app.models.table import Table
from app.services.biz_semantic import format_biz_semantic_for_context
from app.services.data_semantic import generate_schema_summary


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    
    Conservative estimate: ~3 chars per token for structured/code text.
    This is more accurate than 4 chars/token for markdown tables and SQL.
    """
    return len(text) // 3


def truncate_schema_semantically(
    db: Session,
    tables: list[Table],
    question: str,
    max_tokens: int,
) -> str:
    """
    Truncate schema by dropping entire tables, never mid-structure.
    
    Strategy:
    1. Identify tables mentioned in the question (keep these)
    2. Rank remaining tables by relevance (row count, column count)
    3. Include tables until budget exhausted
    """
    question_lower = question.lower()
    
    # Categorize tables
    mentioned_tables = []
    other_tables = []
    
    for table in tables:
        # Check if table name appears in question
        if table.normalized_name.lower() in question_lower:
            mentioned_tables.append(table)
        else:
            other_tables.append(table)
    
    # Sort other tables by relevance heuristic
    # (prefer larger tables and tables with more columns)
    other_tables.sort(
        key=lambda t: (t.row_count or 0) * len(t.columns or []),
        reverse=True,
    )
    
    # Build schema iteratively, stopping when budget hit
    included_tables = []
    budget_used = 0
    
    # Always include mentioned tables first
    for table in mentioned_tables:
        table_schema = generate_schema_summary(db, [table])
        table_tokens = estimate_tokens(table_schema)
        
        if budget_used + table_tokens <= max_tokens:
            included_tables.append(table)
            budget_used += table_tokens
    
    # Add other tables until budget exhausted
    for table in other_tables:
        table_schema = generate_schema_summary(db, [table])
        table_tokens = estimate_tokens(table_schema)
        
        if budget_used + table_tokens <= max_tokens:
            included_tables.append(table)
            budget_used += table_tokens
        else:
            # Stop — can't fit more tables
            break
    
    # Generate final schema with included tables
    if not included_tables:
        # Fallback: if even one table doesn't fit, include the first mentioned one
        # (truncation is better than no schema at all)
        included_tables = mentioned_tables[:1] if mentioned_tables else tables[:1]
    
    return generate_schema_summary(db, included_tables)


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
    
    # Truncate if too long using SEMANTIC truncation
    # Token estimation: ~3 chars per token (conservative for code/structured text)
    total_tokens = estimate_tokens(schema) + estimate_tokens(biz_context) + estimate_tokens(examples)
    
    if total_tokens > max_context_tokens:
        # Priority order: business context > schema > examples
        # Never truncate mid-structure — drop entire sections cleanly
        
        biz_tokens = estimate_tokens(biz_context)
        examples_tokens = estimate_tokens(examples)
        schema_tokens = estimate_tokens(schema)
        
        budget_remaining = max_context_tokens
        
        # 1. Always include full business context (it's critical user input)
        budget_remaining -= biz_tokens
        
        # 2. Drop examples if needed (they're optional)
        if budget_remaining < schema_tokens and examples_tokens > 0:
            examples = ""
            budget_remaining += examples_tokens  # Reclaim
        
        # 3. If schema still too large, drop least relevant tables
        if budget_remaining < schema_tokens:
            schema = truncate_schema_semantically(
                db, tables, question, max_tokens=budget_remaining
            )
        
        # Note: We never truncate biz_context mid-structure
        # If even business context alone exceeds limit, that's a config error
        # (should be caught at upload time)
    
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
    return f"""{context['schema']}

{context['business_context']}

{context['examples']}

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

Generate the SQL query:
"""


def assemble_query_prompt(
    db: Session,
    question: str,
    tables: list[Table] | None = None,
) -> str:
    """
    Main entry point: assemble context and format as prompt.
    """
    context = assemble_context(db, question, tables)
    return format_prompt(context)
