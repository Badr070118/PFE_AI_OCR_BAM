import os
import threading
from datetime import datetime
from pathlib import Path

import arabic_reshaper
import cv2

from app.core.config import get_settings
from src.detection import PlateDetector
from src.ocr import PlateReader

settings = get_settings()

BASE_DIR = Path(__file__).resolve()
SERVICE_DIR = BASE_DIR.parents[2]

OUTPUT_ROOT = Path(settings.anpr_output_dir).resolve()
TMP_DIR = OUTPUT_ROOT / "tmp"
RECEIVED_DIR = OUTPUT_ROOT / "received"
UNKNOWN_DIR = OUTPUT_ROOT / "unknown"
STREAM_DIR = Path(settings.anpr_stream_dir).resolve()

for path in (OUTPUT_ROOT, TMP_DIR, RECEIVED_DIR, UNKNOWN_DIR, STREAM_DIR):
    path.mkdir(parents=True, exist_ok=True)


def _env_path(name: str, default: Path) -> Path:
    return Path(os.getenv(name, str(default))).resolve()


class AnprEngine:
    def __init__(self) -> None:
        detection_weights = _env_path(
            "MLPDR_DETECTION_WEIGHTS_PATH",
            SERVICE_DIR / "weights" / "detection" / "yolov3-detection_final.weights",
        )
        detection_cfg = _env_path(
            "MLPDR_DETECTION_CFG_PATH",
            SERVICE_DIR / "weights" / "detection" / "yolov3-detection.cfg",
        )
        ocr_weights = _env_path(
            "MLPDR_OCR_WEIGHTS_PATH",
            SERVICE_DIR / "weights" / "ocr" / "yolov3-ocr_final.weights",
        )
        ocr_cfg = _env_path(
            "MLPDR_OCR_CFG_PATH",
            SERVICE_DIR / "weights" / "ocr" / "yolov3-ocr.cfg",
        )

        missing = [p for p in (detection_weights, detection_cfg, ocr_weights, ocr_cfg) if not p.exists()]
        if missing:
            joined = ", ".join(str(p) for p in missing)
            raise RuntimeError(f"Missing MLPDR model files: {joined}")

        self.detector = PlateDetector()
        self.detector.load_model(str(detection_weights), str(detection_cfg))

        self.reader = PlateReader()
        self.reader.load_model(str(ocr_weights), str(ocr_cfg))

    def _apply_trained_ocr(self, plate_path: Path, segmented_name: str) -> str:
        image, height, width, channels = self.reader.load_image(str(plate_path))
        blob, outputs = self.reader.read_plate(image)
        boxes, confidences, class_ids = self.reader.get_boxes(outputs, width, height, threshold=0.3)
        segmented_img, plate_text = self.reader.draw_labels(boxes, confidences, class_ids, image)
        cv2.imwrite(str(TMP_DIR / segmented_name), segmented_img)
        return arabic_reshaper.reshape(plate_text)

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

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        detection_name = f"car_box_{stamp}.jpg"
        plate_name = f"plate_box_{stamp}.jpg"
        segmented_name = f"plate_segmented_{stamp}.jpg"
        plate_path = TMP_DIR / plate_name

        cv2.imwrite(str(TMP_DIR / detection_name), detection_img)
        cv2.imwrite(str(plate_path), plate_images[0])

        if ocr_mode == "tesseract":
            plate_text = self._apply_tesseract_ocr(plate_path)
            segmented_name = None
        else:
            plate_text = self._apply_trained_ocr(plate_path, segmented_name)

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


_engine: AnprEngine | None = None
_engine_lock = threading.Lock()


def get_engine() -> AnprEngine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AnprEngine()
    return _engine


__all__ = [
    "AnprEngine",
    "get_engine",
    "OUTPUT_ROOT",
    "TMP_DIR",
    "RECEIVED_DIR",
    "UNKNOWN_DIR",
    "STREAM_DIR",
]
