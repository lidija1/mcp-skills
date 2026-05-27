from fastapi import APIRouter

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.get("/health")
def chat_health():
    return {"status": "chat ok"}