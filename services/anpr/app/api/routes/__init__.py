from fastapi import APIRouter

from app.api.routes.anpr import router as anpr_router
from app.api.routes.health import router as health_router
from app.api.routes.reports import router as reports_router

router = APIRouter()
router.include_router(health_router)
router.include_router(anpr_router)
router.include_router(reports_router)

__all__ = ["router"]
