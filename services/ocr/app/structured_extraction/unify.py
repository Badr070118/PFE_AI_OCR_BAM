from __future__ import annotations

from typing import Any

from app.structured_extraction.types import StructuredCell, StructuredExtraction, StructuredLine, StructuredTable


def _to_float_list(value: Any, *, default: list[float]) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return default
    try:
        return [float(value[0]), float(value[1]), float(value[2]), float(value[3])]
    except (TypeError, ValueError):
        return default


def _normalize_line(line: dict[str, Any]) -> StructuredLine:
    text = str(line.get("text", "")).strip()
    bbox = _to_float_list(line.get("bbox"), default=[0.0, 0.0, 0.0, 0.0])
    try:
        page = int(line.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        confidence = float(line.get("confidence", 1.0))
    except (TypeError, ValueError):
        confidence = 1.0
    return {
        "text": text,
        "bbox": bbox,
        "page": page,
        "confidence": max(0.0, min(1.0, confidence)),
    }


def _normalize_cell(cell: dict[str, Any]) -> StructuredCell:
    try:
        row = int(cell.get("row", 0))
    except (TypeError, ValueError):
        row = 0
    try:
        col = int(cell.get("col", 0))
    except (TypeError, ValueError):
        col = 0

    bbox_raw = cell.get("bbox")
    bbox = None if bbox_raw is None else _to_float_list(bbox_raw, default=[0.0, 0.0, 0.0, 0.0])
    return {
        "row": row,
        "col": col,
        "text": str(cell.get("text", "")),
        "bbox": bbox,
    }


def _normalize_table(table: dict[str, Any]) -> StructuredTable:
    try:
        page = int(table.get("page", 1))
    except (TypeError, ValueError):
        page = 1

    bbox_raw = table.get("bbox")
    bbox = None if bbox_raw is None else _to_float_list(bbox_raw, default=[0.0, 0.0, 0.0, 0.0])
    cells_raw = table.get("cells") if isinstance(table.get("cells"), list) else []
    cells = [_normalize_cell(cell) for cell in cells_raw if isinstance(cell, dict)]
    return {
        "page": page,
        "bbox": bbox,
        "html": str(table.get("html", "")),
        "cells": cells,
    }


def build_structured_extraction(
    *,
    doc_kind: str,
    engine: str,
    raw_text: str,
    lines: list[dict[str, Any]] | None = None,
    tables: list[dict[str, Any]] | None = None,
    meta: dict[str, Any] | None = None,
) -> StructuredExtraction:
    return {
        "doc_kind": doc_kind,
        "engine": engine,
        "raw_text": raw_text or "",
        "lines": [_normalize_line(line) for line in (lines or []) if isinstance(line, dict)],
        "tables": [_normalize_table(table) for table in (tables or []) if isinstance(table, dict)],
        "meta": meta or {},
    }


def tables_to_html_payload(structured: StructuredExtraction) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for table in structured.get("tables", []):
        html = str(table.get("html", "")).strip()
        if not html:
            continue
        payload.append(
            {
                "page": int(table.get("page", 1)),
                "html": html,
            }
        )
    return payload
