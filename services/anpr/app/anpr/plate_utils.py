from __future__ import annotations

import re
import unicodedata

_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_EASTERN_ARABIC_DIGITS = "۰۱۲۳۴۵۶۷۸۹"


def _normalize_digits(value: str) -> str:
    if not value:
        return value
    table = {ord(ch): str(index) for index, ch in enumerate(_ARABIC_DIGITS)}
    table.update({ord(ch): str(index) for index, ch in enumerate(_EASTERN_ARABIC_DIGITS)})
    return value.translate(table)


def normalize_plate(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Cf")
    normalized = _normalize_digits(normalized)
    normalized = normalized.replace("|", "-")
    normalized = normalized.replace(" ", "")
    normalized = normalized.replace("\u2013", "-").replace("\u2014", "-")
    normalized = re.sub(r"-+", "-", normalized)
    normalized = normalized.strip("-")
    return normalized.upper()


def plate_loose_key(value: str) -> str:
    if not value:
        return ""
    normalized = normalize_plate(value)
    tokens = [token for token in normalized.split("-") if token]
    if len(tokens) >= 3 and len(tokens[1]) == 1:
        return f"{tokens[0]}-*-{tokens[-1]}"
    return "-".join(tokens)


__all__ = ["normalize_plate", "plate_loose_key"]
