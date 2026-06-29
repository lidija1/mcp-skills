import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Iterable
import re


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_DIR = Path(__file__).resolve().parent
_DEFAULT_DB = _BACKEND_DIR / "data" / "dashboard.db"
try:
    from dotenv import load_dotenv

    load_dotenv(_PROJECT_ROOT / ".env", override=False)
except Exception:
    pass
_DATABASE_URL = os.environ.get("DASHBOARD_DATABASE_URL") or os.environ.get("DATABASE_URL") or ""
_USE_POSTGRES = _DATABASE_URL.startswith(("postgres://", "postgresql://"))


def _resolve_db_path() -> Path:
    configured = os.environ.get("DASHBOARD_DB_PATH")
    if configured:
        path = Path(configured)
        if path.is_absolute():
            return path
        if path.parts[:2] == ("dashboard", "backend"):
            return _PROJECT_ROOT / path
        return _BACKEND_DIR / path
    return _DEFAULT_DB


DB_PATH = _resolve_db_path()
if _USE_POSTGRES:
    print("ACTIVE DB: PostgreSQL")
else:
    print("DB PATH:", DB_PATH.resolve())
    print("ACTIVE DB:", DB_PATH.resolve())
_current_user: ContextVar[dict[str, Any] | None] = ContextVar("dashboard_current_user", default=None)


def active_db_label() -> str:
    return "PostgreSQL" if _USE_POSTGRES else str(DB_PATH)


def _translate_sql(query: str) -> str:
    sql = query.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    sql = re.sub(r"\bREAL\b", "DOUBLE PRECISION", sql)
    sql = sql.replace("INSERT OR REPLACE INTO executions", "INSERT INTO executions")
    if "INSERT INTO executions" in sql and "ON CONFLICT" not in sql:
        sql = sql.rstrip()
        sql += """
            ON CONFLICT (id) DO UPDATE SET
                execution_type = EXCLUDED.execution_type,
                execution_name = EXCLUDED.execution_name,
                status = EXCLUDED.status,
                created_by = EXCLUDED.created_by,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at,
                logs_json = EXCLUDED.logs_json,
                metadata_json = EXCLUDED.metadata_json
        """

    if (
        sql.lstrip().upper().startswith("INSERT INTO")
        and "RETURNING" not in sql.upper()
        and any(table in sql for table in ("chat_sessions", "chat_messages", "saved_suites", "assertion_results"))
    ):
        sql = sql.rstrip() + " RETURNING id"

    return sql.replace("?", "%s")


class _PostgresCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is not None and "id" in row:
            self.lastrowid = row["id"]
        return row

    def fetchall(self):
        return self._cursor.fetchall()


class _PostgresConnection:
    def __init__(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL support requires psycopg. Install backend requirements first: "
                "pip install -r dashboard/backend/requirements.txt"
            ) from exc
        self._conn = psycopg.connect(_DATABASE_URL, row_factory=dict_row)

    def __enter__(self):
        self._conn.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._conn.__exit__(exc_type, exc, tb)

    def execute(self, query: str, params: Iterable[Any] | None = None):
        cursor = self._conn.execute(_translate_sql(query), params or ())
        wrapped = _PostgresCursor(cursor)
        is_insert = query.lstrip().upper().startswith("INSERT")
        column_name = getattr(cursor.description[0], "name", None) if cursor.description else None
        if is_insert and cursor.description and len(cursor.description) == 1 and column_name == "id":
            row = wrapped.fetchone()
            if row is not None:
                wrapped._cursor = _SingleRowCursor(row)
        return wrapped


class _SingleRowCursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        row = self._row
        self._row = None
        return row

    def fetchall(self):
        row = self.fetchone()
        return [] if row is None else [row]


def connect() -> sqlite3.Connection | _PostgresConnection:
    if _USE_POSTGRES:
        return _PostgresConnection()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    journal_mode = os.environ.get("DASHBOARD_SQLITE_JOURNAL_MODE") or ("OFF" if os.name == "nt" else "WAL")
    try:
        conn.execute(f"PRAGMA journal_mode={journal_mode}")
    except sqlite3.OperationalError:
        conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                first_name TEXT NOT NULL DEFAULT '',
                last_name TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'user',
                created_at REAL NOT NULL
            )
            """
        )
        _ensure_column(conn, "users", "password_hash", "TEXT")
        _ensure_column(conn, "users", "first_name", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "users", "last_name", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "users", "role", "TEXT NOT NULL DEFAULT 'user'")
        _ensure_column(conn, "users", "created_at", "REAL NOT NULL DEFAULT 0")
        _migrate_legacy_password_column(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                revoked_at REAL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                execution_type TEXT NOT NULL,
                execution_name TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                error TEXT,
                created_by INTEGER,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                finished_at REAL,
                logs_json TEXT NOT NULL DEFAULT '[]',
                current_status_json TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_executions_created_by ON executions(created_by)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_executions_created_at ON executions(created_at)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_suites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                prompts_json TEXT NOT NULL DEFAULT '[]',
                builder_json TEXT NOT NULL DEFAULT '{}',
                shared_persona INTEGER NOT NULL DEFAULT 1,
                created_by INTEGER,
                created_at REAL NOT NULL,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_saved_suites_created_by ON saved_suites(created_by)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assertion_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                persona_description TEXT NOT NULL,
                assertion_type TEXT NOT NULL,
                expected_value REAL NOT NULL,
                actual_value REAL,
                operator TEXT NOT NULL,
                tolerance_pct REAL NOT NULL DEFAULT 5.0,
                passed INTEGER NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                lob TEXT NOT NULL DEFAULT 'auto',
                coverage_premiums_json TEXT NOT NULL DEFAULT '{}',
                uw_conditions_json TEXT NOT NULL DEFAULT '[]',
                persona_json TEXT NOT NULL DEFAULT '{}',
                flow_result_json TEXT NOT NULL DEFAULT '{}',
                blocked INTEGER NOT NULL DEFAULT 0,
                blocked_reason TEXT NOT NULL DEFAULT '',
                run_id TEXT,
                created_by INTEGER,
                created_at REAL NOT NULL,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
            """
        )
        _ensure_column(conn, "assertion_results", "flow_result_json", "TEXT NOT NULL DEFAULT '{}'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assertion_results_created_at ON assertion_results(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assertion_results_created_by ON assertion_results(created_by)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages(chat_session_id, created_at)")
        _ensure_postgres_numeric_precision(conn)


def _chat_title_from_message(message: str, max_chars: int = 56) -> str:
    text = re.sub(r"\s+", " ", (message or "").strip())
    text = re.sub(r"^[/#>\-\s]+", "", text).strip()
    if not text:
        return "New chat"
    if len(text) <= max_chars:
        return text
    shortened = text[:max_chars].rsplit(" ", 1)[0].strip()
    return (shortened or text[:max_chars]).rstrip(".,;:") + "..."


def create_chat_session(user_id: int, title: str | None = None, first_message: str = "") -> dict[str, Any]:
    init_db()
    now = time.time()
    clean_title = (title or "").strip() or _chat_title_from_message(first_message)
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO chat_sessions (user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, clean_title, now, now),
        )
        row = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row_to_chat_session(row)


def list_chat_sessions(user_id: int, limit: int = 100) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT chat_sessions.*, COUNT(chat_messages.id) AS message_count
            FROM chat_sessions
            LEFT JOIN chat_messages ON chat_messages.chat_session_id = chat_sessions.id
            WHERE chat_sessions.user_id = ?
            GROUP BY chat_sessions.id
            HAVING COUNT(chat_messages.id) > 0
            ORDER BY chat_sessions.updated_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [_row_to_chat_session(row) for row in rows]


def get_chat_session(session_id: int, user_id: int) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        session_row = conn.execute(
            "SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if not session_row:
            return None
        message_rows = conn.execute(
            """
            SELECT * FROM chat_messages
            WHERE chat_session_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (session_id,),
        ).fetchall()
    session = _row_to_chat_session(session_row)
    session["messages"] = [_row_to_chat_message(row) for row in message_rows]
    return session


def delete_chat_session(session_id: int, user_id: int) -> bool:
    init_db()
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if not row:
            return False
        conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    return True


def add_chat_message(session_id: int, user_id: int, role: str, content: str) -> dict[str, Any] | None:
    init_db()
    role = (role or "").strip().lower()
    content = (content or "").strip()
    if role not in {"user", "assistant"} or not content:
        return None

    now = time.time()
    with connect() as conn:
        session = conn.execute(
            "SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if not session:
            return None
        if role == "user" and (session["title"] or "").strip().lower() == "new chat":
            conn.execute(
                "UPDATE chat_sessions SET title = ? WHERE id = ?",
                (_chat_title_from_message(content), session_id),
            )
        cur = conn.execute(
            """
            INSERT INTO chat_messages (chat_session_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, role, content, now),
        )
        conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        row = conn.execute("SELECT * FROM chat_messages WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row_to_chat_message(row)


def ensure_chat_session(user_id: int, session_id: int | None = None, first_message: str = "") -> dict[str, Any] | None:
    if session_id:
        existing = get_chat_session(session_id, user_id)
        if existing:
            return {k: v for k, v in existing.items() if k != "messages"}
        return None
    return create_chat_session(user_id=user_id, first_message=first_message)


def _row_to_chat_session(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if not row:
        return None
    data = dict(row)
    return {
        "id": data["id"],
        "user_id": data["user_id"],
        "title": data["title"],
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
        "message_count": data.get("message_count", 0),
    }


def _row_to_chat_message(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if not row:
        return None
    data = dict(row)
    return {
        "id": data["id"],
        "chat_session_id": data["chat_session_id"],
        "role": data["role"],
        "content": data["content"],
        "created_at": data["created_at"],
    }


def save_suite(
    name: str,
    prompts: list[str],
    builder: dict[str, Any],
    shared_persona: bool = True,
    user_id: int | None = None,
) -> dict[str, Any]:
    init_db()
    now = time.time()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO saved_suites (name, prompts_json, builder_json, shared_persona, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, _json(prompts), _json(builder), int(shared_persona), user_id, now),
        )
        row = conn.execute("SELECT * FROM saved_suites WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row_to_suite(row)


def list_suites(user_id: int | None = None) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        if user_id is not None:
            rows = conn.execute(
                "SELECT * FROM saved_suites WHERE created_by = ? OR created_by IS NULL ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM saved_suites ORDER BY created_at DESC").fetchall()
    return [_row_to_suite(r) for r in rows]


def delete_suite(suite_id: int, user_id: int | None = None) -> bool:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT created_by FROM saved_suites WHERE id = ?", (suite_id,)).fetchone()
        if not row:
            return False
        owner = row["created_by"]
        if user_id is not None and owner is not None and owner != user_id:
            return False
        conn.execute("DELETE FROM saved_suites WHERE id = ?", (suite_id,))
    return True


def _row_to_suite(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if not row:
        return None
    data = dict(row)
    return {
        "id": data["id"],
        "name": data["name"],
        "prompts": _loads(data["prompts_json"], []),
        "builder": _loads(data["builder_json"], {}),
        "shared_persona": bool(data["shared_persona"]),
        "created_by": data.get("created_by"),
        "created_at": data["created_at"],
    }


def save_assertion_result(
    persona_description: str,
    assertion_type: str,
    expected_value: float,
    actual_value: float | None,
    operator: str,
    tolerance_pct: float,
    passed: bool,
    message: str = "",
    lob: str = "auto",
    coverage_premiums: dict[str, Any] | None = None,
    uw_conditions: list[str] | None = None,
    persona: dict[str, Any] | None = None,
    flow_result: dict[str, Any] | None = None,
    blocked: bool = False,
    blocked_reason: str = "",
    run_id: str | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    init_db()
    now = time.time()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO assertion_results (
                persona_description, assertion_type, expected_value, actual_value,
                operator, tolerance_pct, passed, message, lob,
                coverage_premiums_json, uw_conditions_json, persona_json, flow_result_json,
                blocked, blocked_reason, run_id, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                persona_description, assertion_type, expected_value, actual_value,
                operator, tolerance_pct, int(passed), message, lob,
                _json(coverage_premiums or {}), _json(uw_conditions or []), _json(persona or {}),
                _json(flow_result or {}),
                int(blocked), blocked_reason or "", run_id,
                user_id, now,
            ),
        )
        row = conn.execute("SELECT * FROM assertion_results WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row_to_assertion_result(row)


def list_assertion_results(user_id: int | None = None, limit: int = 200) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        if user_id is not None:
            rows = conn.execute(
                "SELECT * FROM assertion_results WHERE created_by = ? OR created_by IS NULL ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM assertion_results ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [_row_to_assertion_result(r) for r in rows]


def delete_assertion_result(result_id: int, user_id: int | None = None) -> bool:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT created_by FROM assertion_results WHERE id = ?", (result_id,)).fetchone()
        if not row:
            return False
        owner = row["created_by"]
        if user_id is not None and owner is not None and owner != user_id:
            return False
        conn.execute("DELETE FROM assertion_results WHERE id = ?", (result_id,))
    return True


def _row_to_assertion_result(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if not row:
        return None
    data = dict(row)
    return {
        "_type": "assert_flow",
        "id": data["id"],
        "persona_description": data["persona_description"],
        "assertion_type": data["assertion_type"],
        "expected_value": data["expected_value"],
        "actual_value": data["actual_value"],
        "operator": data["operator"],
        "tolerance_pct": data["tolerance_pct"],
        "passed": bool(data["passed"]),
        "message": data["message"] or "",
        "lob": data["lob"],
        "coverage_premiums": _loads(data["coverage_premiums_json"], {}),
        "uw_conditions": _loads(data["uw_conditions_json"], []),
        "persona": _loads(data["persona_json"], {}),
        "flow_result": _loads(data.get("flow_result_json"), {}),
        "blocked": bool(data["blocked"]),
        "blocked_reason": data["blocked_reason"] or "",
        "run_id": data.get("run_id"),
        "created_by": data.get("created_by"),
        "created_at": data["created_at"],
    }


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if _USE_POSTGRES:
        definition = re.sub(r"\bREAL\b", "DOUBLE PRECISION", definition)
    if _USE_POSTGRES:
        rows = conn.execute(
            """
            SELECT column_name AS name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (table,),
        ).fetchall()
    else:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    columns = {row["name"] for row in rows}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _ensure_postgres_numeric_precision(conn: sqlite3.Connection) -> None:
    if not _USE_POSTGRES:
        return

    columns = {
        "users": ["created_at"],
        "sessions": ["created_at", "expires_at", "revoked_at"],
        "executions": ["created_at", "updated_at", "finished_at"],
        "saved_suites": ["created_at"],
        "assertion_results": ["expected_value", "actual_value", "tolerance_pct", "created_at"],
        "chat_sessions": ["created_at", "updated_at"],
        "chat_messages": ["created_at"],
    }
    for table, table_columns in columns.items():
        for column in table_columns:
            conn.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE DOUBLE PRECISION")


def _migrate_legacy_password_column(conn: sqlite3.Connection) -> None:
    if _USE_POSTGRES:
        rows = conn.execute(
            """
            SELECT column_name AS name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """,
            ("users",),
        ).fetchall()
    else:
        rows = conn.execute("PRAGMA table_info(users)").fetchall()
    columns = {row["name"] for row in rows}
    if "password" in columns and "password_hash" in columns:
        conn.execute(
            "UPDATE users SET password_hash = password WHERE (password_hash IS NULL OR password_hash = '') AND password IS NOT NULL"
        )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 260_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt_b64, digest_b64 = stored_hash.split("$", 3)
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(digest_b64)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False
    if stored_hash.startswith("$2"):
        try:
            from passlib.context import CryptContext

            return CryptContext(schemes=["bcrypt"], deprecated="auto").verify(password, stored_hash)
        except Exception:
            return False
    return False


def serialize_user(row: sqlite3.Row | dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    data = dict(row)
    return {
        "id": data["id"],
        "username": data["username"],
        "first_name": data.get("first_name") or "",
        "last_name": data.get("last_name") or "",
        "role": data.get("role") or "user",
        "display_name": _display_name(data),
    }


def _display_name(user: dict[str, Any]) -> str:
    name = f"{user.get('first_name') or ''} {user.get('last_name') or ''}".strip()
    return name or user.get("username") or "User"


def create_user(username: str, password: str, first_name: str = "", last_name: str = "", role: str = "user") -> dict[str, Any]:
    init_db()
    username = username.strip()
    if not username or not password:
        raise ValueError("Username and password are required.")
    role = role if role in {"admin", "user"} else "user"
    now = time.time()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO users (username, password_hash, first_name, last_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, hash_password(password), first_name.strip(), last_name.strip(), role, now),
        )
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return serialize_user(row)


def user_count() -> int:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()
    return int(row["total"] or 0)


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return serialize_user(row)


def create_session(user_id: int, ttl_seconds: int = 60 * 60 * 12) -> str:
    init_db()
    token = secrets.token_urlsafe(32)
    now = time.time()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (token_hash, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (_token_hash(token), user_id, now, now + ttl_seconds),
        )
    return token


def user_for_token(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    init_db()
    now = time.time()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT users.* FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ?
              AND sessions.revoked_at IS NULL
              AND sessions.expires_at > ?
            """,
            (_token_hash(token), now),
        ).fetchone()
    return serialize_user(row)


def revoke_session(token: str | None) -> None:
    if not token:
        return
    init_db()
    with connect() as conn:
        conn.execute(
            "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
            (time.time(), _token_hash(token)),
        )


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def set_current_user(user: dict[str, Any] | None):
    return _current_user.set(user)


def reset_current_user(token) -> None:
    _current_user.reset(token)


def get_current_user() -> dict[str, Any] | None:
    return _current_user.get()


def create_execution(
    execution_id: str,
    execution_name: str,
    execution_type: str = "job",
    created_by: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    init_db()
    user = get_current_user()
    owner_id = created_by if created_by is not None else (user or {}).get("id")
    now = time.time()
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO executions (
                id, execution_type, execution_name, status, created_by, created_at,
                updated_at, logs_json, metadata_json
            )
            VALUES (?, ?, ?, 'running', ?, ?, ?, '[]', ?)
            """,
            (execution_id, execution_type, execution_name, owner_id, now, now, _json(metadata or {})),
        )


def update_execution_status(execution_id: str, phase: str, detail: str = "") -> None:
    current = {
        "phase": phase,
        "detail": detail,
        "updated": time.time(),
    }
    with connect() as conn:
        row = conn.execute("SELECT created_at FROM executions WHERE id = ?", (execution_id,)).fetchone()
        if row:
            current["elapsed_s"] = round(max(0, current["updated"] - float(row["created_at"] or current["updated"])), 1)
        conn.execute(
            "UPDATE executions SET current_status_json = ?, updated_at = ? WHERE id = ? AND status = 'running'",
            (_json(current), current["updated"], execution_id),
        )


def append_execution_log(execution_id: str, message: str) -> None:
    now = time.time()
    with connect() as conn:
        row = conn.execute("SELECT logs_json FROM executions WHERE id = ?", (execution_id,)).fetchone()
        if not row:
            return
        logs = _loads(row["logs_json"], [])
        logs.append({"ts": round(now, 3), "msg": message})
        conn.execute(
            "UPDATE executions SET logs_json = ?, updated_at = ? WHERE id = ?",
            (_json(logs), now, execution_id),
        )


def finish_execution(execution_id: str, status: str, result: str | None = None, error: str | None = None) -> None:
    now = time.time()
    terminal_guard = "" if status in {"canceled", "cancelled"} else "AND status NOT IN ('canceled', 'cancelled')"
    with connect() as conn:
        conn.execute(
            f"""
            UPDATE executions
            SET status = ?, result = ?, error = ?, finished_at = ?, updated_at = ?, current_status_json = NULL
            WHERE id = ?
            {terminal_guard}
            """,
            (status, result, error, now, now, execution_id),
        )


def get_execution(execution_id: str, user: dict[str, Any] | None = None) -> dict[str, Any] | None:
    init_db()
    user = user if user is not None else get_current_user()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT executions.*, users.username, users.first_name, users.last_name
            FROM executions
            LEFT JOIN users ON users.id = executions.created_by
            WHERE executions.id = ?
            """,
            (execution_id,),
        ).fetchone()
    job = _row_to_job(row)
    if not job:
        return None
    if user and user.get("role") != "admin" and job.get("created_by") != user.get("id"):
        return None
    return job


def list_executions(user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    init_db()
    user = user if user is not None else get_current_user()
    query = """
        SELECT executions.*, users.username, users.first_name, users.last_name
        FROM executions
        LEFT JOIN users ON users.id = executions.created_by
    """
    params: tuple[Any, ...] = ()
    if user and user.get("role") != "admin":
        query += " WHERE executions.created_by = ?"
        params = (user.get("id"),)
    query += " ORDER BY executions.created_at DESC"
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_job(row) for row in rows]


def delete_execution(execution_id: str, user: dict[str, Any] | None = None) -> bool:
    init_db()
    user = user if user is not None else get_current_user()
    if not user:
        return False
    deletable_statuses = {"done", "error", "failed", "canceled", "cancelled"}

    with connect() as conn:
        row = conn.execute("SELECT created_by, status FROM executions WHERE id = ?", (execution_id,)).fetchone()
        if not row:
            return False
        if row["created_by"] is not None and row["created_by"] != user.get("id"):
            return False
        if row["status"] not in deletable_statuses:
            return False
        conn.execute("DELETE FROM executions WHERE id = ?", (execution_id,))
    return True


def _row_to_job(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if not row:
        return None
    data = dict(row)
    owner = {
        "id": data.get("created_by"),
        "username": data.get("username") or "",
        "first_name": data.get("first_name") or "",
        "last_name": data.get("last_name") or "",
    }
    owner["display_name"] = _display_name(owner)
    return {
        "id": data["id"],
        "label": data["execution_name"],
        "execution_type": data["execution_type"],
        "status": data["status"],
        "result": data.get("result"),
        "error": data.get("error"),
        "started": data["created_at"],
        "finished": data.get("finished_at"),
        "logs": _loads(data.get("logs_json"), []),
        "current_status": _loads(data.get("current_status_json"), None),
        "metadata": _loads(data.get("metadata_json"), {}),
        "created_by": data.get("created_by"),
        "created_by_user": owner,
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
    }


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


init_db()
