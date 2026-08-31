from fastapi import APIRouter
from backend.app.db.session import test_connection

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/health/db")
def health_db():
    ok = test_connection()
    return {"database": "ok" if ok else "unreachable"}
