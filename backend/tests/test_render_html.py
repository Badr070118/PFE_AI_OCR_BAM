from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SERVICE_OCR_DIR = ROOT_DIR / "services" / "ocr"
if str(SERVICE_OCR_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_OCR_DIR))

from app.structured_extraction.render_html import render_structured_html


def test_render_html_without_table_has_page_and_paragraph() -> None:
    structured = {
        "raw_text": "Titre\nLigne 1\nLigne 2",
        "lines": [
            {"text": "TITRE:", "bbox": [20, 20, 120, 34], "page": 1, "confidence": 1.0},
            {"text": "Ligne 1", "bbox": [20, 50, 160, 64], "page": 1, "confidence": 1.0},
            {"text": "Ligne 2", "bbox": [20, 66, 160, 80], "page": 1, "confidence": 1.0},
        ],
        "tables": [],
    }
    rendered = render_structured_html(structured)
    pages = rendered.get("pages", [])
    assert isinstance(pages, list)
    assert len(pages) == 1
    html = str(pages[0]["html"])
    assert "class='page'" in html
    assert "<p>" in html or "<h3>" in html


def test_render_html_with_table_contains_table() -> None:
    structured = {
        "raw_text": "",
        "lines": [{"text": "FACTURE", "bbox": [20, 20, 120, 36], "page": 1, "confidence": 1.0}],
        "tables": [
            {
                "page": 1,
                "bbox": [20, 100, 500, 260],
                "html": "<table><tr><td>A</td></tr></table>",
                "cells": [],
            }
        ],
    }
    rendered = render_structured_html(structured)
    pages = rendered.get("pages", [])
    assert len(pages) == 1
    assert "<table>" in str(pages[0]["html"])
