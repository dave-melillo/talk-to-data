"""
LLM integration service using LiteLLM for multi-provider support.

Supports:
- Anthropic (Claude)
- OpenAI (GPT-4o)
- Google (Gemini)
- Local (Ollama)
"""

from typing import Any

import litellm
from litellm import completion

from app.core.config import get_settings

settings = get_settings()

# Configure LiteLLM
litellm.set_verbose = False


def get_llm_config() -> dict[str, Any]:
    """Get the current LLM configuration."""
    return {
        "provider": settings.default_llm_provider,
        "model": settings.default_llm_model,
    }


def _get_model_string(provider: str | None = None, model: str | None = None) -> str:
    """Get the LiteLLM model string."""
    p = provider or settings.default_llm_provider
    m = model or settings.default_llm_model
    
    # LiteLLM model format
    if p == "anthropic":
        return m  # e.g., "claude-sonnet-4-20250514"
    elif p == "openai":
        return m  # e.g., "gpt-4o"
    elif p == "google":
        return f"gemini/{m}"
    elif p == "ollama":
        return f"ollama/{m}"
    else:
        return m


def llm_complete(
    prompt: str,
    system: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    max_tokens: int = 2000,
    temperature: float = 0.3,
) -> str:
    """
    Complete a prompt using the configured LLM.
    
    Args:
        prompt: User prompt
        system: Optional system message
        provider: Override default provider
        model: Override default model
        max_tokens: Max response tokens
        temperature: Sampling temperature
    
    Returns:
        Generated text response
    """
    model_string = _get_model_string(provider, model)
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    response = completion(
        model=model_string,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    
    return response.choices[0].message.content or ""


def generate_table_description(
    table_name: str,
    columns: list[dict[str, Any]],
    sample_rows: list[dict[str, Any]] | None = None,
) -> str:
    """
    Generate a natural language description of a table.
    
    Uses LLM to analyze column names and sample data to infer purpose.
    """
    col_summary = "\n".join([
        f"- {c['name']}: {c.get('data_type', 'unknown')} "
        f"(distinct: {c.get('distinct_count', '?')}, nulls: {c.get('null_count', 0)})"
        for c in columns[:20]  # Limit columns
    ])
    
    sample_str = ""
    if sample_rows:
        sample_str = f"\n\nSample data (first 3 rows):\n{sample_rows[:3]}"
    
    prompt = f"""Analyze this database table and write a one-sentence description of what it contains.

Table name: {table_name}

Columns:
{col_summary}
{sample_str}

Write a single sentence describing what this table stores (e.g., "Customer contact information and preferences" or "Sales transactions with product and customer references").

Description:"""

    system = "You are a database analyst. Provide concise, accurate table descriptions based on schema and data."
    
    try:
        description = llm_complete(prompt, system=system, max_tokens=100, temperature=0.2)
        return description.strip().strip('"')
    except Exception as e:
        return f"Table containing {len(columns)} columns"


def generate_column_description(
    column_name: str,
    data_type: str,
    sample_values: list[Any],
    table_context: str = "",
) -> str:
    """
    Generate a natural language description of a column.
    
    DEPRECATED: Use generate_all_column_descriptions() for better performance.
    This makes one API call per column which is slow and expensive.
    """
    samples = str(sample_values[:5]) if sample_values else "no samples"
    
    prompt = f"""Describe this database column in one brief phrase.

Column: {column_name}
Type: {data_type}
Sample values: {samples}
{f"Table context: {table_context}" if table_context else ""}

Description (one phrase, e.g., "Customer email address" or "Order creation timestamp"):"""

    try:
        description = llm_complete(prompt, max_tokens=50, temperature=0.2)
        return description.strip().strip('"')
    except Exception:
        return f"{data_type} field"


def generate_all_column_descriptions(
    table_name: str,
    columns: list[dict[str, Any]],
    table_context: str = "",
) -> dict[str, str]:
    """
    Generate descriptions for ALL columns in ONE LLM call.
    
    Much faster and cheaper than calling generate_column_description() per column.
    
    Returns:
        Dict mapping column_name -> description
    """
    if not columns:
        return {}
    
    # Build column summary for prompt
    col_lines = []
    for col in columns:
        name = col.get("name", "")
        dtype = col.get("data_type", "unknown")
        samples = col.get("sample_values", [])[:3]
        samples_str = str(samples) if samples else "no samples"
        
        col_lines.append(f"- {name} ({dtype}): {samples_str}")
    
    col_summary = "\n".join(col_lines[:50])  # Limit to first 50 columns
    
    prompt = f"""Analyze this database table and write a brief description for EACH column.

Table: {table_name}
{f"Context: {table_context}" if table_context else ""}

Columns:
{col_summary}

For each column, write a concise description (3-8 words). Output as:
column_name: description

Example:
customer_id: Unique customer identifier
email: Customer email address
created_at: Account creation timestamp

Now describe each column:"""

    system = "You are a database analyst. Provide concise, accurate column descriptions."
    
    try:
        response = llm_complete(prompt, system=system, max_tokens=500, temperature=0.2)
        
        # Parse response into dict
        descriptions = {}
        for line in response.strip().split("\n"):
            if ":" in line:
                parts = line.split(":", 1)
                col_name = parts[0].strip()
                desc = parts[1].strip().strip('"').strip("'")
                descriptions[col_name] = desc
        
        return descriptions
    
    except Exception as e:
        # Fallback: return generic descriptions
        return {
            col.get("name", ""): f"{col.get('data_type', 'unknown')} field"
            for col in columns
        }
