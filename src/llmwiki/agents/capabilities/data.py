import os
from typing import Any
from pydantic_ai import RunContext
from llmwiki.utils.paths import safe_join, sanitize_filename

def query_data_file(ctx: RunContext[Any], filename: str, sql_query: str) -> str:
    """
    Executes a SQL query against a large structured file (CSV, Parquet, JSON) in vault/raw/.
    The table name in the query should be the filename enclosed in quotes (e.g., SELECT * FROM 'data.csv').
    Use this for files that are too large to read as raw text.
    """
    # Sanitize and resolve path
    safe_name = sanitize_filename(filename)
    file_path = safe_join(ctx.deps.vt.raw_path, safe_name)
    
    try:
        try:
            import duckdb  # Optional dependency for analytical queries.
        except ModuleNotFoundError:
            return "Error: DuckDB is not installed. Install `duckdb` to enable `query_data_file`."

        # Check if file exists
        if not os.path.exists(file_path):
            return f"Error: File {safe_name} not found in vault/raw/."

        # Using a transient in-memory DuckDB instance
        con = duckdb.connect(database=':memory:')
        
        # Security: Only allow SELECT statements
        if not sql_query.strip().upper().startswith("SELECT"):
            return "Error: Only SELECT queries are permitted."
            
        # Execute query and load into Pandas for formatting
        # DuckDB can query files directly by path
        # We replace the filename in the SQL query with the actual absolute path
        # to ensure DuckDB finds it.
        actual_sql = sql_query.replace(f"'{filename}'", f"'{file_path}'")
        actual_sql = actual_sql.replace(f'"{filename}"', f"'{file_path}'")
        
        df = con.execute(actual_sql).df()
        
        # Limit result size to avoid token overflow
        if len(df) > 50:
            summary = f"Note: Result truncated from {len(df)} rows to top 50.\n\n"
            df = df.head(50)
        else:
            summary = ""

        # Convert to Markdown table for the LLM
        return summary + df.to_markdown(index=False)
    except Exception as e:
        return f"Query Error: {e}"
