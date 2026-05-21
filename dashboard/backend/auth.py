from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from models import User
from security import verify_password

router = APIRouter(tags=["Authentication"])

from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login")
def login():
    return {
        "access_token": "demo-token",
        "token_type": "bearer"
    }

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    username: str
    role: str


@router.post(
    "/api/login",
    response_model=LoginResponse,
    summary="Authenticate user"
)
def login(req: LoginRequest):
    """
    Authenticate a user using username and password.
    """

    db: Session = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.username == req.username)
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )

        if not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )

        return LoginResponse(
            success=True,
            username=user.username,
            role=user.role,
        )

    finally:
        db.close()