"""SQL Generator - use LLM to convert natural language to SQL."""

import os
import re
from typing import Dict, Any, Optional
from anthropic import Anthropic


def generate_sql(
    question: str,
    schema_prompt: str,
    semantic_prompt: str = "",
    dialect: str = "sqlite",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate SQL from natural language question using Claude.
    
    Args:
        question: Natural language question
        schema_prompt: Schema description from introspector
        semantic_prompt: Semantic context from semantic layer
        dialect: SQL dialect (sqlite, postgresql, mysql, etc.)
        api_key: Anthropic API key (or uses ANTHROPIC_API_KEY env var)
    
    Returns:
        Dict with 'sql', 'explanation', and 'confidence'
    """
    client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
    
    system_prompt = f"""You are an expert SQL query generator. Your task is to convert natural language questions into valid {dialect.upper()} SQL queries.

RULES:
1. Generate ONLY valid {dialect.upper()} SQL
2. Use proper JOIN syntax when relating tables
3. Always use table aliases for clarity
4. Include appropriate WHERE, GROUP BY, ORDER BY clauses as needed
5. Limit results to reasonable amounts (use LIMIT if appropriate)
6. If the question is ambiguous, make reasonable assumptions

{schema_prompt}

{semantic_prompt}

OUTPUT FORMAT:
Return your response in this exact format:
```sql
YOUR SQL QUERY HERE
```

EXPLANATION: Brief explanation of what the query does

CONFIDENCE: high/medium/low
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": f"Convert this question to SQL: {question}"}
        ]
    )
    
    response_text = message.content[0].text
    
    # Parse response
    sql_match = re.search(r'```sql\s*(.*?)\s*```', response_text, re.DOTALL)
    sql = sql_match.group(1).strip() if sql_match else ""
    
    explanation_match = re.search(r'EXPLANATION:\s*(.+?)(?=CONFIDENCE:|$)', response_text, re.DOTALL)
    explanation = explanation_match.group(1).strip() if explanation_match else ""
    
    confidence_match = re.search(r'CONFIDENCE:\s*(high|medium|low)', response_text, re.IGNORECASE)
    confidence = confidence_match.group(1).lower() if confidence_match else "medium"
    
    return {
        "sql": sql,
        "explanation": explanation,
        "confidence": confidence,
        "raw_response": response_text
    }


def validate_sql(sql: str, dialect: str = "sqlite") -> Dict[str, Any]:
    """
    Basic SQL validation (syntax check).
    
    Args:
        sql: SQL query string
        dialect: SQL dialect
    
    Returns:
        Dict with 'valid' bool and 'error' message if invalid
    """
    # Basic validation - check for common issues
    sql_upper = sql.upper().strip()
    
    if not sql_upper:
        return {"valid": False, "error": "Empty SQL query"}
    
    # Must start with valid SQL keyword
    valid_starts = ["SELECT", "WITH", "EXPLAIN"]
    if not any(sql_upper.startswith(kw) for kw in valid_starts):
        return {"valid": False, "error": "Query must start with SELECT or WITH"}
    
    # Check for balanced parentheses
    if sql.count("(") != sql.count(")"):
        return {"valid": False, "error": "Unbalanced parentheses"}
    
    # Check for dangerous operations (we only allow SELECT)
    dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE"]
    for kw in dangerous:
        if kw in sql_upper.split():
            return {"valid": False, "error": f"Dangerous operation not allowed: {kw}"}
    
    return {"valid": True, "error": None}


if __name__ == "__main__":
    # Test
    schema = """DATABASE SCHEMA:
    
TABLE: artists
  - ArtistId: INTEGER [PK]
  - Name: TEXT

TABLE: albums
  - AlbumId: INTEGER [PK]
  - Title: TEXT
  - ArtistId: INTEGER

RELATIONSHIPS:
  albums.ArtistId -> artists.ArtistId
"""
    
    result = generate_sql(
        "How many albums does each artist have?",
        schema,
        ""
    )
    print(result)
