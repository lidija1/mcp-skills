import argparse
import os
import sqlite3
from pathlib import Path
from typing import Any


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
try:
    from dotenv import load_dotenv

    load_dotenv(_PROJECT_ROOT / ".env", override=False)
except Exception:
    pass

TABLES = [
    "users",
    "sessions",
    "executions",
    "saved_suites",
    "assertion_results",
    "chat_sessions",
    "chat_messages",
]


def _default_sqlite_path() -> Path:
    configured = os.environ.get("DASHBOARD_DB_PATH")
    backend_dir = Path(__file__).resolve().parent
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else backend_dir / path
    return backend_dir / "data" / "dashboard.db"


def _sqlite_rows(sqlite_path: Path, table: str) -> tuple[list[str], list[dict[str, Any]]]:
    with sqlite3.connect(sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if not columns:
            return [], []
        rows = [dict(row) for row in conn.execute(f"SELECT * FROM {table}").fetchall()]
    return columns, rows


def _copy_table(pg_conn, table: str, columns: list[str], rows: list[dict[str, Any]]) -> None:
    if not rows:
        print(f"{table}: 0 rows")
        return

    from psycopg import sql

    insert = sql.SQL("INSERT INTO {table} ({columns}) VALUES ({values}) ON CONFLICT (id) DO UPDATE SET {updates}").format(
        table=sql.Identifier(table),
        columns=sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        values=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        updates=sql.SQL(", ").join(
            sql.SQL("{column} = EXCLUDED.{column}").format(column=sql.Identifier(column))
            for column in columns
            if column != "id"
        ),
    )
    with pg_conn.cursor() as cur:
        for row in rows:
            cur.execute(insert, [row[column] for column in columns])
    print(f"{table}: {len(rows)} rows")


def _reset_sequence(pg_conn, table: str) -> None:
    serial_tables = {"users", "sessions", "saved_suites", "assertion_results", "chat_sessions", "chat_messages"}
    if table not in serial_tables:
        return
    with pg_conn.cursor() as cur:
        cur.execute("SELECT pg_get_serial_sequence(%s, 'id')", (table,))
        row = cur.fetchone()
        sequence = row[0] if row else None
        if sequence:
            cur.execute(f"SELECT setval(%s, COALESCE((SELECT MAX(id) FROM {table}), 1), true)", (sequence,))


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy dashboard data from SQLite to PostgreSQL.")
    parser.add_argument("--sqlite-path", default=str(_default_sqlite_path()))
    parser.add_argument("--postgres-url", default=os.environ.get("DASHBOARD_DATABASE_URL") or os.environ.get("DATABASE_URL"))
    args = parser.parse_args()

    if not args.postgres_url:
        raise SystemExit("Missing --postgres-url or DASHBOARD_DATABASE_URL.")

    sqlite_path = Path(args.sqlite_path)
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")

    os.environ["DASHBOARD_DATABASE_URL"] = args.postgres_url
    import dashboard_db

    dashboard_db.init_db()

    import psycopg

    with psycopg.connect(args.postgres_url) as pg_conn:
        for table in TABLES:
            columns, rows = _sqlite_rows(sqlite_path, table)
            if columns:
                _copy_table(pg_conn, table, columns, rows)
                _reset_sequence(pg_conn, table)

    print("Migration complete.")


if __name__ == "__main__":
    main()
