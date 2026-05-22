from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
import sqlite3

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DB_PATH = "users.db"


# ─────────────────────────────────────────────────────────────
# Database setup
# ─────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ─────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


# ─────────────────────────────────────────────────────────────
# Register
# ─────────────────────────────────────────────────────────────

@router.post("/api/register")
def register(data: RegisterRequest):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    existing_user = cursor.execute(
        "SELECT * FROM users WHERE username = ?",
        (data.username,)
    ).fetchone()

    if existing_user:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = pwd_context.hash(data.password)

    cursor.execute("""
        INSERT INTO users (first_name, last_name, username, password)
        VALUES (?, ?, ?, ?)
    """, (
        data.first_name,
        data.last_name,
        data.username,
        hashed_password
    ))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "User created successfully"
    }


# ─────────────────────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────────────────────

@router.post("/api/login")
def login(data: LoginRequest):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    user = cursor.execute(
        "SELECT * FROM users WHERE username = ?",
        (data.username,)
    ).fetchone()

    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    stored_password = user[4]

    if not pwd_context.verify(data.password, stored_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "success": True,
        "user": {
            "id": user[0],
            "first_name": user[1],
            "last_name": user[2],
            "username": user[3]
        }
    }