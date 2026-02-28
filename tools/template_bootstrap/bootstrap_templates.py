from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
SERVICE_OCR_DIR = ROOT_DIR / "services" / "ocr"
if str(SERVICE_OCR_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_OCR_DIR))

from app.structured_extraction import detect_pdf_kind, extract_native_pdf, extract_scanned
from app.template_engine.registry import get_template
from app.template_engine.schemas import (
    REQUIRED_FIELDS_BY_DOC_TYPE,
    TEMPLATE_FILE_BY_DOC_TYPE,
    schema_for,
)
from app.template_engine.utils import normalize_text, split_text_lines


DOC_TYPE_TO_DIR = {
    "invoice": "invoices",
    "bank_statement": "bank_statements",
    "payment_receipt": "payment_receipts",
    "wire_transfer": "wire_transfers",
}

STRONG_KEYWORDS = {
    "facture",
    "releve",
    "compte",
    "payeur",
    "beneficiaire",
    "montant",
    "tva",
    "ttc",
    "solde",
    "debit",
    "credit",
    "virement",
    "reference",
    "transaction",
    "iban",
}


def _looks_like_anchor(line: str) -> bool:
    text = line.strip()
    if not text:
        return False
    alpha = [ch for ch in text if ch.isalpha()]
    uppercase_ratio = (sum(1 for ch in alpha if ch.isupper()) / len(alpha)) if alpha else 0.0
    norm = normalize_text(text)
    if uppercase_ratio >= 0.8 and len(text) <= 60:
        return True
    if text.endswith(":") or " : " in text:
        return True
    if any(keyword in norm for keyword in STRONG_KEYWORDS):
        return True
    return False


def _anchor_name(line: str) -> str:
    clean = line.strip()
    if ":" in clean:
        clean = clean.split(":", 1)[0]
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        kind = detect_pdf_kind(str(path))
        if kind.get("kind") == "native":
            payload = extract_native_pdf(str(path))
        else:
            payload = extract_scanned(str(path))
        return str(payload.get("raw_text", "") or "")
    if suffix in {".png", ".jpg", ".jpeg"}:
        payload = extract_scanned(str(path))
        return str(payload.get("raw_text", "") or "")
    return ""


def _build_template(doc_type: str, labels: list[str]) -> dict[str, Any]:
    base = get_template(doc_type) or {}
    return {
        "doc_type": doc_type,
        "template_file": TEMPLATE_FILE_BY_DOC_TYPE.get(doc_type, ""),
        "anchors": {
            "bootstrap_common_labels": labels,
        },
        "schema": schema_for(doc_type),
        "required_fields": REQUIRED_FIELDS_BY_DOC_TYPE.get(doc_type, []),
        "fields_rules": base.get("fields_rules", {}),
    }


def bootstrap_templates(
    *,
    dataset_dir: Path,
    output_dir: Path,
    max_docs_per_type: int = 5,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for doc_type, folder_name in DOC_TYPE_TO_DIR.items():
        folder = dataset_dir / folder_name
        files = sorted(folder.glob("*.pdf"))[:max_docs_per_type]
        if not files:
            files = sorted(folder.glob("*.png"))[:max_docs_per_type]
        if not files:
            continue

        per_doc_labels: list[set[str]] = []
        for file_path in files:
            text = _extract_text_from_file(file_path)
            labels = {
                _anchor_name(line)
                for line in split_text_lines(text)
                if _looks_like_anchor(line)
            }
            per_doc_labels.append({label for label in labels if label})

        threshold = max(1, math.ceil(0.6 * len(per_doc_labels)))
        counter: Counter[str] = Counter()
        for labels in per_doc_labels:
            counter.update(labels)

        common_labels = sorted(
            label for label, count in counter.items() if count >= threshold
        )

        template = _build_template(doc_type, common_labels)
        output_name = TEMPLATE_FILE_BY_DOC_TYPE.get(doc_type)
        if not output_name:
            continue
        (output_dir / output_name).write_text(
            json.dumps(template, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[bootstrap] {doc_type}: {len(common_labels)} anchors -> {output_name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap template anchors from test_ocr_docs dataset."
    )
    parser.add_argument(
        "--dataset-dir",
        default=str(ROOT_DIR / "test_ocr_docs"),
        help="Path to test_ocr_docs root directory.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(
            ROOT_DIR / "services" / "ocr" / "app" / "template_engine" / "templates_generated"
        ),
        help="Output directory for generated template JSON files.",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=5,
        help="Maximum files per doc type.",
    )
    args = parser.parse_args()

    bootstrap_templates(
        dataset_dir=Path(args.dataset_dir),
        output_dir=Path(args.output_dir),
        max_docs_per_type=max(1, args.max_docs),
    )


if __name__ == "__main__":
    main()

