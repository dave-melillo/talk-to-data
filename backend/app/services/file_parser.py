"""File parsing service for CSV, TSV, Excel, and Parquet files."""

import io
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import get_settings

settings = get_settings()

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".txt": "csv",  # Assume CSV for .txt
    ".xlsx": "excel",
    ".xls": "excel",
    ".parquet": "parquet",
    ".pq": "parquet",
}


class FileParseError(Exception):
    """Exception raised when file parsing fails."""

    pass


def detect_file_type(filename: str) -> str:
    """Detect file type from extension."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise FileParseError(
            f"Unsupported file type: {ext}. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS.keys())}"
        )
    return SUPPORTED_EXTENSIONS[ext]


def detect_delimiter(content: bytes, sample_size: int = 8192) -> str:
    """Auto-detect CSV delimiter from content."""
    sample = content[:sample_size].decode("utf-8", errors="ignore")
    
    # Count occurrences of common delimiters
    delimiters = {",": 0, "\t": 0, "|": 0, ";": 0}
    for line in sample.split("\n")[:10]:
        for delim in delimiters:
            delimiters[delim] += line.count(delim)
    
    # Return most common delimiter (default to comma)
    if max(delimiters.values()) == 0:
        return ","
    return max(delimiters, key=delimiters.get)


def detect_encoding(content: bytes) -> str:
    """Detect file encoding."""
    # Try common encodings
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]
    
    for encoding in encodings:
        try:
            content.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    
    return "utf-8"  # Fallback


def parse_file(
    content: bytes,
    filename: str,
    nrows: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Parse file content into a DataFrame.
    
    Args:
        content: Raw file bytes
        filename: Original filename (for type detection)
        nrows: Optional limit on rows to read (for preview)
    
    Returns:
        Tuple of (DataFrame, metadata dict)
    """
    file_type = detect_file_type(filename)
    metadata: dict[str, Any] = {
        "original_filename": filename,
        "file_type": file_type,
        "file_size_bytes": len(content),
    }
    
    try:
        if file_type == "csv" or file_type == "tsv":
            encoding = detect_encoding(content)
            delimiter = "\t" if file_type == "tsv" else detect_delimiter(content)
            metadata["encoding"] = encoding
            metadata["delimiter"] = delimiter
            
            df = pd.read_csv(
                io.BytesIO(content),
                encoding=encoding,
                delimiter=delimiter,
                nrows=nrows,
                on_bad_lines="warn",
            )
        
        elif file_type == "excel":
            df = pd.read_excel(
                io.BytesIO(content),
                nrows=nrows,
            )
        
        elif file_type == "parquet":
            df = pd.read_parquet(io.BytesIO(content))
            if nrows:
                df = df.head(nrows)
        
        else:
            raise FileParseError(f"Unknown file type: {file_type}")
        
        # Add row count to metadata
        if nrows is None:
            metadata["row_count"] = len(df)
        
        metadata["column_count"] = len(df.columns)
        metadata["columns"] = df.columns.tolist()
        
        return df, metadata
    
    except Exception as e:
        raise FileParseError(f"Failed to parse file: {e!s}") from e


def preview_file(
    content: bytes,
    filename: str,
    preview_rows: int = 10,
) -> dict[str, Any]:
    """
    Generate a preview of file contents.
    
    Returns dict with columns, sample data, and metadata.
    """
    df, metadata = parse_file(content, filename, nrows=preview_rows)
    
    # Convert to preview format
    preview = {
        "metadata": metadata,
        "columns": [],
        "data": df.fillna("").astype(str).to_dict(orient="records"),
    }
    
    # Generate column info
    for col in df.columns:
        col_info = {
            "name": col,
            "inferred_type": str(df[col].dtype),
            "sample_values": df[col].dropna().astype(str).head(5).tolist(),
            "null_count": int(df[col].isna().sum()),
        }
        preview["columns"].append(col_info)
    
    return preview


def infer_column_types(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Infer column types and statistics from DataFrame.
    
    Returns list of column metadata dicts.
    """
    columns = []
    
    for col in df.columns:
        series = df[col]
        
        # Determine SQL-friendly type
        if pd.api.types.is_integer_dtype(series):
            sql_type = "INTEGER"
        elif pd.api.types.is_float_dtype(series):
            sql_type = "FLOAT"
        elif pd.api.types.is_bool_dtype(series):
            sql_type = "BOOLEAN"
        elif pd.api.types.is_datetime64_any_dtype(series):
            sql_type = "TIMESTAMP"
        else:
            # Check if it could be a date
            try:
                pd.to_datetime(series.dropna().head(100))
                sql_type = "TIMESTAMP"
            except (ValueError, TypeError):
                # Check max string length
                max_len = series.astype(str).str.len().max()
                if max_len and max_len > 255:
                    sql_type = "TEXT"
                else:
                    sql_type = "VARCHAR(255)"
        
        col_meta = {
            "name": col,
            "data_type": sql_type,
            "pandas_dtype": str(series.dtype),
            "nullable": bool(series.isna().any()),
            "distinct_count": int(series.nunique()),
            "null_count": int(series.isna().sum()),
            "sample_values": series.dropna().astype(str).head(5).tolist(),
        }
        
        # Add numeric stats
        if pd.api.types.is_numeric_dtype(series):
            col_meta["min_value"] = float(series.min()) if not pd.isna(series.min()) else None
            col_meta["max_value"] = float(series.max()) if not pd.isna(series.max()) else None
            col_meta["mean"] = float(series.mean()) if not pd.isna(series.mean()) else None
        
        # Check for potential primary key
        col_meta["is_primary_key"] = (
            col_meta["distinct_count"] == len(df)
            and col_meta["null_count"] == 0
            and ("id" in col.lower() or col.lower().endswith("_id"))
        )
        
        # Check for unique
        col_meta["is_unique"] = col_meta["distinct_count"] == len(df)
        
        columns.append(col_meta)
    
    return columns
