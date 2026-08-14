import re
import sqlite3
from pathlib import Path

# Deliberately a separate SQLite file from the app's own conversation/tool-call
# storage, so this tool can never read internal agent state, no matter what SQL is passed.
DEMO_DB_PATH = Path("data/demo.db")

_SEED_COMPANIES = [
    ("TSLA", "Tesla, Inc.", 3190000000, 248.50),
    ("AAPL", "Apple Inc.", 15334000000, 227.30),
    ("MSFT", "Microsoft Corporation", 7430000000, 421.10),
    ("AMZN", "Amazon.com, Inc.", 10500000000, 186.40),
]


class UnsafeQueryError(ValueError):
    pass


def _connect() -> sqlite3.Connection:
    DEMO_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DEMO_DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_seeded(conn)
    return conn


def _ensure_seeded(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            ticker TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            shares_outstanding INTEGER NOT NULL,
            stock_price_usd REAL NOT NULL
        )
        """
    )
    count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO companies (ticker, name, shares_outstanding, stock_price_usd) "
            "VALUES (?, ?, ?, ?)",
            _SEED_COMPANIES,
        )
        conn.commit()


def _assert_read_only(sql: str) -> None:
    stripped = sql.strip().rstrip(";").strip()
    if not re.match(r"(?is)^select\b", stripped):
        raise UnsafeQueryError("Only SELECT queries are allowed")
    if ";" in stripped:
        raise UnsafeQueryError("Multiple statements are not allowed")


def query_database(sql: str) -> list[dict]:
    _assert_read_only(sql)
    conn = _connect()
    try:
        rows = conn.execute(sql).fetchmany(50)
        return [dict(row) for row in rows]
    finally:
        conn.close()


SCHEMA = {
    "type": "function",
    "function": {
        "name": "query_database",
        "description": (
            "Run a read-only SELECT query against the demo 'companies' table "
            "(columns: ticker, name, shares_outstanding, stock_price_usd). "
            "Company names are stored as full legal names (e.g. 'Tesla, Inc.', "
            "'Apple Inc.'), so match with LIKE '%keyword%' rather than an exact name, "
            "or filter by ticker (e.g. TSLA, AAPL, MSFT, AMZN) when known. "
            "Only SELECT statements are allowed."
        ),
        "parameters": {
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
        },
    },
}


def execute(sql: str) -> dict:
    return {"sql": sql, "rows": query_database(sql)}
