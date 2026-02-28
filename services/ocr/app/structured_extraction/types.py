from __future__ import annotations

from typing import Any, TypedDict


class StructuredLine(TypedDict):
    text: str
    bbox: list[float]
    page: int
    confidence: float


class StructuredCell(TypedDict):
    row: int
    col: int
    text: str
    bbox: list[float] | None


class StructuredTable(TypedDict):
    page: int
    bbox: list[float] | None
    html: str
    cells: list[StructuredCell]


class StructuredExtraction(TypedDict):
    doc_kind: str
    engine: str
    raw_text: str
    lines: list[StructuredLine]
    tables: list[StructuredTable]
    meta: dict[str, Any]
