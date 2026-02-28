from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SERVICE_OCR_DIR = ROOT_DIR / "services" / "ocr"
if str(SERVICE_OCR_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_OCR_DIR))

from app.structured_extraction.unify import build_structured_extraction, tables_to_html_payload


def test_build_structured_extraction_has_required_keys() -> None:
    structured = build_structured_extraction(
        doc_kind="native",
        engine="pdfplumber",
        raw_text="ligne 1\nligne 2",
        lines=[
            {"text": "ligne 1", "bbox": [1, 2, 3, 4], "page": 1, "confidence": 1.0},
        ],
        tables=[
            {
                "page": 1,
                "bbox": None,
                "html": "<table><tr><td>A</td></tr></table>",
                "cells": [{"row": 0, "col": 0, "text": "A", "bbox": None}],
            }
        ],
        meta={"foo": "bar"},
    )

    assert set(structured.keys()) == {"doc_kind", "engine", "raw_text", "lines", "tables", "meta"}
    assert structured["doc_kind"] == "native"
    assert isinstance(structured["lines"], list)
    assert isinstance(structured["tables"], list)


def test_tables_to_html_payload_returns_page_and_html_only() -> None:
    structured = build_structured_extraction(
        doc_kind="scan",
        engine="paddleocr",
        raw_text="",
        tables=[
            {"page": 2, "bbox": None, "html": "<table><tr><td>X</td></tr></table>", "cells": []},
            {"page": 3, "bbox": None, "html": "", "cells": []},
        ],
    )
    payload = tables_to_html_payload(structured)
    assert payload == [{"page": 2, "html": "<table><tr><td>X</td></tr></table>"}]
