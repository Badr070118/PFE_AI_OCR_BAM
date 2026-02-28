from app.structured_extraction.detector import detect_pdf_kind
from app.structured_extraction.ocr_scan import extract_scanned
from app.structured_extraction.pdf_native import extract_native_pdf
from app.structured_extraction.unify import build_structured_extraction, tables_to_html_payload

__all__ = [
    "build_structured_extraction",
    "detect_pdf_kind",
    "extract_native_pdf",
    "extract_scanned",
    "tables_to_html_payload",
]
