"""Query executor - run SQL against the database and return results."""

import pandas as pd
from sqlalchemy import create_engine, text
from typing import Dict, Any, Optional, List


def execute_query(
    sql: str,
    connection_string: str,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Execute SQL query and return results as DataFrame.
    
    Args:
        sql: SQL query to execute
        connection_string: SQLAlchemy connection string
        limit: Max rows to return (safety limit)
    
    Returns:
        Dict with 'success', 'data' (DataFrame), 'columns', 'row_count', 'error'
    """
    try:
        engine = create_engine(connection_string)
        
        # Add LIMIT if not present and it's a SELECT query
        sql_upper = sql.upper().strip()
        if sql_upper.startswith("SELECT") and "LIMIT" not in sql_upper:
            sql = f"{sql.rstrip(';')} LIMIT {limit}"
        
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())
            
            df = pd.DataFrame(rows, columns=columns)
            
            return {
                "success": True,
                "data": df,
                "columns": columns,
                "row_count": len(df),
                "error": None
            }
    
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "columns": [],
            "row_count": 0,
            "error": str(e)
        }


def get_sample_data(
    table_name: str,
    connection_string: str,
    limit: int = 5
) -> pd.DataFrame:
    """
    Get sample rows from a table for preview.
    
    Args:
        table_name: Name of table
        connection_string: SQLAlchemy connection string
        limit: Number of rows
    
    Returns:
        DataFrame with sample data
    """
    result = execute_query(
        f"SELECT * FROM {table_name} LIMIT {limit}",
        connection_string
    )
    return result.get("data", pd.DataFrame())


if __name__ == "__main__":
    # Test
    result = execute_query(
        "SELECT * FROM artists LIMIT 5",
        "sqlite:///data/chinook.db"
    )
    print(result)
