import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import arabic_reshaper
import cv2
import numpy as np

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


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


VIDEO_SAMPLE_SECONDS = max(_env_float("ANPR_VIDEO_SAMPLE_SECONDS", 0.5), 0.1)
VIDEO_MAX_FRAMES = max(_env_int("ANPR_VIDEO_MAX_FRAMES", 30), 1)
VIDEO_EARLY_STOP_SCORE = max(min(_env_float("ANPR_VIDEO_EARLY_STOP_SCORE", 0.72), 1.0), 0.0)
VIDEO_MIN_VOTES = max(_env_int("ANPR_VIDEO_MIN_VOTES", 2), 1)


@dataclass
class VideoCandidate:
    plate_text: str
    normalized: str
    score: float
    frame_index: int
    frame: np.ndarray
    detection_img: np.ndarray
    plate_img: np.ndarray
    segmented_img: np.ndarray | None


@dataclass
class PlateAggregate:
    plate_text: str
    normalized: str
    count: int = 0
    total_score: float = 0.0
    best: VideoCandidate | None = None

    def update(self, candidate: VideoCandidate) -> None:
        self.count += 1
        self.total_score += candidate.score
        if self.best is None or candidate.score > self.best.score:
            self.best = candidate

    def avg_score(self) -> float:
        if not self.count:
            return 0.0
        return self.total_score / self.count


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

    def _apply_trained_ocr_on_plate(self, plate_img: np.ndarray) -> tuple[str, np.ndarray]:
        height, width = plate_img.shape[:2]
        blob, outputs = self.reader.read_plate(plate_img)
        boxes, confidences, class_ids = self.reader.get_boxes(outputs, width, height, threshold=0.3)
        segmented_img, plate_text = self.reader.draw_labels(boxes, confidences, class_ids, plate_img.copy())
        return arabic_reshaper.reshape(plate_text), segmented_img

    def _apply_tesseract_ocr_on_plate(self, plate_img: np.ndarray) -> str:
        return self.reader.tesseract_ocr(plate_img).strip()

    @staticmethod
    def _normalize_plate_text(text: str) -> str:
        normalized = text.strip().upper()
        normalized = normalized.replace(" | ", "-").replace("|", "-").replace(" ", "")
        return normalized

    @staticmethod
    def _score_plate_text(text: str) -> float:
        if not text:
            return 0.0
        cleaned = re.sub(r"[^0-9A-Za-z\u0600-\u06FF]+", "", text)
        if not cleaned:
            return 0.0
        length_score = min(len(cleaned) / 7.0, 1.0)
        has_digit = any(char.isdigit() for char in cleaned)
        has_alpha = any(char.isalpha() for char in cleaned)
        return 0.6 * length_score + 0.2 * (1.0 if has_digit else 0.0) + 0.2 * (1.0 if has_alpha else 0.0)

    def _detect_plate_from_frame(
        self,
        frame: np.ndarray,
        threshold: float = 0.3,
    ) -> tuple[np.ndarray | None, np.ndarray | None, float]:
        height, width = frame.shape[:2]
        blob, outputs = self.detector.detect_plates(frame)
        boxes, confidences, class_ids = self.detector.get_boxes(outputs, width, height, threshold=threshold)
        if not boxes:
            return None, None, 0.0
        detection_img, plate_images = self.detector.draw_labels(boxes, confidences, class_ids, frame.copy())
        if not plate_images:
            return None, None, 0.0
        detection_conf = max(confidences) if confidences else 0.0
        return detection_img, plate_images[0], float(detection_conf)

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

    def process_video(
        self,
        video_path: Path,
        ocr_mode: str = "trained",
        *,
        sample_seconds: float = VIDEO_SAMPLE_SECONDS,
        max_frames: int = VIDEO_MAX_FRAMES,
        min_votes: int = VIDEO_MIN_VOTES,
        early_stop_score: float = VIDEO_EARLY_STOP_SCORE,
    ) -> dict:
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise RuntimeError("Unable to open video file.")

        fps = capture.get(cv2.CAP_PROP_FPS)
        if not fps or fps != fps:
            fps = 24.0
        step = max(1, int(round(fps * sample_seconds)))

        aggregates: dict[str, PlateAggregate] = {}
        best_fallback: VideoCandidate | None = None

        frame_index = 0
        sampled_frames = 0

        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break

                if frame_index % step != 0:
                    frame_index += 1
                    continue

                sampled_frames += 1

                detection_img, plate_img, detection_conf = self._detect_plate_from_frame(frame)
                if detection_img is None or plate_img is None:
                    if best_fallback is None:
                        best_fallback = VideoCandidate(
                            plate_text="",
                            normalized="",
                            score=0.0,
                            frame_index=frame_index,
                            frame=frame.copy(),
                            detection_img=frame.copy(),
                            plate_img=frame.copy(),
                            segmented_img=None,
                        )
                    frame_index += 1
                    if sampled_frames >= max_frames:
                        break
                    continue

                if ocr_mode == "tesseract":
                    plate_text = self._apply_tesseract_ocr_on_plate(plate_img)
                    segmented_img = None
                else:
                    plate_text, segmented_img = self._apply_trained_ocr_on_plate(plate_img)

                plate_text = plate_text.strip()
                if not plate_text:
                    if best_fallback is None:
                        best_fallback = VideoCandidate(
                            plate_text="",
                            normalized="",
                            score=0.0,
                            frame_index=frame_index,
                            frame=frame.copy(),
                            detection_img=detection_img,
                            plate_img=plate_img,
                            segmented_img=segmented_img,
                        )
                    frame_index += 1
                    if sampled_frames >= max_frames:
                        break
                    continue

                normalized = self._normalize_plate_text(plate_text)
                text_score = self._score_plate_text(plate_text)
                combined_score = min(1.0, 0.7 * text_score + 0.3 * min(detection_conf, 1.0))

                candidate = VideoCandidate(
                    plate_text=plate_text,
                    normalized=normalized,
                    score=combined_score,
                    frame_index=frame_index,
                    frame=frame.copy(),
                    detection_img=detection_img,
                    plate_img=plate_img,
                    segmented_img=segmented_img,
                )

                aggregate = aggregates.get(normalized)
                if aggregate is None:
                    aggregate = PlateAggregate(plate_text=plate_text, normalized=normalized)
                    aggregates[normalized] = aggregate
                aggregate.update(candidate)

                if aggregate.count >= min_votes and aggregate.avg_score() >= early_stop_score:
                    break

                frame_index += 1
                if sampled_frames >= max_frames:
                    break
        finally:
            capture.release()

        if not aggregates:
            if best_fallback is None:
                raise RuntimeError("No readable frames in the provided video.")
            return self._persist_video_candidate(
                best_fallback,
                has_plate=False,
                plate_text="",
                video_name=video_path.name,
            )

        best_plate = max(
            aggregates.values(),
            key=lambda agg: (agg.count, agg.avg_score(), agg.best.score if agg.best else 0.0),
        )
        best_candidate = best_plate.best or best_fallback
        if best_candidate is None:
            raise RuntimeError("Video analysis failed to produce a frame.")
        return self._persist_video_candidate(
            best_candidate,
            has_plate=True,
            plate_text=best_candidate.plate_text,
            video_name=video_path.name,
        )

    def _persist_video_candidate(
        self,
        candidate: VideoCandidate,
        *,
        has_plate: bool,
        plate_text: str,
        video_name: str | None,
    ) -> dict:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        frame_name = f"received_frame_{stamp}.jpg"
        detection_name = f"video_car_box_{stamp}.jpg"
        plate_name = f"video_plate_box_{stamp}.jpg"
        segmented_name = f"video_plate_segmented_{stamp}.jpg" if candidate.segmented_img is not None else None

        cv2.imwrite(str(RECEIVED_DIR / frame_name), candidate.frame)
        cv2.imwrite(str(TMP_DIR / detection_name), candidate.detection_img)
        cv2.imwrite(str(TMP_DIR / plate_name), candidate.plate_img)
        if candidate.segmented_img is not None and segmented_name:
            cv2.imwrite(str(TMP_DIR / segmented_name), candidate.segmented_img)

        artifacts = {
            "input": frame_name,
            "detection": detection_name,
            "plate": plate_name,
            "segmented": segmented_name,
        }
        if video_name:
            artifacts["video"] = video_name

        return {
            "has_plate": has_plate,
            "plate_text": plate_text,
            "artifacts": artifacts,
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
