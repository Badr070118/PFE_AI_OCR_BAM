from __future__ import annotations

from pathlib import Path
import html
import logging
from typing import Any


logger = logging.getLogger(__name__)


def _bbox_from_words(words: list[dict[str, Any]]) -> list[float]:
    x0 = min(float(word.get("x0", 0.0)) for word in words)
    top = min(float(word.get("top", 0.0)) for word in words)
    x1 = max(float(word.get("x1", 0.0)) for word in words)
    bottom = max(float(word.get("bottom", 0.0)) for word in words)
    return [x0, top, x1, bottom]


def _group_words_into_lines(words: list[dict[str, Any]], page_number: int, y_tolerance: float = 3.0) -> list[dict]:
    if not words:
        return []

    sorted_words = sorted(words, key=lambda item: (float(item.get("top", 0.0)), float(item.get("x0", 0.0))))
    groups: list[dict[str, Any]] = []

    for word in sorted_words:
        top = float(word.get("top", 0.0))
        placed = False
        for group in groups:
            if abs(top - group["top"]) <= y_tolerance:
                group["words"].append(word)
                group["top"] = (group["top"] + top) / 2.0
                placed = True
                break
        if not placed:
            groups.append({"top": top, "words": [word]})

    lines: list[dict] = []
    for group in groups:
        line_words = sorted(group["words"], key=lambda item: float(item.get("x0", 0.0)))
        line_text = " ".join(str(word.get("text", "")).strip() for word in line_words).strip()
        if not line_text:
            continue
        lines.append(
            {
                "text": line_text,
                "bbox": _bbox_from_words(line_words),
                "page": page_number,
                "confidence": 1.0,
            }
        )
    return lines


def _extract_lines_with_pdfplumber(file_path: str) -> tuple[list[dict], str]:
    import pdfplumber  # type: ignore

    all_lines: list[dict] = []
    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(use_text_flow=True, keep_blank_chars=False) or []
            page_lines = _group_words_into_lines(words, page_number=page_number)
            all_lines.extend(page_lines)

    raw_text = "\n".join(line["text"] for line in all_lines).strip()
    return all_lines, raw_text


def _df_to_cells(df: Any) -> list[dict]:
    cells: list[dict] = []
    for row_index in range(df.shape[0]):
        for col_index in range(df.shape[1]):
            value = "" if df.iat[row_index, col_index] is None else str(df.iat[row_index, col_index])
            cells.append(
                {
                    "row": int(row_index),
                    "col": int(col_index),
                    "text": value,
                    "bbox": None,
                }
            )
    return cells


def _extract_tables_with_camelot(file_path: str) -> tuple[list[dict], str | None]:
    try:
        import camelot  # type: ignore
    except Exception as exc:
        logger.info("Camelot indisponible, fallback pdfplumber-only: %s", exc)
        return [], None

    tables = None
    for flavor in ("stream", "lattice"):
        try:
            candidate = camelot.read_pdf(file_path, pages="1-end", flavor=flavor)
            if len(candidate) > 0:
                tables = candidate
                break
            if tables is None:
                tables = candidate
        except Exception as exc:
            logger.warning("Camelot (%s) a echoue: %s", flavor, exc)

    if tables is None or len(tables) == 0:
        return [], None

    extracted_tables: list[dict] = []
    for table in tables:
        df = table.df.fillna("")
        try:
            page = int(str(getattr(table, "page", "1")))
        except (TypeError, ValueError):
            page = 1
        bbox_raw = getattr(table, "_bbox", None)
        bbox = None
        if isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) == 4:
            try:
                bbox = [float(bbox_raw[0]), float(bbox_raw[1]), float(bbox_raw[2]), float(bbox_raw[3])]
            except (TypeError, ValueError):
                bbox = None
        extracted_tables.append(
            {
                "page": page,
                "bbox": bbox,
                "html": df.to_html(index=False, border=1),
                "cells": _df_to_cells(df),
            }
        )
    return extracted_tables, "camelot"


def _matrix_to_html(matrix: list[list[str | None]]) -> tuple[str, list[dict]]:
    if not matrix:
        return "", []
    col_count = max((len(row) for row in matrix), default=0)
    if col_count == 0:
        return "", []

    rows_normalized: list[list[str]] = []
    for row in matrix:
        norm_row = [(cell or "") for cell in row]
        if len(norm_row) < col_count:
            norm_row.extend([""] * (col_count - len(norm_row)))
        rows_normalized.append(norm_row)

    html_rows = []
    cells: list[dict] = []
    for row_idx, row in enumerate(rows_normalized):
        cols = []
        for col_idx, value in enumerate(row):
            text = str(value)
            cols.append(f"<td>{html.escape(text)}</td>")
            cells.append(
                {
                    "row": row_idx,
                    "col": col_idx,
                    "text": text,
                    "bbox": None,
                }
            )
        html_rows.append("<tr>" + "".join(cols) + "</tr>")

    table_html = "<table><tbody>" + "".join(html_rows) + "</tbody></table>"
    return table_html, cells


def _extract_tables_with_pdfplumber(file_path: str) -> list[dict]:
    import pdfplumber  # type: ignore

    extracted_tables: list[dict] = []
    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            matrices = page.extract_tables() or []
            for matrix in matrices:
                table_html, cells = _matrix_to_html(matrix)
                if not table_html:
                    continue
                extracted_tables.append(
                    {
                        "page": page_number,
                        "bbox": None,
                        "html": table_html,
                        "cells": cells,
                    }
                )
    return extracted_tables


def extract_native_pdf(file_path: str) -> dict:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {file_path}")

    lines, raw_text = _extract_lines_with_pdfplumber(file_path)
    tables, camelot_engine = _extract_tables_with_camelot(file_path)
    engine = "pdfplumber"

    if tables:
        engine = camelot_engine or "camelot"
    else:
        try:
            tables = _extract_tables_with_pdfplumber(file_path)
        except Exception as exc:
            logger.warning("Extraction tables pdfplumber echouee: %s", exc)
            tables = []

    return {
        "raw_text": raw_text,
        "lines": lines,
        "tables": tables,
        "engine": engine,
        "meta": {
            "source": "pdf_native",
            "line_count": len(lines),
            "table_count": len(tables),
        },
    }
