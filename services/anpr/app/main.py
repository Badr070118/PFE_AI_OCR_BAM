from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.api.routes.anpr import router as anpr_router
from app.api.routes.reports import router as reports_router
from app.anpr.database import init_db
from app.core.config import get_settings
from app.services.legacy_mount import legacy_mlpdr_app

settings = get_settings()

app = FastAPI(
    title="MLPDR Service Gateway",
    version="1.0.0",
    description="Production wrapper for the legacy MLPDR FastAPI service.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(anpr_router, prefix="/api", include_in_schema=False)
app.include_router(reports_router, prefix="/api", include_in_schema=False)
app.mount(settings.api_prefix, legacy_mlpdr_app)


@app.on_event("startup")
def _startup() -> None:
    init_db()
