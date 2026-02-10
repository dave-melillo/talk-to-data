"""Talk To Data - Streamlit Demo App"""

import streamlit as st
import os
import yaml
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

from talk_to_data.introspector import introspect_schema, schema_to_prompt
from talk_to_data.semantic import load_semantic_config, semantic_to_prompt
from talk_to_data.generator import generate_sql, validate_sql
from talk_to_data.executor import execute_query

# Page config
st.set_page_config(
    page_title="Talk To Data",
    page_icon="💬",
    layout="wide"
)

# Title
st.title("💬 Talk To Data")
st.markdown("*Ask questions about your data in plain English*")

# Sidebar - Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Database connection
    db_type = st.selectbox(
        "Database Type",
        ["SQLite (Demo)", "PostgreSQL", "MySQL", "Custom"]
    )
    
    if db_type == "SQLite (Demo)":
        db_path = Path(__file__).parent / "data" / "chinook.db"
        connection_string = f"sqlite:///{db_path}"
        st.success(f"Using Chinook demo database")
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
    
    # Semantic config
    st.divider()
    config_file = st.selectbox(
        "Semantic Config",
        ["chinook.yaml", "None", "Upload..."]
    )
    
    semantic = {}
    if config_file == "chinook.yaml":
        config_path = Path(__file__).parent / "config" / "chinook.yaml"
        if config_path.exists():
            with open(config_path) as f:
                semantic = yaml.safe_load(f)
            st.success("Loaded chinook.yaml")
    elif config_file == "Upload...":
        uploaded = st.file_uploader("Upload YAML config", type=["yaml", "yml"])
        if uploaded:
            semantic = yaml.safe_load(uploaded.read())
            st.success("Config loaded")
    
    # API Key
    st.divider()
    api_key = st.text_input(
        "Anthropic API Key",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        type="password"
    )
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.header("🗣️ Ask a Question")
    
    # Question input
    question = st.text_area(
        "Your question:",
        placeholder="e.g., Which artists have the most albums?",
        height=100
    )
    
    # Example questions
    with st.expander("💡 Example questions"):
        examples = [
            "How many albums does each artist have?",
            "What are the top 10 longest songs?",
            "Which genres have the most tracks?",
            "Who are the top 5 customers by spending?",
            "What's the average track length by genre?",
            "How many customers are from each country?",
        ]
        for ex in examples:
            if st.button(ex, key=f"ex_{ex[:20]}"):
                question = ex
    
    # Generate button
    if st.button("🔍 Generate SQL", type="primary", disabled=not question):
        if not connection_string:
            st.error("Please configure database connection")
        elif not api_key:
            st.error("Please provide Anthropic API key")
        else:
            with st.spinner("Analyzing schema..."):
                try:
                    # Introspect schema
                    schema = introspect_schema(connection_string)
                    schema_prompt = schema_to_prompt(schema, semantic)
                    semantic_prompt = semantic_to_prompt(semantic) if semantic else ""
                    
                    # Generate SQL
                    with st.spinner("Generating SQL..."):
                        result = generate_sql(
                            question,
                            schema_prompt,
                            semantic_prompt,
                            dialect="sqlite" if "sqlite" in connection_string else "postgresql"
                        )
                    
                    # Store in session state
                    st.session_state.generated_sql = result["sql"]
                    st.session_state.explanation = result["explanation"]
                    st.session_state.confidence = result["confidence"]
                    st.session_state.connection_string = connection_string
                    
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
        st.markdown(f"**Confidence:** {confidence_colors.get(confidence, '🟡')} {confidence}")
        
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
        st.info("Enter a question and click 'Generate SQL' to see the query here")

# Results
st.divider()
st.header("📊 Results")

if "query_result" in st.session_state and st.session_state.query_result["success"]:
    result = st.session_state.query_result
    st.success(f"✅ {result['row_count']} rows returned")
    st.dataframe(result["data"], use_container_width=True)
else:
    st.info("Execute a query to see results here")

# Schema explorer
with st.expander("🗄️ Database Schema"):
    if connection_string:
        try:
            schema = introspect_schema(connection_string)
            for table_name, table_info in schema["tables"].items():
                st.markdown(f"**{table_name}**")
                cols = [f"`{c['name']}` ({c['type']})" for c in table_info["columns"]]
                st.markdown(", ".join(cols))
        except Exception as e:
            st.error(f"Could not load schema: {e}")
