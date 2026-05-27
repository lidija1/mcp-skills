from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

import dashboard_db
import re

router = APIRouter(tags=["auth"])
SESSION_COOKIE = "dashboard_session"


class RegisterRequest(BaseModel):
    first_name: str = ""
    last_name: str = ""
    username: str
    password: str
    role: str = "user"


class LoginRequest(BaseModel):
    username: str
    password: str


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        if token and token.lower() != "undefined":
            return token
    return request.cookies.get(SESSION_COOKIE)


def user_from_request(request: Request) -> dict | None:
    return dashboard_db.user_for_token(_extract_token(request))


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 12,
        path="/",
    )


@router.post("/api/register")
def register(data: RegisterRequest):
    role = "admin" if dashboard_db.user_count() == 0 else "user"
    try:
        name_regex = r"^[A-Za-zÀ-ž\s-]{2,}$"

        if not re.match(name_regex, data.first_name.strip()):
            raise HTTPException(
                status_code=400,
                detail="First name must contain at least 2 letters and cannot contain numbers or special characters."
            )

        if not re.match(name_regex, data.last_name.strip()):
            raise HTTPException(
                status_code=400,
                detail="Last name must contain at least 2 letters and cannot contain numbers or special characters."
            )

        password_regex = r"^(?=.*[A-Za-z])(?=.*[\d\W]).{8,}$"

        if len(data.username.strip()) < 3:
            raise HTTPException(
                status_code=400,
                detail="Username must contain at least 3 characters."
            )

        if not re.match(password_regex, data.password):
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 8 characters long and contain at least one letter plus one number or special character."
            )

        user = dashboard_db.create_user(
            username=data.username,
            password=data.password,
            first_name=data.first_name,
            last_name=data.last_name,
            role=role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise HTTPException(status_code=400, detail="Username already exists")
        raise

    return {"success": True, "message": "User created successfully", "user": user}


@router.post("/api/login")
@router.post("/api/auth/login")
def login(data: LoginRequest, response: Response):
    user = dashboard_db.authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = dashboard_db.create_session(user["id"])
    set_session_cookie(response, token)
    return {"success": True, "user": user, "access_token": token}


@router.get("/api/auth/me")
def me(request: Request):
    user = user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user": user}


@router.post("/api/auth/logout")
def logout(request: Request, response: Response):
    dashboard_db.revoke_session(_extract_token(request))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"success": True}
