"""Tools used by the SQLite database agent."""

import os
import sqlite3
import logging
import re

from google.adk.tools import ToolContext
from google.genai import Client

MAX_NUM_ROWS = 80

database_settings = None
sqlite_conn = None


def get_sqlite_conn():
    """Get a connection to the SQLite database."""
    global sqlite_conn
    if sqlite_conn is None:
        db_path = os.getenv("SQLITE_DB_PATH", "data_science/utils/data/data.db")
        sqlite_conn = sqlite3.connect(db_path)
    return sqlite_conn


def get_database_settings():
    """Get database settings."""
    global database_settings
    if database_settings is None:
        database_settings = update_database_settings()
    return database_settings


def update_database_settings():
    conn = get_sqlite_conn()
    ddl_schema = get_sqlite_schema(conn)
    return {"sqlite_db_path": os.getenv("SQLITE_DB_PATH", "data_science/utils/data/data.db"), "ddl_schema": ddl_schema}


def get_sqlite_schema(conn):
    cursor = conn.cursor()
    tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    ddl_statements = ""
    for table in tables:
        ddl_statements += f"CREATE TABLE {table} (\n"
        columns = cursor.execute(f"PRAGMA table_info({table});").fetchall()
        for col in columns:
            ddl_statements += f"  {col[1]} {col[2]},\n"
        ddl_statements = ddl_statements[:-2] + "\n);\n\n"
        rows = cursor.execute(f"SELECT * FROM {table} LIMIT 5").fetchall()
        if rows:
            ddl_statements += f"-- Example values for table {table}:\n"
            for row in rows:
                ddl_statements += f"INSERT INTO {table} VALUES {row};\n"
            ddl_statements += "\n"
    return ddl_statements


def initial_sqlite_nl2sql(question: str, tool_context: ToolContext) -> str:
    """Generate initial SQL from natural language question."""
    ddl_schema = tool_context.state["database_settings"]["ddl_schema"]
    prompt = f"You are a SQLite SQL expert. Given the schema:\n{ddl_schema}\nGenerate SQL to answer: {question}"
    client = Client()
    response = client.models.generate_content(model=os.getenv("BASELINE_NL2SQL_MODEL"), contents=prompt, config={"temperature": 0.1})
    sql = response.text
    if sql:
        sql = sql.replace("```sql", "").replace("```", "").strip()
    tool_context.state["sql_query"] = sql
    return sql


def run_sqlite_validation(sql_string: str, tool_context: ToolContext) -> str:
    """Execute the SQL and return results or errors."""

    def cleanup_sql(sql_string):
        sql_string = sql_string.replace('\n', ' ')
        if "limit" not in sql_string.lower():
            sql_string = sql_string + f" limit {MAX_NUM_ROWS}"
        return sql_string

    logging.info("Validating SQL: %s", sql_string)
    sql_string = cleanup_sql(sql_string)

    final_result = {"query_result": None, "error_message": None}

    if re.search(r"(?i)(update|delete|drop|insert|create|alter|truncate|merge)", sql_string):
        final_result["error_message"] = "Invalid SQL: Contains disallowed DML/DDL operations."
        return final_result

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(sql_string)
        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]
        results = [dict(zip(column_names, row)) for row in rows]
        final_result["query_result"] = results
        tool_context.state["query_result"] = results
    except Exception as e:  # pylint: disable=broad-exception-caught
        final_result["error_message"] = f"Invalid SQL: {e}"

    return final_result
