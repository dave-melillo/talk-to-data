"""Tests for DATA SEMANTIC and BIZ SEMANTIC generation and context assembly."""

from unittest.mock import patch

import pytest

from app.services.biz_semantic import (
    BizSemantic,
    format_biz_semantic_for_context,
    get_default_biz_semantic,
    merge_biz_semantics,
    parse_biz_semantic_yaml,
    update_table_biz_semantic,
)
from app.services.context_assembler import (
    assemble_context,
    assemble_query_prompt,
    format_prompt,
    generate_example_queries,
)
from app.services.data_semantic import (
    generate_data_semantic,
    generate_schema_summary,
    update_table_semantic,
)


class TestDataSemanticGeneration:
    """Test DATA SEMANTIC layer generation."""

    def test_generate_without_llm(self, db, sample_customers_table):
        """Test data semantic generation with LLM disabled."""
        semantic = generate_data_semantic(db, sample_customers_table, use_llm=False)

        assert semantic["version"] == "1.0"
        assert semantic["table"]["name"] == "test_customers"
        assert semantic["table"]["original_name"] == "customers.csv"
        assert semantic["table"]["row_count"] == 3
        assert semantic["table"]["description"] == "Data table with 3 rows"

        # Check columns
        assert len(semantic["columns"]) == 3
        col_names = [c["name"] for c in semantic["columns"]]
        assert "name" in col_names
        assert "email" in col_names
        assert "total_orders" in col_names

        # Check email column detected as email format
        email_col = next(c for c in semantic["columns"] if c["name"] == "email")
        assert email_col["format"] == "email"

    def test_generate_includes_statistics(self, db, sample_customers_table):
        semantic = generate_data_semantic(db, sample_customers_table, use_llm=False)

        stats = semantic["statistics"]
        assert stats["row_count"] == 3
        assert stats["column_count"] == 3

    def test_generate_column_statistics(self, db, sample_customers_table):
        semantic = generate_data_semantic(db, sample_customers_table, use_llm=False)

        total_orders_col = next(
            c for c in semantic["columns"] if c["name"] == "total_orders"
        )
        assert total_orders_col["statistics"]["distinct_count"] == 3
        assert total_orders_col["statistics"]["min_value"] == 0
        assert total_orders_col["statistics"]["max_value"] == 5

    def test_generate_with_llm_mocked(self, db, sample_customers_table, mock_llm_descriptions):
        semantic = generate_data_semantic(db, sample_customers_table, use_llm=True)

        # LLM mock returns "Test table description"
        assert semantic["table"]["description"] == "Test table description"

    def test_update_table_semantic(self, db, sample_customers_table, mock_llm_descriptions):
        updated = update_table_semantic(db, sample_customers_table, use_llm=True)

        assert updated.data_semantic is not None
        assert updated.data_semantic["version"] == "1.0"
        assert updated.description is not None

    def test_generate_timestamp_present(self, db, sample_customers_table):
        semantic = generate_data_semantic(db, sample_customers_table, use_llm=False)
        assert "generated_at" in semantic

    def test_generate_primary_key_detection(self, db, sample_orders_table):
        semantic = generate_data_semantic(db, sample_orders_table, use_llm=False)

        pk_cols = semantic["statistics"]["primary_key_columns"]
        assert "order_id" in pk_cols


class TestSchemaSummary:
    """Test schema summary generation for LLM context."""

    def test_summary_single_table(self, db, sample_customers_table):
        summary = generate_schema_summary(db, [sample_customers_table])

        assert "test_customers" in summary
        assert "name" in summary
        assert "email" in summary
        assert "total_orders" in summary

    def test_summary_multiple_tables(
        self, db, sample_customers_table, sample_orders_table
    ):
        summary = generate_schema_summary(
            db, [sample_customers_table, sample_orders_table]
        )

        assert "test_customers" in summary
        assert "test_orders" in summary

    def test_summary_empty_tables(self, db):
        summary = generate_schema_summary(db, [])
        assert "Database Schema" in summary


class TestBizSemanticGeneration:
    """Test BIZ SEMANTIC layer operations."""

    def test_default_biz_semantic(self):
        default = get_default_biz_semantic()

        assert default.version == "1.0"
        assert "active_customer" in default.glossary
        assert "total_revenue" in default.kpis
        assert len(default.terminology) > 0
        assert len(default.caveats) > 0

    def test_parse_yaml(self):
        yaml_content = """
version: "1.0"
business_name: "Acme Corp"
glossary:
  vip: "Customer with > 10 orders"
kpis:
  churn_rate: "COUNT(inactive) / COUNT(*)"
caveats:
  - "Data refreshes nightly"
"""
        semantic = parse_biz_semantic_yaml(yaml_content)

        assert semantic.business_name == "Acme Corp"
        assert semantic.glossary["vip"] == "Customer with > 10 orders"
        assert "churn_rate" in semantic.kpis
        assert "Data refreshes nightly" in semantic.caveats

    def test_parse_invalid_yaml_raises(self):
        with pytest.raises(ValueError, match="Invalid YAML"):
            parse_biz_semantic_yaml("{{invalid: yaml: [")

    def test_update_table_biz_semantic(self, db, sample_customers_table):
        biz = BizSemantic(
            business_name="Test Corp",
            glossary={"vip": "Top customer"},
        )
        updated = update_table_biz_semantic(db, sample_customers_table, biz)

        assert updated.biz_semantic is not None
        assert updated.biz_semantic["business_name"] == "Test Corp"
        assert updated.biz_semantic["updated_at"] is not None

    def test_update_with_dict(self, db, sample_customers_table):
        biz_dict = {
            "business_name": "Dict Corp",
            "glossary": {"key_metric": "Important value"},
        }
        updated = update_table_biz_semantic(db, sample_customers_table, biz_dict)

        assert updated.biz_semantic["business_name"] == "Dict Corp"

    def test_merge_glossaries(self):
        base = {"glossary": {"a": "1", "b": "2"}, "caveats": ["warn1"]}
        updates = {"glossary": {"b": "updated", "c": "3"}, "caveats": ["warn2"]}
        merged = merge_biz_semantics(base, updates)

        assert merged["glossary"] == {"a": "1", "b": "updated", "c": "3"}
        assert "warn1" in merged["caveats"]
        assert "warn2" in merged["caveats"]

    def test_merge_deduplicates_lists(self):
        base = {"caveats": ["warn1", "warn2"]}
        updates = {"caveats": ["warn2", "warn3"]}
        merged = merge_biz_semantics(base, updates)

        assert merged["caveats"] == ["warn1", "warn2", "warn3"]

    def test_format_for_context(self):
        semantic = {
            "business_name": "Acme",
            "description": "E-commerce platform",
            "glossary": {"churn": "Customer who left"},
            "kpis": {"revenue": "SUM(amount)"},
            "terminology": [{"use": "customer", "instead_of": "user"}],
            "caveats": ["Legacy data before 2024"],
        }
        formatted = format_biz_semantic_for_context(semantic)

        assert "Acme" in formatted
        assert "churn" in formatted
        assert "SUM(amount)" in formatted
        assert "customer" in formatted
        assert "Legacy data" in formatted

    def test_format_empty_semantic(self):
        formatted = format_biz_semantic_for_context({})
        assert "Business Context" in formatted


class TestContextAssembly:
    """Test context assembly with both semantic layers."""

    def test_assemble_context_with_tables(self, db, sample_customers_table):
        context = assemble_context(db, "How many customers?")

        assert "schema" in context
        assert "business_context" in context
        assert "examples" in context
        assert "question" in context
        assert context["question"] == "How many customers?"
        assert "test_customers" in context["schema"]

    def test_assemble_context_with_biz_semantic(self, db, sample_customers_table):
        # Add biz semantic to the table
        sample_customers_table.biz_semantic = {
            "business_name": "Test Corp",
            "glossary": {"active": "Has orders"},
        }
        db.commit()

        context = assemble_context(db, "How many active customers?")
        assert "Test Corp" in context["business_context"]

    def test_assemble_includes_examples(self, db, sample_customers_table):
        context = assemble_context(db, "test", include_examples=True)
        assert len(context["examples"]) > 0
        assert "Example" in context["examples"]

    def test_assemble_excludes_examples(self, db, sample_customers_table):
        context = assemble_context(db, "test", include_examples=False)
        assert context["examples"] == ""

    def test_format_prompt_structure(self):
        context = {
            "schema": "## Schema\ntest_table",
            "business_context": "## Business\ntest context",
            "examples": "## Examples\nSELECT 1",
            "question": "How many?",
        }
        prompt = format_prompt(context)

        assert "test_table" in prompt
        assert "test context" in prompt
        assert "How many?" in prompt
        assert "PostgreSQL" in prompt
        assert "SELECT" in prompt

    def test_assemble_query_prompt_end_to_end(self, db, sample_customers_table):
        prompt = assemble_query_prompt(db, "Count all customers")

        assert "test_customers" in prompt
        assert "Count all customers" in prompt
        assert "PostgreSQL" in prompt

    def test_generate_example_queries(self):
        examples = generate_example_queries()

        assert "COUNT" in examples
        assert "JOIN" in examples
        assert "GROUP BY" in examples

    def test_assemble_both_layers(self, db, sample_customers_table, mock_llm_descriptions):
        """Test context assembly with both DATA and BIZ SEMANTIC."""
        # Generate data semantic
        update_table_semantic(db, sample_customers_table, use_llm=True)

        # Add biz semantic
        sample_customers_table.biz_semantic = {
            "business_name": "Both Layers Corp",
            "glossary": {"vip": "Top spender"},
        }
        db.commit()

        context = assemble_context(db, "Who are the VIP customers?")

        assert "test_customers" in context["schema"]
        assert "Both Layers Corp" in context["business_context"]
