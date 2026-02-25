from fastapi import APIRouter, Depends

from app.db.session import get_db_health

router = APIRouter(tags=["health"])


@router.get("/health")
def health_root(payload: dict = Depends(get_db_health)) -> dict:
    return payload


@router.get("/api/mlpdr/health")
def health_prefixed(payload: dict = Depends(get_db_health)) -> dict:
    return payload


@router.get("/api/anpr/health", include_in_schema=False)
def health_prefixed_legacy(payload: dict = Depends(get_db_health)) -> dict:
    return payload
