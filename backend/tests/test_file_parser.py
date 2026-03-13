"""Tests for file parsing service."""

import pytest

from app.services.file_parser import (
    FileParseError,
    detect_delimiter,
    detect_encoding,
    detect_file_type,
    infer_column_types,
    parse_file,
    preview_file,
)


class TestDetectFileType:
    """Tests for file type detection."""

    def test_csv(self):
        assert detect_file_type("data.csv") == "csv"
        assert detect_file_type("DATA.CSV") == "csv"

    def test_tsv(self):
        assert detect_file_type("data.tsv") == "tsv"

    def test_excel(self):
        assert detect_file_type("data.xlsx") == "excel"
        assert detect_file_type("data.xls") == "excel"

    def test_parquet(self):
        assert detect_file_type("data.parquet") == "parquet"
        assert detect_file_type("data.pq") == "parquet"

    def test_unsupported(self):
        with pytest.raises(FileParseError, match="Unsupported file type"):
            detect_file_type("data.json")


class TestDetectDelimiter:
    """Tests for delimiter detection."""

    def test_comma(self):
        content = b"a,b,c\n1,2,3\n4,5,6"
        assert detect_delimiter(content) == ","

    def test_tab(self):
        content = b"a\tb\tc\n1\t2\t3"
        assert detect_delimiter(content) == "\t"

    def test_pipe(self):
        content = b"a|b|c\n1|2|3"
        assert detect_delimiter(content) == "|"

    def test_semicolon(self):
        content = b"a;b;c\n1;2;3"
        assert detect_delimiter(content) == ";"


class TestDetectEncoding:
    """Tests for encoding detection."""

    def test_utf8(self):
        content = "Hello, World!".encode("utf-8")
        assert detect_encoding(content) == "utf-8"

    def test_utf8_bom(self):
        content = "\ufeffHello".encode("utf-8-sig")
        # Should detect utf-8 or utf-8-sig
        encoding = detect_encoding(content)
        assert encoding in ("utf-8", "utf-8-sig")


class TestParseFile:
    """Tests for file parsing."""

    def test_parse_csv(self):
        content = b"name,age,city\nAlice,30,NYC\nBob,25,LA"
        df, metadata = parse_file(content, "test.csv")

        assert len(df) == 2
        assert list(df.columns) == ["name", "age", "city"]
        assert metadata["file_type"] == "csv"
        assert metadata["column_count"] == 3

    def test_parse_csv_with_limit(self):
        content = b"name,age\nAlice,30\nBob,25\nCharlie,35"
        df, metadata = parse_file(content, "test.csv", nrows=1)

        assert len(df) == 1
        assert df.iloc[0]["name"] == "Alice"

    def test_parse_tsv(self):
        content = b"name\tage\nAlice\t30"
        df, metadata = parse_file(content, "test.tsv")

        assert len(df) == 1
        assert metadata["file_type"] == "tsv"


class TestPreviewFile:
    """Tests for file preview."""

    def test_preview(self):
        content = b"id,name,score\n1,Alice,95\n2,Bob,87\n3,Charlie,92"
        preview = preview_file(content, "test.csv", preview_rows=2)

        assert len(preview["data"]) == 2
        assert len(preview["columns"]) == 3
        assert preview["columns"][0]["name"] == "id"


class TestInferColumnTypes:
    """Tests for column type inference."""

    def test_integer_column(self):
        import pandas as pd

        df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
        columns = infer_column_types(df)

        id_col = next(c for c in columns if c["name"] == "id")
        assert id_col["data_type"] == "INTEGER"

    def test_float_column(self):
        import pandas as pd

        df = pd.DataFrame({"price": [1.5, 2.5, 3.5]})
        columns = infer_column_types(df)

        price_col = columns[0]
        assert price_col["data_type"] == "FLOAT"
        assert "min_value" in price_col
        assert "max_value" in price_col

    def test_varchar_column(self):
        import pandas as pd

        df = pd.DataFrame({"name": ["Alice", "Bob", "Charlie"]})
        columns = infer_column_types(df)

        name_col = columns[0]
        assert name_col["data_type"] == "VARCHAR(255)"

    def test_nullable_detection(self):
        import pandas as pd

        df = pd.DataFrame({"value": [1, None, 3]})
        columns = infer_column_types(df)

        assert columns[0]["nullable"] is True
        assert columns[0]["null_count"] == 1
