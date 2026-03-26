from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _fmt_date(value: date | datetime | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return value.strftime("%Y-%m-%d")


def _fmt_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M")


def _report_type_label(report_type: str) -> str:
    return {
        "daily": "Quotidien",
        "weekly": "Hebdomadaire",
        "monthly": "Mensuel",
        "yearly": "Annuel",
        "custom": "Personnalise",
    }.get(report_type, report_type)


def _register_unicode_fonts() -> tuple[str, str]:
    candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", None),
    ]
    for regular_path, bold_path in candidates:
        regular = Path(regular_path)
        if not regular.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("DejaVuSans", str(regular)))
            bold_name = "DejaVuSans"
            if bold_path:
                bold = Path(bold_path)
                if bold.exists():
                    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(bold)))
                    bold_name = "DejaVuSans-Bold"
            return "DejaVuSans", bold_name
        except Exception:
            continue
    return "Helvetica", "Helvetica-Bold"


def build_presence_pdf(report: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    base_font, bold_font = _register_unicode_fonts()
    styles["Normal"].fontName = base_font
    styles.add(
        ParagraphStyle(
            name="TitleLarge",
            fontName=bold_font,
            fontSize=18,
            leading=22,
            spaceAfter=8,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Brand",
            fontName=bold_font,
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BrandRight",
            fontName=base_font,
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetaCenter",
            fontName=base_font,
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            fontName=bold_font,
            fontSize=12,
            leading=15,
            spaceBefore=10,
            spaceAfter=6,
        )
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        title="Rapport de presence",
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    accesses = report.get("accesses", []) or []

    story: list = []

    logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo_bam.png"
    logo = None
    if logo_path.exists():
        logo = Image(str(logo_path), width=2.4 * cm, height=2.4 * cm)
        logo.hAlign = "LEFT"

    brand_block = Paragraph("Bank Al-Maghrib", styles["Brand"])
    right_block = Paragraph("Bank Al-Maghrib \u2013 Rapport de pr\u00e9sence", styles["BrandRight"])
    title_block = Paragraph("Rapport de presence", styles["TitleLarge"])
    header_rows = [[logo or "", brand_block, right_block]]
    header_table = Table(header_rows, colWidths=[2.8 * cm, 9.4 * cm, 4.8 * cm])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 6))
    story.append(title_block)
    story.append(Paragraph(f"Type: {_report_type_label(report.get('report_type', ''))}", styles["MetaCenter"]))
    story.append(
        Paragraph(
            f"Periode: {_fmt_date(report.get('start_date'))} au {_fmt_date(report.get('end_date'))}",
            styles["MetaCenter"],
        )
    )
    story.append(Paragraph(f"Genere le: {_fmt_datetime(report.get('generated_at'))}", styles["MetaCenter"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Derniers acces", styles["SectionTitle"]))
    if not accesses:
        story.append(Paragraph("Aucune donnee disponible pour cette periode.", styles["Normal"]))
        doc.build(story)
        return

    access_rows = [["Employe", "Plaque", "Entree", "Sortie", "Statut"]]
    for item in accesses:
        access_rows.append(
            [
                item.get("employee_name") or "-",
                item.get("plate_number") or "-",
                _fmt_datetime(item.get("entry_time")),
                _fmt_datetime(item.get("exit_time")),
                item.get("status") or "-",
            ]
        )

    access_table = Table(access_rows, repeatRows=1, colWidths=[4.5 * cm, 3.5 * cm, 3 * cm, 3 * cm, 3 * cm])
    access_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 1), (-1, -1), base_font),
            ]
        )
    )
    story.append(access_table)

    doc.build(story)


__all__ = ["build_presence_pdf"]
