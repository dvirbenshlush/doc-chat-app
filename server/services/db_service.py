import duckdb
import pandas as pd
import re
from pathlib import Path

TABLES_DIR = Path(__file__).parent.parent / "data" / "tables"
ALLOWED_TABLES = {"students", "courses", "enrollments"}
BLOCKED_KEYWORDS = {
    "DROP", "INSERT", "UPDATE", "DELETE", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "MERGE", "EXEC", "EXECUTE", "CALL",
    "PRAGMA", "ATTACH", "DETACH", "COPY", "EXPORT", "IMPORT",
    "LOAD", "INSTALL", "CHECKPOINT",
}

_conn: duckdb.DuckDBPyConnection | None = None


def load_tables():
    global _conn
    _conn = duckdb.connect(":memory:")
    loaded = []
    for csv_path in sorted(TABLES_DIR.glob("*.csv")):
        table_name = csv_path.stem
        _conn.execute(f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM read_csv_auto('{csv_path.as_posix()}', header=true)
        """)
        loaded.append(table_name)
    print(f"DuckDB loaded tables: {loaded}")


def get_schema() -> str:
    if not _conn:
        return ""
    parts = []
    for (table_name,) in _conn.execute("SHOW TABLES").fetchall():
        cols = _conn.execute(f"DESCRIBE {table_name}").fetchall()
        col_lines = "\n  ".join(f"{c[0]} ({c[1]})" for c in cols)
        sample_df = _conn.execute(f"SELECT * FROM {table_name} LIMIT 3").df()
        parts.append(
            f"Table: {table_name}\n  Columns:\n  {col_lines}\n  Sample:\n{sample_df.to_string(index=False)}"
        )
    parts.append(
        "Relationships:\n"
        "  enrollments.student_id → students.student_id\n"
        "  enrollments.course_id  → courses.course_id"
    )
    return "\n\n".join(parts)


def get_table_info() -> list[dict]:
    if not _conn:
        return []
    result = []
    for (table_name,) in _conn.execute("SHOW TABLES").fetchall():
        count = _conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        cols = [c[0] for c in _conn.execute(f"DESCRIBE {table_name}").fetchall()]
        result.append({"name": table_name, "row_count": count, "columns": cols})
    return result


def validate_sql(sql: str) -> tuple[bool, str]:
    cleaned = sql.strip().rstrip(";")

    if not re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
        return False, "Only SELECT queries are allowed."

    tokens = set(re.findall(r"\b([A-Z_]+)\b", cleaned.upper()))
    blocked = tokens & BLOCKED_KEYWORDS
    if blocked:
        return False, f"Blocked keyword(s): {', '.join(sorted(blocked))}"

    # Only allow queries against known tables
    referenced = set(
        t.lower()
        for t in re.findall(r"\b(?:FROM|JOIN)\s+(\w+)", cleaned, re.IGNORECASE)
    )
    unknown = referenced - ALLOWED_TABLES
    if unknown:
        return False, f"Unauthorized table(s): {', '.join(sorted(unknown))}"

    return True, ""


def add_limit(sql: str, max_rows: int = 50) -> str:
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        return sql.rstrip(";").rstrip() + f" LIMIT {max_rows}"
    return sql


def execute_query(sql: str) -> tuple[list[dict], str | None]:
    if not _conn:
        return [], "Database not initialized."
    try:
        df: pd.DataFrame = _conn.execute(sql).df()
        return df.to_dict("records"), None
    except Exception as e:
        return [], str(e)
