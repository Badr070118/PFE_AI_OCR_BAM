from __future__ import annotations

from collections import defaultdict
import html
from typing import Any


def _safe_bbox(value: Any) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return [0.0, 0.0, 0.0, 0.0]
    try:
        return [float(value[0]), float(value[1]), float(value[2]), float(value[3])]
    except (TypeError, ValueError):
        return [0.0, 0.0, 0.0, 0.0]


def _line_is_title(
    text: str,
    *,
    prev_gap: float,
    next_gap: float,
) -> bool:
    if not text:
        return False
    compact = text.strip()
    if len(compact) > 60:
        return False
    has_alpha = any(ch.isalpha() for ch in compact)
    uppercase_like = has_alpha and compact.upper() == compact
    colon_like = ":" in compact
    isolated = prev_gap >= 18.0 or next_gap >= 18.0
    return uppercase_like or colon_like or isolated


def _flush_paragraph(buffer: list[str], y_top: float, y_bottom: float) -> dict[str, Any] | None:
    text = " ".join(item.strip() for item in buffer if item and item.strip()).strip()
    if not text:
        return None
    return {
        "kind": "paragraph",
        "y": y_top,
        "y_bottom": y_bottom,
        "html": f"<p>{html.escape(text)}</p>",
    }


def _lines_to_blocks(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not lines:
        return []

    ordered = sorted(lines, key=lambda item: (item["bbox"][1], item["bbox"][0]))
    blocks: list[dict[str, Any]] = []

    paragraph_buffer: list[str] = []
    paragraph_y_top = 0.0
    paragraph_y_bottom = 0.0
    prev_line: dict[str, Any] | None = None

    for idx, line in enumerate(ordered):
        text = str(line.get("text", "")).strip()
        if not text:
            continue
        bbox = line["bbox"]

        prev_gap = 999.0
        if prev_line is not None:
            prev_gap = max(0.0, bbox[1] - prev_line["bbox"][3])
        next_gap = 999.0
        if idx + 1 < len(ordered):
            next_gap = max(0.0, ordered[idx + 1]["bbox"][1] - bbox[3])

        is_title = _line_is_title(text, prev_gap=prev_gap, next_gap=next_gap)
        if is_title:
            paragraph = _flush_paragraph(paragraph_buffer, paragraph_y_top, paragraph_y_bottom)
            if paragraph:
                blocks.append(paragraph)
            paragraph_buffer = []

            blocks.append(
                {
                    "kind": "title",
                    "y": bbox[1],
                    "y_bottom": bbox[3],
                    "html": f"<h3>{html.escape(text)}</h3>",
                }
            )
            prev_line = line
            continue

        if prev_line is None or prev_gap > 12.0 or not paragraph_buffer:
            paragraph = _flush_paragraph(paragraph_buffer, paragraph_y_top, paragraph_y_bottom)
            if paragraph:
                blocks.append(paragraph)
            paragraph_buffer = [text]
            paragraph_y_top = bbox[1]
            paragraph_y_bottom = bbox[3]
        else:
            paragraph_buffer.append(text)
            paragraph_y_bottom = max(paragraph_y_bottom, bbox[3])

        prev_line = line

    paragraph = _flush_paragraph(paragraph_buffer, paragraph_y_top, paragraph_y_bottom)
    if paragraph:
        blocks.append(paragraph)
    return blocks


def _detect_two_columns(lines: list[dict[str, Any]]) -> tuple[bool, float]:
    if len(lines) < 8:
        return False, 0.0
    xs = sorted(line["bbox"][0] for line in lines)
    if not xs:
        return False, 0.0
    x_min = xs[0]
    x_max = xs[-1]
    if (x_max - x_min) < 180:
        return False, 0.0

    mid = len(xs) // 2
    median = xs[mid]
    left_count = sum(1 for x in xs if x <= median)
    right_count = sum(1 for x in xs if x > median)
    if left_count < 3 or right_count < 3:
        return False, 0.0
    return True, median


def _render_text_blocks(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not lines:
        return []

    has_two_columns, split = _detect_two_columns(lines)
    if not has_two_columns:
        return _lines_to_blocks(lines)

    left_lines = [line for line in lines if line["bbox"][0] <= split]
    right_lines = [line for line in lines if line["bbox"][0] > split]
    left_blocks = _lines_to_blocks(left_lines)
    right_blocks = _lines_to_blocks(right_lines)

    left_html = "".join(block["html"] for block in left_blocks)
    right_html = "".join(block["html"] for block in right_blocks)
    y_candidates = [line["bbox"][1] for line in lines]
    y = min(y_candidates) if y_candidates else 0.0
    y_bottom = max((line["bbox"][3] for line in lines), default=y)

    return [
        {
            "kind": "columns",
            "y": y,
            "y_bottom": y_bottom,
            "html": (
                "<div class='columns'>"
                f"<div class='col'>{left_html}</div>"
                f"<div class='col'>{right_html}</div>"
                "</div>"
            ),
        }
    ]


def _render_table_blocks(tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, table in enumerate(tables):
        table_html = str(table.get("html", "") or "").strip()
        if not table_html:
            continue
        bbox = table.get("bbox")
        y = 999999.0 + index
        y_bottom = y
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            try:
                y = float(bbox[1])
                y_bottom = float(bbox[3])
            except (TypeError, ValueError):
                pass
        blocks.append(
            {
                "kind": "table",
                "y": y,
                "y_bottom": y_bottom,
                "html": f"<div class='table-block'>{table_html}</div>",
            }
        )
    return blocks


def _render_raw_text_fallback(raw_text: str) -> str:
    paragraphs = [chunk.strip() for chunk in (raw_text or "").split("\n\n") if chunk.strip()]
    if not paragraphs:
        paragraphs = [line.strip() for line in (raw_text or "").splitlines() if line.strip()]
    if not paragraphs:
        return "<p></p>"
    return "".join(f"<p>{html.escape(paragraph)}</p>" for paragraph in paragraphs)


def render_structured_html(structured: dict | None) -> dict:
    if not isinstance(structured, dict):
        return {"pages": []}

    lines_raw = structured.get("lines") if isinstance(structured.get("lines"), list) else []
    tables_raw = structured.get("tables") if isinstance(structured.get("tables"), list) else []
    raw_text = str(structured.get("raw_text", "") or "")

    lines_by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for line in lines_raw:
        if not isinstance(line, dict):
            continue
        text = str(line.get("text", "")).strip()
        if not text:
            continue
        try:
            page = int(line.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        lines_by_page[page].append(
            {
                "text": text,
                "bbox": _safe_bbox(line.get("bbox")),
            }
        )

    tables_by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for table in tables_raw:
        if not isinstance(table, dict):
            continue
        try:
            page = int(table.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        tables_by_page[page].append(table)

    page_numbers = sorted(set(lines_by_page.keys()) | set(tables_by_page.keys()))
    if not page_numbers:
        page_numbers = [1]

    pages: list[dict[str, Any]] = []
    for page in page_numbers:
        text_blocks = _render_text_blocks(lines_by_page.get(page, []))
        table_blocks = _render_table_blocks(tables_by_page.get(page, []))

        blocks = sorted(
            [*text_blocks, *table_blocks],
            key=lambda item: (float(item.get("y", 0.0)), float(item.get("y_bottom", 0.0))),
        )

        if blocks:
            inner = "".join(block["html"] for block in blocks)
        else:
            inner = _render_raw_text_fallback(raw_text)

        page_html = (
            "<div class='doc'>"
            f"<div class='page' data-page='{page}'>"
            f"{inner}"
            "</div>"
            "</div>"
        )
        pages.append({"page": page, "html": page_html})

    return {"pages": pages}


def concat_structured_pages_html(rendered: dict | None) -> str:
    if not isinstance(rendered, dict):
        return ""
    pages = rendered.get("pages")
    if not isinstance(pages, list):
        return ""
    html_parts = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        html_parts.append(str(page.get("html", "") or ""))
    return "".join(html_parts).strip()
