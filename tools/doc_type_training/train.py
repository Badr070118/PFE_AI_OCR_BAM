from __future__ import annotations

import pickle
import sys
from pathlib import Path

try:
    import fitz  # type: ignore
except ImportError:
    fitz = None


LABEL_MAP = {
    "invoices": "invoice",
    "bank_statements": "bank_statement",
    "payment_receipts": "payment_receipt",
    "wire_transfers": "wire_transfer",
}


def _extract_pdf_text(pdf_path: Path) -> str:
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) is required to read PDF files.")
    document = fitz.open(pdf_path)
    try:
        return "\n".join(page.get_text("text") for page in document).strip()
    finally:
        document.close()


def _collect_samples(dataset_root: Path) -> tuple[list[str], list[str]]:
    texts: list[str] = []
    labels: list[str] = []

    for folder_name, label in LABEL_MAP.items():
        folder = dataset_root / folder_name
        if not folder.exists():
            continue
        for pdf_path in sorted(folder.glob("*.pdf")):
            txt_path = pdf_path.with_suffix(".txt")
            if txt_path.exists():
                text = txt_path.read_text(encoding="utf-8", errors="ignore").strip()
            else:
                text = _extract_pdf_text(pdf_path)
            if text:
                texts.append(text)
                labels.append(label)

    return texts, labels


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    dataset_root = repo_root / "test_ocr_docs"
    model_path = Path(__file__).resolve().parent / "model.pkl"

    if not dataset_root.exists():
        print(f"[ERROR] Dataset not found: {dataset_root}")
        return 1

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
    except ImportError:
        print(
            "[ERROR] scikit-learn is required.\n"
            "Install with: python -m pip install scikit-learn"
        )
        return 1

    texts, labels = _collect_samples(dataset_root)
    if len(texts) < 8:
        print("[ERROR] Not enough samples to train. Need at least 8 OCR texts.")
        return 1

    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=0.25,
        random_state=42,
        stratify=labels,
    )

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_features=12000,
    )
    x_train_vec = vectorizer.fit_transform(x_train)
    x_test_vec = vectorizer.transform(x_test)

    classifier = LogisticRegression(max_iter=2000)
    classifier.fit(x_train_vec, y_train)
    accuracy = classifier.score(x_test_vec, y_test)

    labels_sorted = sorted(set(labels))
    payload = {
        "vectorizer": vectorizer,
        "classifier": classifier,
        "labels": labels_sorted,
        "meta": {
            "accuracy": float(accuracy),
            "sample_count": len(texts),
        },
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as handle:
        pickle.dump(payload, handle)

    print(f"[OK] Model saved: {model_path}")
    print(f"[INFO] Validation accuracy: {accuracy:.4f}")
    print(f"[INFO] Samples: {len(texts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
