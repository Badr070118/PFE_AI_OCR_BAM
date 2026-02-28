from __future__ import annotations

from pathlib import Path
import logging


logger = logging.getLogger(__name__)


def _count_text_with_fitz(path: Path, pages_to_check: int) -> tuple[int, int]:
    import fitz  # type: ignore

    document = fitz.open(path)
    try:
        page_count = len(document)
        sample_count = min(page_count, pages_to_check)
        text_char_count = 0
        for page_index in range(sample_count):
            text_char_count += len((document[page_index].get_text("text") or "").strip())
        return text_char_count, page_count
    finally:
        document.close()


def _count_text_with_pdfplumber(path: Path, pages_to_check: int) -> tuple[int, int]:
    import pdfplumber  # type: ignore

    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)
        sample_count = min(page_count, pages_to_check)
        text_char_count = 0
        for page_index in range(sample_count):
            text_char_count += len((pdf.pages[page_index].extract_text() or "").strip())
        return text_char_count, page_count


def detect_pdf_kind(file_path: str) -> dict:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF introuvable: {file_path}")

    # Sample the first pages; if the PDF is tiny we still scan all pages.
    pages_to_check = 2
    text_char_count = 0
    page_count = 0
    backend = None

    try:
        text_char_count, page_count = _count_text_with_fitz(path, pages_to_check)
        backend = "fitz"
    except Exception as fitz_exc:
        logger.debug("detect_pdf_kind: fitz indisponible (%s), fallback pdfplumber", fitz_exc)
        try:
            text_char_count, page_count = _count_text_with_pdfplumber(path, pages_to_check)
            backend = "pdfplumber"
        except Exception as plumber_exc:
            logger.warning(
                "detect_pdf_kind: impossible d'analyser le PDF (%s / %s), fallback scan",
                fitz_exc,
                plumber_exc,
            )
            text_char_count = 0
            page_count = 0

    has_text = text_char_count >= 50
    return {
        "kind": "native" if has_text else "scan",
        "has_text": has_text,
        "text_char_count": int(text_char_count),
        "page_count": int(page_count),
        "backend": backend,
    }
