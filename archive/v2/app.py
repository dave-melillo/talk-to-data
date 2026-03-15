"""Talk To Data v2 - Natural Language to SQL"""

import streamlit as st
import os
import yaml
from pathlib import Path
import tempfile

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

from talk_to_data.introspector import introspect_schema, introspect_csv, schema_to_prompt
from talk_to_data.semantic import load_semantic_config, semantic_to_prompt
from talk_to_data.generator import generate_sql, validate_sql
from talk_to_data.executor import execute_query, csv_to_sqlite

# Page config
st.set_page_config(
    page_title="Talk To Data v2",
    page_icon="💬",
    layout="wide"
)

# Title
st.title("💬 Talk To Data v2")
st.markdown("*Ask questions about your data in plain English*")

# Sidebar - Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Data source selector
    data_source = st.radio(
        "Data Source",
        ["Sample Database", "CSV File", "Custom Database"]
    )
    
    connection_string = None
    schema = None
    semantic = {}
    
    # Sample Database
    if data_source == "Sample Database":
        sample_db = st.selectbox(
            "Choose Sample",
            ["Chinook (SQLite)", "None"]
        )
        
        if sample_db == "Chinook (SQLite)":
            db_path = Path(__file__).parent / "data" / "chinook.db"
            connection_string = f"sqlite:///{db_path}"
            config_path = Path(__file__).parent / "config" / "chinook.yaml"
            if config_path.exists():
                with open(config_path) as f:
                    semantic = yaml.safe_load(f)
            st.success(f"✅ Loaded Chinook database + config")
    
    # CSV File
    elif data_source == "CSV File":
        uploaded_csv = st.file_uploader("Upload CSV", type=["csv"])
        
        if uploaded_csv:
            # Save temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                tmp.write(uploaded_csv.read())
                csv_path = tmp.name
            
            # Introspect CSV
            try:
                schema = introspect_csv(csv_path)
                connection_string, st.session_state.csv_engine = csv_to_sqlite(csv_path)
                st.success(f"✅ Loaded CSV: {uploaded_csv.name}")
                
                # Display schema
                with st.expander("Detected Schema"):
                    for table_name, table_info in schema["tables"].items():
                        st.markdown(f"**Table:** {table_name}")
                        for col in table_info["columns"]:
                            st.markdown(f"- {col['name']}: {col['type']}")
            except Exception as e:
                st.error(f"Failed to load CSV: {e}")
    
    # Custom Database
    else:
        db_type = st.selectbox(
            "Database Type",
            ["PostgreSQL", "MySQL", "SQLite", "Custom"]
        )
        
        if db_type == "SQLite":
            db_file = st.text_input("SQLite file path", placeholder="data/mydb.db")
            if db_file:
                connection_string = f"sqlite:///{db_file}"
        elif db_type == "Custom":
            connection_string = st.text_input(
                "Connection String",
                placeholder="postgresql://user:pass@host/db"
            )
        else:
            host = st.text_input("Host", "localhost")
            port = st.text_input("Port", "5432" if db_type == "PostgreSQL" else "3306")
            database = st.text_input("Database")
            user = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if db_type == "PostgreSQL":
                connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            else:
                connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    
    # Semantic config (optional)
    st.divider()
    st.subheader("Semantic Layer (Optional)")
    
    if data_source != "Sample Database":  # Sample DB already loaded config
        config_option = st.radio(
            "Semantic Config",
            ["None", "Upload YAML"]
        )
        
        if config_option == "Upload YAML":
            uploaded_config = st.file_uploader("Upload semantic YAML", type=["yaml", "yml"])
            if uploaded_config:
                semantic = yaml.safe_load(uploaded_config.read())
                st.success("✅ Config loaded")
    
    # LLM Provider
    st.divider()
    st.subheader("LLM Provider")
    
    llm_provider = st.selectbox(
        "Choose Provider",
        ["Anthropic (Claude)", "OpenAI (ChatGPT)"]
    )
    
    provider_key = "anthropic" if "Anthropic" in llm_provider else "openai"
    
    if provider_key == "anthropic":
        api_key = st.text_input(
            "Anthropic API Key",
            value=os.environ.get("ANTHROPIC_API_KEY", ""),
            type="password"
        )
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
    else:
        api_key = st.text_input(
            "OpenAI API Key",
            value=os.environ.get("OPENAI_API_KEY", ""),
            type="password"
        )
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.header("🗣️ Ask a Question")
    
    # Question input
    question = st.text_area(
        "Your question:",
        placeholder="e.g., What are the top customers by revenue?",
        height=100
    )
    
    # Example questions (generic, not database-specific)
    with st.expander("💡 Example questions"):
        examples = [
            "Show me the first 10 rows",
            "What are the column names and types?",
            "How many total rows are there?",
            "What's the average value in the numeric columns?",
            "Group by category and show counts",
        ]
        for ex in examples:
            if st.button(ex, key=f"ex_{ex[:20]}"):
                question = ex
    
    # Generate button
    if st.button("🔍 Generate SQL", type="primary", disabled=not question):
        if not connection_string:
            st.error("Please configure data source")
        elif not api_key:
            st.error(f"Please provide {llm_provider} API key")
        else:
            with st.spinner("Analyzing schema..."):
                try:
                    # Introspect schema (if not already done for CSV)
                    if schema is None:
                        schema = introspect_schema(connection_string)
                    
                    schema_prompt = schema_to_prompt(schema, semantic)
                    semantic_prompt = semantic_to_prompt(semantic) if semantic else ""
                    
                    # Detect SQL dialect
                    if "sqlite" in connection_string.lower():
                        dialect = "sqlite"
                    elif "postgresql" in connection_string.lower():
                        dialect = "postgresql"
                    elif "mysql" in connection_string.lower():
                        dialect = "mysql"
                    else:
                        dialect = "sqlite"
                    
                    # Generate SQL
                    with st.spinner(f"Generating SQL with {llm_provider}..."):
                        result = generate_sql(
                            question,
                            schema_prompt,
                            semantic_prompt,
                            dialect=dialect,
                            provider=provider_key,
                            api_key=api_key
                        )
                    
                    # Store in session state
                    st.session_state.generated_sql = result["sql"]
                    st.session_state.explanation = result["explanation"]
                    st.session_state.confidence = result["confidence"]
                    st.session_state.connection_string = connection_string
                    st.session_state.schema = schema
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")

with col2:
    st.header("📝 Generated SQL")
    
    # SQL display/edit
    if "generated_sql" in st.session_state:
        sql = st.text_area(
            "SQL Query (editable):",
            value=st.session_state.generated_sql,
            height=150,
            key="sql_editor"
        )
        
        # Confidence indicator
        confidence = st.session_state.get("confidence", "medium")
        confidence_colors = {"high": "🟢", "medium": "🟡", "low": "🔴"}
        st.markdown(f"**Confidence:** {confidence_colors.get(confidence, '🟡')} {confidence.upper()}")
        
        # Explanation
        if st.session_state.get("explanation"):
            with st.expander("📖 Explanation"):
                st.write(st.session_state.explanation)
        
        # Validate
        validation = validate_sql(sql)
        if not validation["valid"]:
            st.warning(f"⚠️ {validation['error']}")
        
        # Execute button
        if st.button("▶️ Execute Query", type="secondary"):
            if validation["valid"]:
                with st.spinner("Executing..."):
                    result = execute_query(sql, st.session_state.connection_string)
                    
                    if result["success"]:
                        st.session_state.query_result = result
                    else:
                        st.error(f"Execution error: {result['error']}")
    else:
        st.info("💡 Enter a question and click 'Generate SQL' to see the query here")

# Results
st.divider()
st.header("📊 Results")

if "query_result" in st.session_state and st.session_state.query_result["success"]:
    result = st.session_state.query_result
    st.success(f"✅ {result['row_count']} rows returned")
    st.dataframe(result["data"], use_container_width=True)
    
    # Download button
    csv_data = result["data"].to_csv(index=False)
    st.download_button(
        label="⬇️ Download CSV",
        data=csv_data,
        file_name="query_results.csv",
        mime="text/csv"
    )
else:
    st.info("📊 Execute a query to see results here")

# Schema explorer
with st.expander("🗄️ Database Schema"):
    if connection_string and "schema" in st.session_state:
        schema = st.session_state.schema
        for table_name, table_info in schema["tables"].items():
            st.markdown(f"**{table_name}** ({table_info['row_count'] or '?'} rows)")
            cols = []
            for c in table_info["columns"]:
                pk_marker = " 🔑" if c["primary_key"] else ""
                cols.append(f"`{c['name']}` ({c['type']}){pk_marker}")
            st.markdown(", ".join(cols))
            st.markdown("")
    else:
        st.info("Configure data source to see schema")

# Footer
st.divider()
st.markdown("""
**Talk To Data v2** | Features:
- Multi-LLM: Anthropic Claude & OpenAI ChatGPT
- CSV file support
- Multiple sample databases
- YAML semantic layer
- Auto-generate configs with `generate_semantic.py`
""")
