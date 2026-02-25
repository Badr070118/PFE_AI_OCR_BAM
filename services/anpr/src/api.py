import os
import threading
from datetime import datetime
from io import BytesIO
from pathlib import Path

import arabic_reshaper
import cv2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from .detection import PlateDetector
from .ocr import PlateReader

BASE_DIR = Path(__file__).resolve().parent
SERVICE_DIR = BASE_DIR.parent
OUTPUT_ROOT = Path(os.getenv("MLPDR_OUTPUT_DIR", "/srv/service/outputs"))
TMP_DIR = OUTPUT_ROOT / "tmp"
RECEIVED_DIR = OUTPUT_ROOT / "received"

for path in (OUTPUT_ROOT, TMP_DIR, RECEIVED_DIR):
    path.mkdir(parents=True, exist_ok=True)

_cors_origins_raw = os.getenv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost,http://127.0.0.1,http://localhost:5173,http://127.0.0.1:5173",
)
_cors_origins = [origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()]

app = FastAPI(title="MLPDR API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LPDREngine:
    def __init__(self) -> None:
        detection_weights = Path(
            os.getenv(
                "MLPDR_DETECTION_WEIGHTS_PATH",
                str(SERVICE_DIR / "weights" / "detection" / "yolov3-detection_final.weights"),
            )
        )
        detection_cfg = Path(
            os.getenv(
                "MLPDR_DETECTION_CFG_PATH",
                str(SERVICE_DIR / "weights" / "detection" / "yolov3-detection.cfg"),
            )
        )
        ocr_weights = Path(
            os.getenv(
                "MLPDR_OCR_WEIGHTS_PATH",
                str(SERVICE_DIR / "weights" / "ocr" / "yolov3-ocr_final.weights"),
            )
        )
        ocr_cfg = Path(
            os.getenv(
                "MLPDR_OCR_CFG_PATH",
                str(SERVICE_DIR / "weights" / "ocr" / "yolov3-ocr.cfg"),
            )
        )

        missing = [p for p in (detection_weights, detection_cfg, ocr_weights, ocr_cfg) if not p.exists()]
        if missing:
            joined = ", ".join(str(p) for p in missing)
            raise RuntimeError(f"Missing MLPDR model files: {joined}")

        self.detector = PlateDetector()
        self.detector.load_model(str(detection_weights), str(detection_cfg))

        self.reader = PlateReader()
        self.reader.load_model(str(ocr_weights), str(ocr_cfg))

    def _apply_trained_ocr(self, plate_path: Path) -> tuple[str, str | None]:
        image, height, width, channels = self.reader.load_image(str(plate_path))
        blob, outputs = self.reader.read_plate(image)
        boxes, confidences, class_ids = self.reader.get_boxes(outputs, width, height, threshold=0.3)
        segmented_img, plate_text = self.reader.draw_labels(boxes, confidences, class_ids, image)
        segmented_name = "plate_segmented.jpg"
        cv2.imwrite(str(TMP_DIR / segmented_name), segmented_img)
        return arabic_reshaper.reshape(plate_text), segmented_name

    def _apply_tesseract_ocr(self, plate_path: Path) -> str:
        return self.reader.tesseract_ocr(str(plate_path)).strip()

    def process_image(self, image_path: Path, ocr_mode: str = "trained") -> dict:
        image, height, width, channels = self.detector.load_image(str(image_path))
        blob, outputs = self.detector.detect_plates(image)
        boxes, confidences, class_ids = self.detector.get_boxes(outputs, width, height, threshold=0.3)
        detection_img, plate_images = self.detector.draw_labels(boxes, confidences, class_ids, image)

        if not plate_images:
            return {
                "has_plate": False,
                "plate_text": "",
                "artifacts": {
                    "input": image_path.name,
                    "detection": None,
                    "plate": None,
                    "segmented": None,
                },
            }

        detection_name = "car_box.jpg"
        plate_name = "plate_box.jpg"
        plate_path = TMP_DIR / plate_name

        cv2.imwrite(str(TMP_DIR / detection_name), detection_img)
        cv2.imwrite(str(plate_path), plate_images[0])

        if ocr_mode == "tesseract":
            plate_text = self._apply_tesseract_ocr(plate_path)
            segmented_name = None
        else:
            plate_text, segmented_name = self._apply_trained_ocr(plate_path)

        return {
            "has_plate": True,
            "plate_text": plate_text,
            "artifacts": {
                "input": image_path.name,
                "detection": detection_name,
                "plate": plate_name,
                "segmented": segmented_name,
            },
        }


_engine: LPDREngine | None = None
_engine_lock = threading.Lock()


def get_engine() -> LPDREngine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = LPDREngine()
    return _engine


def _safe_child(base: Path, filename: str) -> Path:
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = base / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return path


@app.get("/")
def home() -> dict:
    return {
        "name": "MLPDR API",
        "endpoints": {
            "upload": "POST /upload (multipart form-data: image, ocr_mode=trained|tesseract)",
            "artifact": "GET /artifacts/{filename}",
            "received": "GET /received/{filename}",
        },
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "mlpdr"}


@app.post("/upload")
async def upload_image(
    image: UploadFile = File(...),
    ocr_mode: str = Form("trained"),
) -> dict:
    if ocr_mode not in {"trained", "tesseract"}:
        raise HTTPException(status_code=400, detail="Invalid ocr_mode. Use 'trained' or 'tesseract'.")

    if not image.filename:
        raise HTTPException(status_code=400, detail="Invalid image file")

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

    try:
        result = get_engine().process_image(image_path, ocr_mode=ocr_mode)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"MLPDR processing failed: {exc}") from exc

    ts = int(datetime.now().timestamp() * 1000)
    artifacts = {}
    for key, value in result["artifacts"].items():
        if not value:
            artifacts[key] = None
        elif key == "input":
            artifacts[key] = f"/received/{value}?t={ts}"
        else:
            artifacts[key] = f"/artifacts/{value}?t={ts}"

    return {
        "result": result["plate_text"],
        "plate_text": result["plate_text"],
        "has_plate": result["has_plate"],
        "ocr_mode": ocr_mode,
        "artifacts": artifacts,
    }


@app.get("/artifacts/{filename:path}")
def artifact(filename: str):
    path = _safe_child(TMP_DIR, filename)
    return FileResponse(path)


@app.get("/received/{filename:path}")
def received(filename: str):
    path = _safe_child(RECEIVED_DIR, filename)
    return FileResponse(path)
