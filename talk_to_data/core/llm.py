"""Shared LLM integration for SQL generation.

This is the single source of truth for LLM-based SQL generation,
used by both the CLI and backend. Supports direct Anthropic/OpenAI
clients (for standalone CLI use) and LiteLLM (for backend use).
"""

import os
import re
import time
from typing import Any, Optional

from talk_to_data.core.sql_utils import parse_llm_response


def build_system_prompt(
    schema_prompt: str,
    semantic_prompt: str = "",
    dialect: str = "sqlite",
) -> str:
    """Build the system prompt for SQL generation."""
    return f"""You are an expert SQL query generator. Your task is to convert natural language questions into valid {dialect.upper()} SQL queries.

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


def generate_sql_with_anthropic(
    question: str,
    system_prompt: str,
    api_key: Optional[str] = None,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """
    Generate SQL using Anthropic Claude (direct client).

    Returns dict with 'sql', 'explanation', 'confidence', 'raw_response'.
    """
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    start_time = time.time()
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[
            {"role": "user", "content": f"Convert this question to SQL: {question}"}
        ],
    )
    generation_time_ms = int((time.time() - start_time) * 1000)

    response_text = message.content[0].text
    result = parse_llm_response(response_text)
    result["generation_time_ms"] = generation_time_ms
    result["provider"] = "anthropic"
    result["model"] = model
    return result


def generate_sql_with_openai(
    question: str,
    system_prompt: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """
    Generate SQL using OpenAI GPT (direct client).

    Returns dict with 'sql', 'explanation', 'confidence', 'raw_response'.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("OpenAI library not installed. Run: pip install openai")

    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    start_time = time.time()
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Convert this question to SQL: {question}"},
        ],
    )
    generation_time_ms = int((time.time() - start_time) * 1000)

    response_text = response.choices[0].message.content
    result = parse_llm_response(response_text)
    result["generation_time_ms"] = generation_time_ms
    result["provider"] = "openai"
    result["model"] = model
    return result


def generate_sql(
    question: str,
    schema_prompt: str,
    semantic_prompt: str = "",
    dialect: str = "sqlite",
    provider: str = "anthropic",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """
    Generate SQL from a natural language question.

    This is the unified entry point for SQL generation. It builds the
    prompt and routes to the appropriate LLM provider.

    Args:
        question: Natural language question
        schema_prompt: Schema description string
        semantic_prompt: Business context string
        dialect: SQL dialect (sqlite, postgresql, mysql)
        provider: LLM provider ("anthropic" or "openai")
        api_key: API key (or uses env var)
        model: Model override (uses provider default if not set)
        max_tokens: Max response tokens
        temperature: Sampling temperature

    Returns:
        Dict with 'sql', 'explanation', 'confidence', 'raw_response',
        'generation_time_ms', 'provider', 'model'
    """
    system_prompt = build_system_prompt(schema_prompt, semantic_prompt, dialect)

    if provider == "anthropic":
        return generate_sql_with_anthropic(
            question,
            system_prompt,
            api_key=api_key,
            model=model or "claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            temperature=temperature,
        )
    elif provider == "openai":
        return generate_sql_with_openai(
            question,
            system_prompt,
            api_key=api_key,
            model=model or "gpt-4o",
            max_tokens=max_tokens,
            temperature=temperature,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}. Choose 'anthropic' or 'openai'.")
