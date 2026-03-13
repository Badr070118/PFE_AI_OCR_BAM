import shutil
from datetime import datetime
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from app.anpr.decision_engine import evaluate_plate
from app.anpr.engine import RECEIVED_DIR, STREAM_DIR, TMP_DIR, get_engine
from app.anpr.rag_module import answer_question
from app.anpr.database import close_parking_session, fetch_alerts, fetch_logs, stats_snapshot
from app.schemas.anpr import AskRequest, AskResponse, DetectDecision, DetectResponse, ExitResponse

router = APIRouter(tags=["anpr"])


def _safe_child(base: Path, filename: str) -> Path:
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = base / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return path


def _build_artifact_urls(artifacts: dict) -> dict:
    prefix = "/api/anpr"
    output = {}
    for key, value in artifacts.items():
        if not value:
            output[key] = None
        elif key == "input":
            output[key] = f"{prefix}/received/{value}"
        else:
            output[key] = f"{prefix}/artifacts/{value}"
    return output


async def _persist_upload(image: UploadFile) -> Path:
    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty image file")
    filename = f"received_{datetime.now().strftime('%Y_%m_%d-%H_%M_%S_%f')}.jpg"
    image_path = RECEIVED_DIR / filename
    try:
        pil_image = Image.open(BytesIO(raw)).convert("RGB")
        pil_image.save(image_path)
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image") from exc
    return image_path


def _persist_stream_path(image_path: str) -> Path:
    candidate = Path(image_path)
    if not candidate.is_absolute():
        candidate = STREAM_DIR / candidate
    candidate = candidate.resolve()
    if STREAM_DIR not in candidate.parents and candidate != STREAM_DIR:
        raise HTTPException(status_code=400, detail="image_path must be inside the stream folder")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="image_path not found")
    filename = f"received_{datetime.now().strftime('%Y_%m_%d-%H_%M_%S_%f')}.jpg"
    target = RECEIVED_DIR / filename
    shutil.copy(candidate, target)
    return target


@router.post("/anpr/detect", response_model=DetectResponse)
async def detect_plate(
    image: UploadFile | None = File(default=None),
    image_path: str | None = Form(default=None),
    ocr_mode: str = Form(default="trained"),
) -> DetectResponse:
    if ocr_mode not in {"trained", "tesseract"}:
        raise HTTPException(status_code=400, detail="Invalid ocr_mode. Use 'trained' or 'tesseract'.")
    if not image and not image_path:
        raise HTTPException(status_code=400, detail="Provide image file or image_path.")

    if image:
        saved_path = await _persist_upload(image)
    else:
        saved_path = _persist_stream_path(image_path or "")

    try:
        result = get_engine().process_image(saved_path, ocr_mode=ocr_mode)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ANPR processing failed: {exc}") from exc

    detected_at = datetime.now()
    image_ref = f"received/{saved_path.name}"

    decision = evaluate_plate(result["plate_text"], image_ref, detected_at)

    response = DetectResponse(
        plate_text=result["plate_text"],
        has_plate=result["has_plate"],
        ocr_mode=ocr_mode,
        decision=DetectDecision(
            status=decision.status,
            action=decision.action,
            gate=decision.gate,
            owner_name=decision.owner_name,
            vehicle_type=decision.vehicle_type,
            reason=decision.reason,
            event=decision.event,
        ),
        artifacts=_build_artifact_urls(result["artifacts"]),
        log_id=decision.log_id,
        image_path=image_ref,
        timestamp=detected_at,
    )
    return response


@router.post("/anpr/exit", response_model=ExitResponse)
async def register_exit(
    plate_number: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    image_path: str | None = Form(default=None),
    ocr_mode: str = Form(default="trained"),
) -> ExitResponse:
    if plate_number:
        result = close_parking_session(plate_number.strip(), datetime.now())
        if not result["closed"]:
            return ExitResponse(
                plate_text=plate_number,
                closed=False,
                log_id=None,
                message="No open parking session found for that plate.",
            )
        return ExitResponse(
            plate_text=plate_number,
            closed=True,
            log_id=result["log_id"],
            message="Exit registered.",
        )

    if not image and not image_path:
        raise HTTPException(status_code=400, detail="Provide plate_number or image/image_path.")

    if image:
        saved_path = await _persist_upload(image)
    else:
        saved_path = _persist_stream_path(image_path or "")

    try:
        detection = get_engine().process_image(saved_path, ocr_mode=ocr_mode)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ANPR processing failed: {exc}") from exc

    if not detection["has_plate"]:
        return ExitResponse(plate_text=None, closed=False, log_id=None, message="No plate detected.")

    plate = detection["plate_text"].strip()
    result = close_parking_session(plate, datetime.now())
    if not result["closed"]:
        return ExitResponse(plate_text=plate, closed=False, log_id=None, message="No open parking session found.")
    return ExitResponse(plate_text=plate, closed=True, log_id=result["log_id"], message="Exit registered.")


@router.get("/anpr/logs")
def get_logs(limit: int = 50, plate_number: str | None = None, status: str | None = None) -> dict:
    logs = fetch_logs(limit=limit, plate_number=plate_number, status=status)
    for row in logs:
        image_path = row.get("image_path")
        if image_path:
            row["image_url"] = f"/api/anpr/received/{Path(image_path).name}"
    return {"items": logs}


@router.get("/anpr/alerts")
def get_alerts(limit: int = 50) -> dict:
    alerts = fetch_alerts(limit=limit)
    for row in alerts.get("blacklisted", []):
        image_path = row.get("image_path")
        if image_path:
            row["image_url"] = f"/api/anpr/received/{Path(image_path).name}"
    for row in alerts.get("unknown", []):
        image_path = row.get("image_path")
        if image_path:
            row["image_url"] = f"/api/anpr/received/{Path(image_path).name}"
    return alerts


@router.get("/anpr/stats")
def get_stats() -> dict:
    return stats_snapshot()


@router.post("/anpr/ask", response_model=AskResponse)
def ask_question(payload: AskRequest) -> AskResponse:
    response = answer_question(payload.question)
    return AskResponse(**response)


@router.get("/anpr/artifacts/{filename:path}")
def artifact(filename: str):
    path = _safe_child(TMP_DIR, filename)
    return FileResponse(path)


@router.get("/anpr/received/{filename:path}")
def received(filename: str):
    path = _safe_child(RECEIVED_DIR, filename)
    return FileResponse(path)


# Legacy root-level aliases required by the spec
@router.get("/logs", include_in_schema=False)
def logs_alias(limit: int = 50, plate_number: str | None = None, status: str | None = None) -> dict:
    return get_logs(limit=limit, plate_number=plate_number, status=status)


@router.get("/alerts", include_in_schema=False)
def alerts_alias(limit: int = 50) -> dict:
    return get_alerts(limit=limit)


@router.post("/ask", include_in_schema=False)
def ask_alias(payload: AskRequest) -> AskResponse:
    return ask_question(payload)
