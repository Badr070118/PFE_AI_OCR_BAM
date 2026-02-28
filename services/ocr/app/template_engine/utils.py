from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def normalize_compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_text(value))


def split_text_lines(raw_text: str) -> list[str]:
    return [line.strip() for line in (raw_text or "").splitlines() if line.strip()]


def looks_like_amount(value: str) -> bool:
    return bool(re.search(r"\d[\d\s]*[.,]\d{2}\s*(mad)?", value, flags=re.IGNORECASE))


def clean_value(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", (value or "")).strip(" :-\t")
    return cleaned


def first_non_empty(values: list[str]) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def normalize_line_entries(lines: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    if not isinstance(lines, list):
        return normalized
    for line in lines:
        if not isinstance(line, dict):
            continue
        text = clean_value(str(line.get("text", "")))
        if not text:
            continue
        bbox = line.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            bbox = [0.0, 0.0, 0.0, 0.0]
        try:
            x0, y0, x1, y1 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        except (TypeError, ValueError):
            x0, y0, x1, y1 = 0.0, 0.0, 0.0, 0.0
        try:
            page = int(line.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        normalized.append(
            {
                "text": text,
                "text_norm": normalize_text(text),
                "bbox": [x0, y0, x1, y1],
                "page": page,
            }
        )
    return normalized

