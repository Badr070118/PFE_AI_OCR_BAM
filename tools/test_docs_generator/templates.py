from __future__ import annotations

from typing import Iterable, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from data import format_mad


PAGE_WIDTH, PAGE_HEIGHT = A4


def _y_from_top(top: float) -> float:
    return PAGE_HEIGHT - top


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    if max_chars <= 3:
        return value[:max_chars]
    return value[: max_chars - 3] + "..."


def _draw_block(canvas: Canvas, x: float, top: float, width: float, height: float, title: str) -> None:
    y = PAGE_HEIGHT - top - height
    canvas.setLineWidth(1)
    canvas.rect(x, y, width, height, stroke=1, fill=0)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(x + 6, PAGE_HEIGHT - top - 14, title)


def _draw_lines(
    canvas: Canvas,
    x: float,
    top: float,
    lines: Iterable[str],
    line_height: float = 14,
    font_name: str = "Helvetica",
    font_size: int = 9,
) -> None:
    y = _y_from_top(top)
    canvas.setFont(font_name, font_size)
    for line in lines:
        canvas.drawString(x, y, line)
        y -= line_height


def _draw_table(
    canvas: Canvas,
    x: float,
    top: float,
    width: float,
    height: float,
    headers: Sequence[str],
    col_widths: Sequence[float],
    rows: Sequence[Sequence[str]],
    row_height: float = 22,
    right_aligned_cols: Sequence[int] | None = None,
) -> None:
    y = PAGE_HEIGHT - top - height
    canvas.rect(x, y, width, height, stroke=1, fill=0)

    pos = x
    for col_width in col_widths[:-1]:
        pos += col_width
        canvas.line(pos, y, pos, y + height)

    header_bottom = y + height - row_height
    canvas.line(x, header_bottom, x + width, header_bottom)

    max_rows = int((height - row_height) // row_height)
    for i in range(1, max_rows + 1):
        row_line = header_bottom - (i * row_height)
        canvas.line(x, row_line, x + width, row_line)

    canvas.setFont("Helvetica-Bold", 9)
    col_x = x
    for header, col_width in zip(headers, col_widths):
        canvas.drawString(col_x + 4, y + height - 15, header)
        col_x += col_width

    canvas.setFont("Helvetica", 9)
    right_cols = set(right_aligned_cols or [])
    rows_to_draw = min(len(rows), max_rows)

    for row_idx in range(rows_to_draw):
        row = rows[row_idx]
        baseline = header_bottom - (row_idx * row_height) - 15
        col_x = x
        for col_idx, (cell, col_width) in enumerate(zip(row, col_widths)):
            text = _truncate(str(cell), max(5, int(col_width / 5.2)))
            if col_idx in right_cols:
                canvas.drawRightString(col_x + col_width - 4, baseline, text)
            else:
                canvas.drawString(col_x + 4, baseline, text)
            col_x += col_width


def draw_invoice(canvas: Canvas, data: dict) -> None:
    canvas.setStrokeColor(colors.black)
    canvas.setFillColor(colors.black)
    canvas.setTitle(data["invoice_ref"])

    canvas.setFont("Helvetica-Bold", 17)
    canvas.drawString(40, _y_from_top(40), "FACTURE")
    canvas.setFont("Helvetica", 10)
    canvas.drawRightString(555, _y_from_top(40), f"Reference: {data['invoice_ref']}")
    canvas.drawRightString(555, _y_from_top(56), f"Date: {data['invoice_date']}")
    canvas.drawRightString(555, _y_from_top(72), f"Echeance: {data['due_date']}")

    _draw_block(canvas, 40, 84, 250, 115, "FOURNISSEUR")
    _draw_lines(
        canvas,
        48,
        112,
        [
            data["supplier_name"],
            data["supplier_address"],
            f"ICE: {data['supplier_ice']}",
            f"Telephone: {data['supplier_phone']}",
        ],
    )

    _draw_block(canvas, 305, 84, 250, 115, "CLIENT")
    _draw_lines(
        canvas,
        313,
        112,
        [
            data["client_name"],
            data["client_address"],
            f"Contact: {data['client_contact']}",
        ],
    )

    rows = []
    for line in data["lines"]:
        rows.append(
            [
                line["description"],
                str(line["qty"]),
                format_mad(line["unit_price"]),
                format_mad(line["line_total"]),
            ]
        )

    _draw_table(
        canvas,
        x=40,
        top=215,
        width=515,
        height=320,
        headers=["Designation", "Qte", "PU", "Total"],
        col_widths=[245, 60, 105, 105],
        rows=rows,
        right_aligned_cols=[1, 2, 3],
    )

    _draw_block(canvas, 40, 548, 320, 118, "CONDITIONS DE PAIEMENT")
    _draw_lines(
        canvas,
        48,
        576,
        [
            data["payment_terms"],
            "Devise: MAD",
            "Mode: Virement bancaire",
        ],
    )

    _draw_block(canvas, 375, 548, 180, 118, "TOTAUX")
    _draw_lines(
        canvas,
        383,
        576,
        [
            f"Total HT: {format_mad(data['total_ht'])}",
            f"TVA 20%: {format_mad(data['total_vat'])}",
            f"Total TTC: {format_mad(data['total_ttc'])}",
        ],
        line_height=20,
    )


def draw_bank_statement(canvas: Canvas, data: dict) -> None:
    canvas.setStrokeColor(colors.black)
    canvas.setFillColor(colors.black)
    canvas.setTitle(data["statement_ref"])

    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(40, _y_from_top(40), "RELEVE DE COMPTE")
    canvas.setFont("Helvetica", 10)
    canvas.drawRightString(555, _y_from_top(40), f"Reference: {data['statement_ref']}")

    _draw_block(canvas, 40, 76, 515, 120, "INFORMATIONS COMPTE")
    _draw_lines(
        canvas,
        48,
        104,
        [
            f"Banque: {data['bank_name']}",
            f"Titulaire: {data['holder_name']}",
            f"Compte: {data['account_number']}",
            f"IBAN: {data['iban']}",
            f"Periode: du {data['period_start']} au {data['period_end']}",
        ],
    )

    rows = []
    for txn in data["transactions"]:
        rows.append(
            [
                txn["date"],
                txn["label"],
                format_mad(txn["debit"]) if txn["debit"] else "",
                format_mad(txn["credit"]) if txn["credit"] else "",
                format_mad(txn["balance"]),
            ]
        )

    _draw_table(
        canvas,
        x=40,
        top=212,
        width=515,
        height=372,
        headers=["Date", "Libelle", "Debit", "Credit", "Solde"],
        col_widths=[78, 217, 75, 75, 70],
        rows=rows,
        right_aligned_cols=[2, 3, 4],
    )

    _draw_block(canvas, 40, 596, 515, 132, "SYNTHESE PERIODE")
    _draw_lines(
        canvas,
        48,
        624,
        [
            f"Total debit: {format_mad(data['total_debit'])}",
            f"Total credit: {format_mad(data['total_credit'])}",
            f"Solde debut: {format_mad(data['opening_balance'])}",
            f"Solde fin: {format_mad(data['closing_balance'])}",
        ],
        line_height=20,
    )


def draw_payment_receipt(canvas: Canvas, data: dict) -> None:
    canvas.setStrokeColor(colors.black)
    canvas.setFillColor(colors.black)
    canvas.setTitle(data["receipt_ref"])

    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(40, _y_from_top(40), "RECU DE PAIEMENT")
    canvas.setFont("Helvetica", 10)
    canvas.drawRightString(555, _y_from_top(40), f"Reference: {data['receipt_ref']}")

    _draw_block(canvas, 40, 76, 515, 110, "DETAILS RECU")
    _draw_lines(
        canvas,
        48,
        104,
        [
            f"Date: {data['date']}    Heure: {data['time']}",
            f"Canal: {data['channel']}",
            f"Statut: {data['status']}",
        ],
    )

    _draw_block(canvas, 40, 198, 250, 130, "PAYEUR")
    _draw_lines(
        canvas,
        48,
        226,
        [
            data["payer_name"],
            f"Compte: {data['payer_account']}",
        ],
    )

    _draw_block(canvas, 305, 198, 250, 130, "BENEFICIAIRE")
    _draw_lines(
        canvas,
        313,
        226,
        [
            data["beneficiary_name"],
            f"Compte: {data['beneficiary_account']}",
        ],
    )

    _draw_block(canvas, 40, 340, 515, 170, "MONTANTS ET MOTIF")
    _draw_lines(
        canvas,
        48,
        368,
        [
            f"Motif: {data['reason']}",
            f"Montant: {format_mad(data['amount'])}",
            f"Frais: {format_mad(data['fees'])}",
            f"Total debite: {format_mad(data['total'])}",
            "Devise: MAD",
        ],
        line_height=20,
    )

    _draw_block(canvas, 40, 522, 515, 140, "INFORMATIONS TRANSACTION")
    _draw_lines(
        canvas,
        48,
        550,
        [
            f"Transaction ID: {data['transaction_id']}",
            f"Auth code: {data['auth_code']}",
            "Canal securise: OUI",
        ],
        line_height=20,
    )


def draw_wire_transfer(canvas: Canvas, data: dict) -> None:
    canvas.setStrokeColor(colors.black)
    canvas.setFillColor(colors.black)
    canvas.setTitle(data["transfer_ref"])

    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(40, _y_from_top(40), "ORDRE DE VIREMENT")
    canvas.setFont("Helvetica", 10)
    canvas.drawRightString(555, _y_from_top(40), f"Reference: {data['transfer_ref']}")

    _draw_block(canvas, 40, 76, 515, 140, "EMETTEUR")
    _draw_lines(
        canvas,
        48,
        104,
        [
            f"Nom: {data['sender_name']}",
            f"Banque: {data['sender_bank']}",
            f"Compte: {data['sender_account']}",
            f"Adresse: {data['sender_address']}",
        ],
    )

    _draw_block(canvas, 40, 228, 515, 170, "BENEFICIAIRE")
    _draw_lines(
        canvas,
        48,
        256,
        [
            f"Nom: {data['beneficiary_name']}",
            f"Banque beneficiaire: {data['beneficiary_bank']}",
            f"IBAN: {data['beneficiary_iban']}",
            f"RIB: {data['beneficiary_rib']}",
        ],
    )

    _draw_block(canvas, 40, 410, 515, 170, "DETAILS VIREMENT")
    _draw_lines(
        canvas,
        48,
        438,
        [
            f"Motif: {data['reason']}",
            f"Montant: {format_mad(data['amount'])}",
            f"Frais: {format_mad(data['fees'])}",
            f"Total: {format_mad(data['total'])}",
            "Devise: MAD",
        ],
        line_height=20,
    )

    _draw_block(canvas, 40, 592, 515, 120, "EXECUTION")
    _draw_lines(
        canvas,
        48,
        620,
        [
            f"Date ordre: {data['order_date']}",
            f"Date execution: {data['execution_date']}",
            f"Statut: {data['status']}",
        ],
        line_height=20,
    )
