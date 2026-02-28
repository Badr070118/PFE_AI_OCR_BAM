from app.structured_extraction.detector import detect_pdf_kind
from app.structured_extraction.ocr_scan import extract_scanned
from app.structured_extraction.pdf_native import extract_native_pdf
from app.structured_extraction.render_html import concat_structured_pages_html, render_structured_html
from app.structured_extraction.unify import build_structured_extraction, tables_to_html_payload

__all__ = [
    "build_structured_extraction",
    "concat_structured_pages_html",
    "detect_pdf_kind",
    "extract_native_pdf",
    "extract_scanned",
    "render_structured_html",
    "tables_to_html_payload",
]
