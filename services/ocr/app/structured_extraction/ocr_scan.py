from __future__ import annotations

from pathlib import Path
import logging
import os
from typing import Any

import numpy as np
from PIL import Image

from app.legacy.ocr import extract_text_with_local_ocr


logger = logging.getLogger(__name__)

_OCR_ENGINE = None
_STRUCTURE_ENGINE = None


def _pil_to_bgr_array(image: Image.Image) -> np.ndarray:
    rgb = np.array(image.convert("RGB"))
    return rgb[:, :, ::-1]


def _preprocess_for_ocr(bgr: np.ndarray, enabled: bool = True) -> np.ndarray:
    if not enabled:
        return bgr
    try:
        import cv2  # type: ignore
    except Exception:
        return bgr

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresholded = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35,
        11,
    )
    return cv2.cvtColor(thresholded, cv2.COLOR_GRAY2BGR)


def _bbox_from_polygon(polygon: Any) -> list[float]:
    if not isinstance(polygon, (list, tuple)) or not polygon:
        return [0.0, 0.0, 0.0, 0.0]
    xs: list[float] = []
    ys: list[float] = []
    for point in polygon:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            try:
                xs.append(float(point[0]))
                ys.append(float(point[1]))
            except (TypeError, ValueError):
                continue
    if not xs or not ys:
        return [0.0, 0.0, 0.0, 0.0]
    return [min(xs), min(ys), max(xs), max(ys)]


def _get_paddle_ocr():
    global _OCR_ENGINE
    if _OCR_ENGINE is not None:
        return _OCR_ENGINE
    from paddleocr import PaddleOCR  # type: ignore

    lang = (os.getenv("PADDLE_OCR_LANG") or "fr").strip() or "fr"
    _OCR_ENGINE = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
    return _OCR_ENGINE


def _get_pp_structure():
    global _STRUCTURE_ENGINE
    if _STRUCTURE_ENGINE is not None:
        return _STRUCTURE_ENGINE
    from paddleocr import PPStructure  # type: ignore

    lang = (os.getenv("PADDLE_OCR_LANG") or "fr").strip() or "fr"
    _STRUCTURE_ENGINE = PPStructure(show_log=False, lang=lang, layout=True, table=True, ocr=True)
    return _STRUCTURE_ENGINE


def _extract_lines_with_paddle(image_array: np.ndarray, page: int) -> list[dict]:
    engine = _get_paddle_ocr()
    result = engine.ocr(image_array, cls=True) or []
    page_result = result[0] if result and isinstance(result[0], list) else result

    lines: list[dict] = []
    for item in page_result:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        polygon = item[0]
        text_info = item[1]
        if not isinstance(text_info, (list, tuple)) or len(text_info) < 2:
            continue
        text = str(text_info[0]).strip()
        if not text:
            continue
        try:
            confidence = float(text_info[1])
        except (TypeError, ValueError):
            confidence = 0.0
        lines.append(
            {
                "text": text,
                "bbox": _bbox_from_polygon(polygon),
                "page": page,
                "confidence": max(0.0, min(1.0, confidence)),
            }
        )
    return lines


def _extract_tables_with_structure(image_array: np.ndarray, page: int) -> list[dict]:
    structure_engine = _get_pp_structure()
    result = structure_engine(image_array) or []
    tables: list[dict] = []
    for block in result:
        if not isinstance(block, dict):
            continue
        if str(block.get("type", "")).lower() != "table":
            continue
        bbox_raw = block.get("bbox")
        bbox = None
        if isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) == 4:
            try:
                bbox = [float(bbox_raw[0]), float(bbox_raw[1]), float(bbox_raw[2]), float(bbox_raw[3])]
            except (TypeError, ValueError):
                bbox = None

        html = ""
        res = block.get("res")
        if isinstance(res, dict):
            html = str(res.get("html", "") or "")
        if not html:
            html = str(block.get("html", "") or "")
        if not html:
            continue

        tables.append(
            {
                "page": page,
                "bbox": bbox,
                "html": html,
                "cells": [],
            }
        )
    return tables


def _pdf_to_images(file_path: str, dpi: int = 300) -> list[Image.Image]:
    try:
        from pdf2image import convert_from_path  # type: ignore
        from pdf2image.exceptions import PDFInfoNotInstalledError  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "pdf2image n'est pas installe. Installez les dependances structured extraction."
        ) from exc

    try:
        return convert_from_path(file_path, dpi=dpi)
    except PDFInfoNotInstalledError as exc:
        raise RuntimeError(
            "Poppler introuvable. Installez Poppler et ajoutez 'bin' au PATH."
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            "Conversion PDF -> image impossible (verifiez Poppler/pdftoppm)."
        ) from exc


def _legacy_fallback(file_path: str, doc_kind: str, warning: str) -> dict:
    text = extract_text_with_local_ocr(file_path)
    lines = []
    for idx, line in enumerate((text or "").splitlines(), start=1):
        cleaned = line.strip()
        if not cleaned:
            continue
        lines.append(
            {
                "text": cleaned,
                "bbox": [0.0, 0.0, 0.0, 0.0],
                "page": 1,
                "confidence": 0.5,
            }
        )
    return {
        "raw_text": text or "",
        "lines": lines,
        "tables": [],
        "engine": "legacy_local_ocr",
        "meta": {
            "source": "fallback",
            "warning": warning,
        },
        "doc_kind": doc_kind,
    }


def extract_scanned(file_path: str) -> dict:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {file_path}")

    suffix = path.suffix.lower()
    is_pdf = suffix == ".pdf"
    doc_kind = "scan" if is_pdf else "image"

    images: list[Image.Image] = []
    if is_pdf:
        try:
            images = _pdf_to_images(file_path, dpi=300)
        except Exception as exc:
            logger.warning("PDF->images a echoue, fallback OCR legacy: %s", exc)
            return _legacy_fallback(file_path, doc_kind, str(exc))
    else:
        images = [Image.open(path)]

    try:
        all_lines: list[dict] = []
        all_tables: list[dict] = []
        for page_number, image in enumerate(images, start=1):
            bgr = _pil_to_bgr_array(image)
            prepared = _preprocess_for_ocr(bgr, enabled=True)
            try:
                page_lines = _extract_lines_with_paddle(prepared, page=page_number)
                page_tables = _extract_tables_with_structure(prepared, page=page_number)
            except Exception as exc:
                logger.warning("PaddleOCR/PP-Structure indisponible, fallback OCR legacy: %s", exc)
                return _legacy_fallback(file_path, doc_kind, str(exc))

            all_lines.extend(page_lines)
            all_tables.extend(page_tables)

        raw_text = "\n".join(line["text"] for line in all_lines).strip()
        return {
            "raw_text": raw_text,
            "lines": all_lines,
            "tables": all_tables,
            "engine": "paddleocr",
            "meta": {
                "source": "scan_layout",
                "page_count": len(images),
                "line_count": len(all_lines),
                "table_count": len(all_tables),
            },
            "doc_kind": doc_kind,
        }
    finally:
        for image in images:
            try:
                image.close()
            except Exception:
                pass
