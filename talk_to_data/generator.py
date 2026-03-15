"""SQL Generator - use LLM to convert natural language to SQL.

This module is a thin wrapper around talk_to_data.core, which is the
single source of truth for SQL generation logic. Both the CLI/Streamlit
app and the backend API use the same core implementation.
"""

from typing import Dict, Any, Optional

from talk_to_data.core.llm import generate_sql as _core_generate_sql
from talk_to_data.core.sql_utils import validate_sql, extract_sql, parse_llm_response  # noqa: F401


def generate_sql(
    question: str,
    schema_prompt: str,
    semantic_prompt: str = "",
    dialect: str = "sqlite",
    provider: str = "anthropic",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate SQL from natural language question using specified LLM provider.

    Args:
        question: Natural language question
        schema_prompt: Schema description from introspector
        semantic_prompt: Semantic context from semantic layer
        dialect: SQL dialect (sqlite, postgresql, mysql, etc.)
        provider: LLM provider ("anthropic" or "openai")
        api_key: API key (or uses env var ANTHROPIC_API_KEY / OPENAI_API_KEY)

    Returns:
        Dict with 'sql', 'explanation', 'confidence', and 'raw_response'
    """
    return _core_generate_sql(
        question=question,
        schema_prompt=schema_prompt,
        semantic_prompt=semantic_prompt,
        dialect=dialect,
        provider=provider,
        api_key=api_key,
    )


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
