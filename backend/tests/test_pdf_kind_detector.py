from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[2]
SERVICE_OCR_DIR = ROOT_DIR / "services" / "ocr"
if str(SERVICE_OCR_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_OCR_DIR))

from app.structured_extraction.detector import detect_pdf_kind


def test_detect_pdf_kind_native_when_text_count_is_high() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "sample_native.pdf"
        path.write_bytes(b"%PDF-1.4\n%mock\n")
        with patch(
            "app.structured_extraction.detector._count_text_with_fitz",
            return_value=(180, 2),
        ):
            result = detect_pdf_kind(str(path))
    assert result["kind"] == "native"
    assert result["has_text"] is True
    assert result["text_char_count"] == 180
    assert result["page_count"] == 2


def test_detect_pdf_kind_scan_when_text_count_is_low() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "sample_scan.pdf"
        path.write_bytes(b"%PDF-1.4\n%mock\n")
        with patch(
            "app.structured_extraction.detector._count_text_with_fitz",
            return_value=(12, 1),
        ):
            result = detect_pdf_kind(str(path))
    assert result["kind"] == "scan"
    assert result["has_text"] is False
