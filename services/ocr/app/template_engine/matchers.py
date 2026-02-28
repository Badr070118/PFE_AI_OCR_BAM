from __future__ import annotations

import re
from typing import Any

from app.template_engine.utils import clean_value, normalize_compact, normalize_text


def _find_label_indices(raw_lines: list[str], labels: list[str]) -> list[int]:
    if not raw_lines or not labels:
        return []
    normalized_labels = [normalize_text(label) for label in labels if label]
    indices: list[int] = []
    for idx, line in enumerate(raw_lines):
        line_norm = normalize_text(line)
        if any(label in line_norm for label in normalized_labels):
            indices.append(idx)
    return indices


def value_after_colon(raw_lines: list[str], labels: list[str]) -> tuple[str, str]:
    indices = _find_label_indices(raw_lines, labels)
    for idx in indices:
        line = raw_lines[idx]
        if ":" in line:
            left, right = line.split(":", 1)
            if right.strip():
                return clean_value(right), line
            # Handle repeated key:value pairs on same line.
            if right.strip() == "" and idx + 1 < len(raw_lines):
                nxt = raw_lines[idx + 1].strip()
                if nxt and ":" not in nxt:
                    return clean_value(nxt), line
        # Label can be a standalone line and value is next one.
        for label in labels:
            if normalize_text(line) == normalize_text(label) and idx + 1 < len(raw_lines):
                nxt = raw_lines[idx + 1]
                if nxt and ":" not in nxt:
                    return clean_value(nxt), line
    return "", ""


def value_next_line(raw_lines: list[str], labels: list[str]) -> tuple[str, str]:
    indices = _find_label_indices(raw_lines, labels)
    for idx in indices:
        if idx + 1 >= len(raw_lines):
            continue
        nxt = clean_value(raw_lines[idx + 1])
        if nxt:
            return nxt, raw_lines[idx]
    return "", ""


def regex_search(raw_text: str, pattern: str, group: int = 1, flags: int = re.IGNORECASE) -> tuple[str, str]:
    match = re.search(pattern, raw_text or "", flags=flags)
    if not match:
        return "", ""
    value = clean_value(match.group(group))
    return value, clean_value(match.group(0))


def value_right_of_label_using_bbox(
    lines: list[dict[str, Any]] | None,
    labels: list[str],
) -> tuple[str, str]:
    if not isinstance(lines, list) or not labels:
        return "", ""

    normalized_labels = [normalize_compact(label) for label in labels if label]
    best_candidate: tuple[float, str, str] | None = None

    for line in lines:
        text = str(line.get("text", ""))
        text_compact = normalize_compact(text)
        if not any(label and label in text_compact for label in normalized_labels):
            continue

        bbox = line.get("bbox") or [0.0, 0.0, 0.0, 0.0]
        page = int(line.get("page", 1))
        x0, y0, x1, y1 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])

        # Prefer inline "Label: value".
        if ":" in text:
            right = clean_value(text.split(":", 1)[1])
            if right:
                return right, text

        # Search aligned line to the right, same page and near y.
        for candidate in lines:
            if int(candidate.get("page", 1)) != page:
                continue
            ctext = clean_value(str(candidate.get("text", "")))
            if not ctext or ctext == text:
                continue
            cbbox = candidate.get("bbox") or [0.0, 0.0, 0.0, 0.0]
            cx0, cy0 = float(cbbox[0]), float(cbbox[1])
            if cx0 <= x1 - 2:
                continue
            if abs(cy0 - y0) > max(10.0, (y1 - y0) * 1.6):
                continue
            distance = abs(cy0 - y0) + (cx0 - x1)
            if best_candidate is None or distance < best_candidate[0]:
                best_candidate = (distance, ctext, text)

    if best_candidate is None:
        return "", ""
    return best_candidate[1], best_candidate[2]


def find_block_between(
    raw_lines: list[str],
    start_markers: list[str],
    end_markers: list[str],
) -> list[str]:
    if not raw_lines:
        return []
    starts = _find_label_indices(raw_lines, start_markers)
    if not starts:
        return []
    start_idx = starts[0] + 1
    end_idx = len(raw_lines)
    end_candidates = _find_label_indices(raw_lines, end_markers)
    for idx in end_candidates:
        if idx >= start_idx:
            end_idx = idx
            break
    return raw_lines[start_idx:end_idx]

