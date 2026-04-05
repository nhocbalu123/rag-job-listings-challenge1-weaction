from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service health check")
def health_check(db: Session = Depends(get_db)):
    """
    Checks:
    - API is running
    - PostgreSQL connection is alive
    Returns 200 OK when all systems are healthy.
    """
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
