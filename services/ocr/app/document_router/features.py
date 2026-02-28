from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.document_router.rules import DOC_TYPES, KEYWORD_WEIGHTS, REGEX_RULES


DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
AMOUNT_PATTERN = re.compile(r"\b\d{1,3}(?:[ .]\d{3})*(?:[.,]\d{2})\b")


def normalize_text(value: str) -> str:
    lowered = value.lower()
    stripped = unicodedata.normalize("NFKD", lowered)
    stripped = "".join(ch for ch in stripped if not unicodedata.combining(ch))
    stripped = re.sub(r"[ \t]+", " ", stripped)
    return stripped


def normalize_lines(ocr_text: str, ocr_lines: list[str] | None) -> list[str]:
    if ocr_lines:
        base_lines = [line for line in ocr_lines if isinstance(line, str)]
    else:
        base_lines = ocr_text.splitlines()
    return [normalize_text(line).strip() for line in base_lines if line and line.strip()]


def _keyword_hits(text: str) -> dict[str, dict[str, int]]:
    hits: dict[str, dict[str, int]] = {doc_type: {} for doc_type in DOC_TYPES}
    for doc_type, weighted_keywords in KEYWORD_WEIGHTS.items():
        for keyword in weighted_keywords:
            escaped = re.escape(keyword)
            count = len(re.findall(escaped, text))
            if count > 0:
                hits[doc_type][keyword] = count
    return hits


def _regex_hits(text: str) -> dict[str, list[dict[str, Any]]]:
    results: dict[str, list[dict[str, Any]]] = {doc_type: [] for doc_type in DOC_TYPES}
    for doc_type, rules in REGEX_RULES.items():
        for pattern, _weight, reason in rules:
            count = len(re.findall(pattern, text, flags=re.IGNORECASE))
            if count > 0:
                results[doc_type].append(
                    {
                        "pattern": pattern,
                        "count": count,
                        "reason": reason,
                    }
                )
    return results


def _count_transaction_lines(lines: list[str]) -> int:
    txn_count = 0
    for line in lines:
        has_date = bool(DATE_PATTERN.search(line))
        has_amount = len(AMOUNT_PATTERN.findall(line)) >= 1
        mentions_flow = ("debit" in line) or ("credit" in line) or ("solde" in line)
        if (has_date and has_amount) or (has_date and mentions_flow):
            txn_count += 1
    return txn_count


def extract_features(ocr_text: str, ocr_lines: list[str] | None) -> dict[str, Any]:
    normalized_text = normalize_text(ocr_text or "")
    lines = normalize_lines(ocr_text or "", ocr_lines)
    date_line_count = sum(1 for line in lines if DATE_PATTERN.search(line))
    amount_line_count = sum(1 for line in lines if AMOUNT_PATTERN.search(line))
    transaction_line_count = _count_transaction_lines(lines)
    multi_amount_lines = sum(1 for line in lines if len(AMOUNT_PATTERN.findall(line)) >= 2)

    return {
        "text": normalized_text,
        "lines": lines,
        "line_count": len(lines),
        "date_line_count": date_line_count,
        "amount_line_count": amount_line_count,
        "transaction_line_count": transaction_line_count,
        "multi_amount_lines": multi_amount_lines,
        "keyword_hits": _keyword_hits(normalized_text),
        "regex_hits": _regex_hits(normalized_text),
    }
