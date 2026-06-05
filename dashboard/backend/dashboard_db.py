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
from typing import Any


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB = Path("/data/dashboard.db")


def _resolve_db_path() -> Path:
    configured = os.environ.get("DASHBOARD_DB_PATH")
    if configured:
        return Path(configured)
    return _DEFAULT_DB


DB_PATH = _resolve_db_path()
# provera
print("DB PATH:", DB_PATH.resolve())
print("ACTIVE DB:", DB_PATH.resolve())
_current_user: ContextVar[dict[str, Any] | None] = ContextVar("dashboard_current_user", default=None)


def connect() -> sqlite3.Connection:
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
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _migrate_legacy_password_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
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
