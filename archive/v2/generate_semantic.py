#!/usr/bin/env python3
"""Auto-generate semantic YAML configuration from database or CSV."""

import argparse
import sys
import yaml
from pathlib import Path

# Add talk_to_data to path
sys.path.insert(0, str(Path(__file__).parent))

from talk_to_data.introspector import introspect_schema, introspect_csv


def generate_semantic_yaml(schema: dict, database_name: str, description: str = "") -> str:
    """
    Auto-generate semantic YAML from schema.
    
    Args:
        schema: Output from introspect_schema() or introspect_csv()
        database_name: Name for the database
        description: Optional description
    
    Returns:
        YAML string
    """
    config = {
        "database": database_name,
        "description": description or f"Auto-generated config for {database_name}",
        "tables": {}
    }
    
    for table_name, table_info in schema["tables"].items():
        config["tables"][table_name] = {
            "description": f"Table: {table_name}",
            "columns": {}
        }
        
        for col in table_info["columns"]:
            col_name = col["name"]
            col_type = col["type"]
            
            # Basic description based on column name heuristics
            if col_name.lower().endswith("id"):
                desc = f"Unique identifier"
            elif col_name.lower() in ["name", "title"]:
                desc = f"{table_name.capitalize()} name"
            elif col_name.lower() in ["date", "created_at", "updated_at", "timestamp"]:
                desc = f"Timestamp"
            elif col_name.lower() in ["email"]:
                desc = f"Email address"
            elif col_name.lower() in ["price", "cost", "total", "amount"]:
                desc = f"Monetary value"
            else:
                desc = f"{col_name} ({col_type})"
            
            config["tables"][table_name]["columns"][col_name] = desc
    
    # Placeholder for user to add business_terms and reference_queries
    config["tables"]["_example_"] = {
        "description": "Remove this example. Add your own business terms below:",
        "business_terms": {
            "user_term": "database_column_name"
        }
    }
    
    config["reference_queries"] = [
        {
            "question": "Example question goes here",
            "sql": "SELECT * FROM table LIMIT 10"
        }
    ]
    
    return yaml.dump(config, default_flow_style=False, sort_keys=False)


def main():
    parser = argparse.ArgumentParser(
        description="Generate semantic YAML config from database or CSV"
    )
    parser.add_argument(
        "--database",
        help="Database connection string (e.g., postgresql://user:pass@host/db)"
    )
    parser.add_argument(
        "--csv",
        help="Path to CSV file"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Name for the database/dataset"
    )
    parser.add_argument(
        "--description",
        default="",
        help="Optional description"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output YAML file path"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.database and not args.csv:
        print("Error: Must provide either --database or --csv")
        sys.exit(1)
    
    if args.database and args.csv:
        print("Error: Provide only one of --database or --csv")
        sys.exit(1)
    
    # Introspect schema
    try:
        if args.database:
            print(f"Introspecting database: {args.database}")
            schema = introspect_schema(args.database)
        else:
            print(f"Introspecting CSV: {args.csv}")
            schema = introspect_csv(args.csv)
        
        print(f"✅ Found {len(schema['tables'])} table(s)")
        
        # Generate YAML
        yaml_content = generate_semantic_yaml(schema, args.name, args.description)
        
        # Write to file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(yaml_content)
        
        print(f"✅ Semantic YAML written to: {output_path}")
        print("\n🎯 Next steps:")
        print("1. Review the generated YAML and improve descriptions")
        print("2. Add business_terms to map user terminology")
        print("3. Add reference_queries for few-shot learning")
        print("4. Remove the _example_ table section")
        print(f"5. Test with: streamlit run app.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
