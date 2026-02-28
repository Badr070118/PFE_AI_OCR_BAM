from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Dict, Tuple


if __package__ in (None, ""):
    current_dir = Path(__file__).resolve().parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))

from data import (
    generate_invoice_data,
    generate_receipt_data,
    generate_statement_data,
    generate_transfer_data,
)
from render import render_document
from templates import draw_bank_statement, draw_invoice, draw_payment_receipt, draw_wire_transfer


DataFactory = Callable[[int], Dict]
TemplateFunc = Callable[..., None]


DOC_CONFIG: Tuple[Tuple[str, str, DataFactory, TemplateFunc], ...] = (
    ("invoices", "invoice", generate_invoice_data, draw_invoice),
    ("bank_statements", "statement", generate_statement_data, draw_bank_statement),
    ("payment_receipts", "receipt", generate_receipt_data, draw_payment_receipt),
    ("wire_transfers", "transfer", generate_transfer_data, draw_wire_transfer),
)


def generate_all_documents(output_root: Path, per_type_count: int = 5) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    for folder, file_prefix, data_factory, template in DOC_CONFIG:
        target_dir = output_root / folder
        target_dir.mkdir(parents=True, exist_ok=True)

        for index in range(1, per_type_count + 1):
            data = data_factory(index)
            file_stem = f"{file_prefix}_{index:02d}"
            pdf_path = target_dir / f"{file_stem}.pdf"
            png_path = target_dir / f"{file_stem}.png"
            render_document(pdf_path, png_path, template, data, dpi=300)
            print(f"[OK] {pdf_path}")
            print(f"[OK] {png_path}")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    output_root = repo_root / "test_ocr_docs"
    print(f"Generation des documents OCR dans: {output_root}")
    try:
        generate_all_documents(output_root=output_root, per_type_count=5)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
        return 1
    print("Generation terminee.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
