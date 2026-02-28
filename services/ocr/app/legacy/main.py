import json
import shutil
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.document_router.router import choose_extractor_name, detect_document_type
from app.legacy.db import (
    Document,
    create_db_and_tables,
    get_db,
    save_document,
    update_document_data,
    update_llama_output,
)
from app.legacy.invoice_ocr import invoice_ocr
from app.legacy.llama_service import (
    extract_hybrid_data_from_text,
    generate_from_llama,
    generate_hybrid_json_from_text,
    merge_hybrid_data,
)
from app.legacy.ocr import (
    extract_text_with_glm_ocr,
    extract_text_with_local_ocr,
    format_extracted_text_as_json,
)
from app.legacy.qa_service import ask_document_question
from app.legacy.review.router import review_router
from app.legacy.schemas import DocumentAskRequest, DocumentAskResponse, DocumentOut

FASTAPI_ROOT_PATH = (os.getenv("FASTAPI_ROOT_PATH") or "").strip()

app = FastAPI(
    title="GLM-OCR API",
    description="FastAPI service for OCR extraction and llama.cpp Llama processing.",
    version="1.0.0",
    root_path=FASTAPI_ROOT_PATH,
)

# Allow the frontend to call the API from the browser.
_cors_origins_raw = os.getenv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5180,http://127.0.0.1:5180",
)
_cors_origins = [origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(review_router)

UPLOADS_DIR = Path(os.getenv("OCR_UPLOAD_DIR") or os.getenv("UPLOADS_DIR") or "uploads")
RESULTS_DIR = Path(
    os.getenv("OCR_RESULTS_DIR") or os.getenv("RESULTS_DIR") or "results"
)
ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/jpg"}
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


@app.on_event("startup")
def on_startup() -> None:
    # Ensure folders and database are ready when the server starts.
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    create_db_and_tables()


@app.get("/", tags=["health"])
def root() -> dict:
    return {"status": "API OK"}


class LlamaRequest(BaseModel):
    text: str
    instruction: str | None = None


class ProcessWithLlamaRequest(BaseModel):
    text: str
    instruction: str | None = None
    document_id: int | None = None
    sync_data: bool = False


class UpdateDocumentDataRequest(BaseModel):
    data: dict[str, Any]
    merge: bool = True


class DetectTypeRequest(BaseModel):
    text: str
    lines: list[str] | None = None


def _is_allowed_upload(file: UploadFile) -> bool:
    extension = Path(file.filename or "").suffix.lower()
    if file.content_type in ALLOWED_CONTENT_TYPES:
        return True
    return extension in ALLOWED_EXTENSIONS


def _normalize_doc_type_override(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"invoice", "bank_statement", "payment_receipt", "wire_transfer"}:
        return normalized
    return None


def _extract_structured_data(
    *,
    doc_type: str,
    extractor_name: str,
    file_path: Path,
    ocr_text: str,
) -> dict[str, Any]:
    if extractor_name == "invoice_table":
        try:
            invoice_result = invoice_ocr(str(file_path), save_debug=False)
            return {
                "table_rows_structured": invoice_result.get("table_rows_structured", []),
                "quality_metrics": invoice_result.get("quality_metrics", {}),
                "warnings": invoice_result.get("warnings", []),
                "doc_type": doc_type,
                "extractor": extractor_name,
            }
        except Exception:
            # Keep service resilient: fallback to legacy generic parser.
            pass

    if extractor_name == "raw_text_only":
        return {}

    return format_extracted_text_as_json(ocr_text)


@app.post("/detect-type", tags=["ocr"])
def detect_type(payload: DetectTypeRequest) -> dict[str, Any]:
    text = payload.text or ""
    if not text.strip() and payload.lines:
        text = "\n".join(payload.lines)
    return detect_document_type(text, payload.lines)


@app.post("/upload", response_model=DocumentOut, tags=["documents"])
async def upload_file(
    file: UploadFile = File(...),
    forced_doc_type: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> Document:
    if not _is_allowed_upload(file):
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    original_name = Path(file.filename or "upload").name
    extension = Path(original_name).suffix.lower()
    safe_name = f"{uuid4().hex}{extension}"
    destination = UPLOADS_DIR / safe_name

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        extracted_text = extract_text_with_glm_ocr(str(destination))
        detection = detect_document_type(extracted_text, None)

        selected_doc_type = detection.get("doc_type", "unknown")
        override_type = _normalize_doc_type_override(forced_doc_type)
        if override_type is not None:
            selected_doc_type = override_type
            detection = {
                "doc_type": override_type,
                "confidence": 1.0,
                "reasons": (detection.get("reasons") or [])
                + [f"type force par l'utilisateur: {override_type}"],
            }

        extractor_name = choose_extractor_name(str(selected_doc_type))
        structured_data = _extract_structured_data(
            doc_type=str(selected_doc_type),
            extractor_name=extractor_name,
            file_path=destination,
            ocr_text=extracted_text,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    document = save_document(
        db, file_name=original_name, data=structured_data, raw_text=extracted_text
    )
    setattr(document, "doc_type_detection", detection)
    return document


@app.post("/ocr", tags=["ocr"])
async def run_local_ocr(file: UploadFile = File(...)) -> dict:
    if not _is_allowed_upload(file):
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    original_name = Path(file.filename or "upload").name
    extension = Path(original_name).suffix.lower()
    safe_name = f"{uuid4().hex}{extension}"
    destination = UPLOADS_DIR / safe_name

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        text = extract_text_with_local_ocr(str(destination))
        detection = detect_document_type(text, None)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"text": text, "doc_type_detection": detection}


@app.post("/ocr/invoice-table", tags=["ocr"])
async def run_invoice_table_ocr(file: UploadFile = File(...)) -> dict:
    if not _is_allowed_upload(file):
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    original_name = Path(file.filename or "upload").name
    extension = Path(original_name).suffix.lower()
    safe_name = f"{uuid4().hex}{extension}"
    destination = UPLOADS_DIR / safe_name

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = invoice_ocr(str(destination))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return result


@app.get("/documents", response_model=list[DocumentOut], tags=["documents"])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    return db.query(Document).order_by(Document.date_uploaded.desc()).all()


@app.post(
    "/documents/{document_id}/ask",
    response_model=DocumentAskResponse,
    tags=["documents"],
)
def ask_document(
    document_id: int,
    payload: DocumentAskRequest,
    db: Session = Depends(get_db),
) -> DocumentAskResponse:
    try:
        return ask_document_question(db, document_id, payload.question)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/generate_with_llama", tags=["llama"])
def generate_with_llama(payload: LlamaRequest) -> dict:
    # Expects OCR text; returns the Ollama Llama-generated result.
    try:
        generated = generate_from_llama(payload.text, payload.instruction)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"result": generated}


@app.post("/process_with_llama", tags=["llama"])
def process_with_llama(
    payload: ProcessWithLlamaRequest, db: Session = Depends(get_db)
) -> dict:
    llm_error: str | None = None
    generated: str = ""
    structured_data = None

    try:
        generated = generate_from_llama(payload.text, payload.instruction)
    except Exception as exc:
        llm_error = str(exc)

    if generated:
        structured_data = extract_hybrid_data_from_text(generated)
        if structured_data is None:
            try:
                structured_data = generate_hybrid_json_from_text(
                    payload.text, payload.instruction
                )
            except Exception:
                structured_data = None

    # Deterministic fallback when neither llama.cpp nor Ollama is reachable.
    if structured_data is None:
        try:
            local_structured = format_extracted_text_as_json(payload.text)
            structured_data = merge_hybrid_data({}, local_structured)
        except Exception:
            structured_data = None

    if structured_data is not None:
        generated = json.dumps(structured_data, ensure_ascii=False, indent=2)
    elif not generated and llm_error:
        generated = (
            "LLM indisponible (llama.cpp/Ollama). "
            "Aucune structuration automatique n'a pu être générée."
        )

    if payload.document_id is not None and payload.sync_data:
        existing_document = (
            db.query(Document).filter(Document.id == payload.document_id).first()
        )
        update_llama_output(db, payload.document_id, generated)
        if existing_document is not None and structured_data is not None:
            merged_data = merge_hybrid_data(existing_document.data, structured_data)
            updated_document = update_document_data(
                db, payload.document_id, merged_data
            )
            structured_data = updated_document.data if updated_document else merged_data

    return {
        "generated_text": generated,
        "document_id": payload.document_id,
        "structured_data": structured_data,
        "warning": llm_error,
    }


@app.put("/documents/{document_id}/data", response_model=DocumentOut, tags=["documents"])
def save_document_structured_data(
    document_id: int,
    payload: UpdateDocumentDataRequest,
    db: Session = Depends(get_db),
) -> Document:
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    final_data = (
        merge_hybrid_data(document.data, payload.data)
        if payload.merge
        else payload.data
    )
    updated = update_document_data(db, document_id, final_data)
    if updated is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return updated


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.legacy.main:app", host="0.0.0.0", port=8000, reload=True)
