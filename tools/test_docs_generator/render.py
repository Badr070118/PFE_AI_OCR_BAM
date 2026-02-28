from __future__ import annotations

from pathlib import Path
from typing import Callable

from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


TemplateFunc = Callable[[canvas.Canvas, dict], None]


def export_pdf(pdf_path: Path, template: TemplateFunc, data: dict) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_canvas = canvas.Canvas(str(pdf_path), pagesize=A4)
    pdf_canvas.setAuthor("test_docs_generator")
    template(pdf_canvas, data)
    pdf_canvas.showPage()
    pdf_canvas.save()


def export_png_from_pdf(pdf_path: Path, png_path: Path, dpi: int = 300) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        pages = convert_from_path(str(pdf_path), dpi=dpi, first_page=1, last_page=1)
    except PDFInfoNotInstalledError as exc:
        raise RuntimeError(
            "Impossible de convertir PDF vers PNG: Poppler est introuvable. "
            "Sous Windows, installez Poppler et ajoutez le dossier 'bin' au PATH."
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            "Conversion PDF vers PNG echouee. Verifiez l'installation de Poppler "
            "et l'accessibilite de ses executables dans le PATH."
        ) from exc

    if not pages:
        raise RuntimeError(f"Aucune page convertie pour le PDF: {pdf_path}")

    pages[0].save(str(png_path), "PNG")


def render_document(pdf_path: Path, png_path: Path, template: TemplateFunc, data: dict, dpi: int = 300) -> None:
    export_pdf(pdf_path, template, data)
    export_png_from_pdf(pdf_path, png_path, dpi=dpi)
