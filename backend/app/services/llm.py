"""
LLM integration service using LiteLLM for multi-provider support.

Supports:
- Anthropic (Claude)
- OpenAI (GPT-4o)
- Google (Gemini)
- Local (Ollama)

Features:
- Automatic retry on rate limits (429) and transient errors (5xx)
- Exponential backoff with jitter
- Max 3 retries
"""

from typing import Any
import time
import random

import litellm
from litellm import completion
from litellm.exceptions import RateLimitError, ServiceUnavailableError, APIError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)
import logging

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RateLimitError, ServiceUnavailableError, APIError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.INFO),
    reraise=True,
)
def _llm_complete_with_retry(
    model_string: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> Any:
    """
    Internal function that wraps LiteLLM completion with retry logic.
    
    Retries on:
    - 429 (Rate Limit) - backs off and retries
    - 5xx (Server Error) - transient errors
    - APIError - generic API failures
    
    Max 3 attempts with exponential backoff (2s, 4s, 8s) + jitter.
    """
    # Add random jitter to avoid thundering herd
    time.sleep(random.uniform(0, 0.5))
    
    return completion(
        model=model_string,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )


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
    
    Includes automatic retry on rate limits and transient errors.
    
    Args:
        prompt: User prompt
        system: Optional system message
        provider: Override default provider
        model: Override default model
        max_tokens: Max response tokens
        temperature: Sampling temperature
    
    Returns:
        Generated text response
    
    Raises:
        RateLimitError: After 3 retries on rate limit
        ServiceUnavailableError: After 3 retries on server error
        APIError: After 3 retries on other API failures
    """
    model_string = _get_model_string(provider, model)
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = _llm_complete_with_retry(
            model_string=model_string,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded after retries: {e}")
        raise Exception(f"LLM API rate limit exceeded. Please try again in a few minutes.") from e
    
    except (ServiceUnavailableError, APIError) as e:
        logger.error(f"LLM API error after retries: {e}")
        raise Exception(f"LLM API temporarily unavailable. Please try again shortly.") from e


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
