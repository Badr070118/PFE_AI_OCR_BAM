from fastapi import APIRouter, Depends

from app.db.health import get_db_health

router = APIRouter(tags=["health"])


@router.get("/health")
def health_root(payload: dict = Depends(get_db_health)) -> dict:
    return payload


@router.get("/api/ocr/health")
def health_prefixed(payload: dict = Depends(get_db_health)) -> dict:
    return payload

