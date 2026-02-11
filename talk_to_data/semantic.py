"""Semantic layer - load and manage table/column descriptions and reference queries."""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional


def load_semantic_config(config_path: str) -> Dict[str, Any]:
    """
    Load semantic configuration from YAML file.
    
    Args:
        config_path: Path to YAML config file
    
    Returns:
        Parsed semantic configuration
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config or {}


def get_reference_queries(semantic: Dict[str, Any], limit: int = 5) -> List[Dict[str, str]]:
    """
    Get reference queries for few-shot learning.
    
    Args:
        semantic: Semantic config dict
        limit: Max number of reference queries to return
    
    Returns:
        List of {question, sql} dicts
    """
    refs = semantic.get("reference_queries", [])
    return refs[:limit]


def get_business_terms(semantic: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract business term mappings from semantic config.
    
    Args:
        semantic: Semantic config dict
    
    Returns:
        Dict mapping user terms to database terms
    """
    terms = {}
    
    for table_name, table_info in semantic.get("tables", {}).items():
        table_terms = table_info.get("business_terms", {})
        if isinstance(table_terms, dict):
            # New format: dict of {user_term: db_term}
            terms.update(table_terms)
        elif isinstance(table_terms, list):
            # Legacy format: list of "user_term = db_term" strings (for backwards compatibility)
            for term_mapping in table_terms:
                if "=" in term_mapping:
                    user_term, db_term = term_mapping.split("=", 1)
                    terms[user_term.strip().strip('"')] = db_term.strip().strip('"')
    
    return terms


def semantic_to_prompt(semantic: Dict[str, Any]) -> str:
    """
    Convert semantic config to prompt-friendly context.
    
    Args:
        semantic: Semantic config dict
    
    Returns:
        String for LLM prompt
    """
    lines = []
    
    # Database description
    if semantic.get("description"):
        lines.append(f"DATABASE CONTEXT: {semantic['description']}")
        lines.append("")
    
    # Business terms
    terms = get_business_terms(semantic)
    if terms:
        lines.append("BUSINESS TERMS (user term = database term):")
        for user_term, db_term in terms.items():
            lines.append(f"  \"{user_term}\" means \"{db_term}\"")
        lines.append("")
    
    # Reference queries
    refs = get_reference_queries(semantic)
    if refs:
        lines.append("EXAMPLE QUERIES:")
        for ref in refs:
            lines.append(f"  Q: {ref.get('question', '')}")
            lines.append(f"  SQL: {ref.get('sql', '')}")
            lines.append("")
    
    return "\n".join(lines)


def create_sample_config() -> str:
    """Generate sample semantic config YAML."""
    return '''# Semantic configuration for Chinook database
database: chinook
description: "Music store database with artists, albums, tracks, invoices, and customers"

tables:
  artists:
    description: "Music artists and bands"
    columns:
      ArtistId: "Unique identifier for the artist"
      Name: "Artist or band name"

  albums:
    description: "Albums released by artists"
    columns:
      AlbumId: "Unique identifier for the album"
      Title: "Album title"
      ArtistId: "Foreign key to artists table"

  tracks:
    description: "Individual songs/tracks on albums"
    columns:
      TrackId: "Unique identifier for the track"
      Name: "Track/song name"
      AlbumId: "Foreign key to albums table"
      MediaTypeId: "Type of media (MP3, AAC, etc.)"
      GenreId: "Music genre"
      Composer: "Song composer(s)"
      Milliseconds: "Track duration in milliseconds"
      Bytes: "File size in bytes"
      UnitPrice: "Price per track"
    business_terms:
      song: track
      length: Milliseconds
      duration: Milliseconds

  genres:
    description: "Music genres (Rock, Jazz, etc.)"
    columns:
      GenreId: "Unique identifier"
      Name: "Genre name"

  customers:
    description: "Store customers"
    columns:
      CustomerId: "Unique identifier"
      FirstName: "Customer first name"
      LastName: "Customer last name"
      Email: "Email address"
      Country: "Customer country"

  invoices:
    description: "Customer purchase invoices"
    columns:
      InvoiceId: "Unique identifier"
      CustomerId: "Foreign key to customers"
      InvoiceDate: "Date of purchase"
      Total: "Total amount"

  invoice_items:
    description: "Line items on invoices"
    columns:
      InvoiceLineId: "Unique identifier"
      InvoiceId: "Foreign key to invoices"
      TrackId: "Foreign key to tracks"
      UnitPrice: "Price at time of sale"
      Quantity: "Number of units"

reference_queries:
  - question: "How many albums does each artist have?"
    sql: "SELECT ar.Name, COUNT(al.AlbumId) as album_count FROM artists ar LEFT JOIN albums al ON ar.ArtistId = al.ArtistId GROUP BY ar.ArtistId, ar.Name ORDER BY album_count DESC"

  - question: "What are the top 10 longest songs?"
    sql: "SELECT Name, Milliseconds/1000.0 as seconds FROM tracks ORDER BY Milliseconds DESC LIMIT 10"

  - question: "Which genres have the most tracks?"
    sql: "SELECT g.Name as genre, COUNT(t.TrackId) as track_count FROM genres g JOIN tracks t ON g.GenreId = t.GenreId GROUP BY g.GenreId, g.Name ORDER BY track_count DESC"

  - question: "Who are the top 5 customers by total spending?"
    sql: "SELECT c.FirstName || ' ' || c.LastName as customer, SUM(i.Total) as total_spent FROM customers c JOIN invoices i ON c.CustomerId = i.CustomerId GROUP BY c.CustomerId ORDER BY total_spent DESC LIMIT 5"

  - question: "How many tracks are in each album?"
    sql: "SELECT al.Title, COUNT(t.TrackId) as track_count FROM albums al LEFT JOIN tracks t ON al.AlbumId = t.AlbumId GROUP BY al.AlbumId, al.Title ORDER BY track_count DESC"
'''


if __name__ == "__main__":
    print(create_sample_config())
