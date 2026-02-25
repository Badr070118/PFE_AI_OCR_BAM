from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import get_settings
from app.legacy.main import on_startup as legacy_ocr_startup
from app.services.legacy_mount import legacy_ocr_app

settings = get_settings()

app = FastAPI(
    title="OCR Service Gateway",
    version="1.0.0",
    description="Production wrapper for the legacy OCR FastAPI service.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup_legacy_ocr() -> None:
    # Mounted sub-app startup hooks are not guaranteed to run in this wrapper setup.
    legacy_ocr_startup()


app.include_router(api_router)
app.mount(settings.api_prefix, legacy_ocr_app)
