from __future__ import annotations

from typing import Any

from app.document_router.features import extract_features
from app.document_router.ml_model import predict_with_optional_model
from app.document_router.rules import (
    DOC_TYPES,
    KEYWORD_WEIGHTS,
    MIN_ABSOLUTE_SCORE,
    UNKNOWN_DOC_TYPE,
    UNKNOWN_THRESHOLD,
)


def _safe_doc_type(value: str | None) -> str:
    if value in DOC_TYPES:
        return str(value)
    return UNKNOWN_DOC_TYPE


def _build_unknown(reasons: list[str]) -> dict[str, Any]:
    return {
        "doc_type": UNKNOWN_DOC_TYPE,
        "confidence": 0.0,
        "reasons": reasons[:6],
    }


def _add_score(
    scores: dict[str, float],
    reasons: dict[str, list[str]],
    doc_type: str,
    value: float,
    reason: str,
) -> None:
    if doc_type not in scores:
        return
    scores[doc_type] += value
    if reason not in reasons[doc_type]:
        reasons[doc_type].append(reason)


def _compute_confidence(scores: dict[str, float], top_type: str) -> float:
    positive_scores = {key: max(value, 0.0) for key, value in scores.items()}
    total = sum(positive_scores.values())
    if total <= 0.0:
        return 0.0

    ordered = sorted(positive_scores.items(), key=lambda item: item[1], reverse=True)
    top_score = positive_scores[top_type]
    second_score = ordered[1][1] if len(ordered) > 1 else 0.0

    relative = top_score / total
    margin = (top_score - second_score) / max(top_score, 1e-6)
    strength = min(1.0, top_score / 8.0)
    confidence = (0.55 * relative) + (0.30 * margin) + (0.15 * strength)
    return max(0.0, min(1.0, confidence))


def detect_document_type(ocr_text: str, ocr_lines: list[str] | None = None) -> dict[str, Any]:
    raw_text = (ocr_text or "").strip()
    if not raw_text:
        return _build_unknown(["texte OCR vide"])

    features = extract_features(raw_text, ocr_lines)

    scores: dict[str, float] = {doc_type: 0.0 for doc_type in DOC_TYPES}
    reasons: dict[str, list[str]] = {doc_type: [] for doc_type in DOC_TYPES}

    # 1) Keyword scoring.
    for doc_type in DOC_TYPES:
        hits = features["keyword_hits"][doc_type]
        for keyword, count in hits.items():
            weight = KEYWORD_WEIGHTS[doc_type][keyword]
            capped_count = min(count, 3)
            _add_score(
                scores,
                reasons,
                doc_type,
                weight * capped_count,
                f"mot-cle '{keyword}' x{count}",
            )

    # 2) Regex scoring.
    for doc_type in DOC_TYPES:
        regex_hits = features["regex_hits"][doc_type]
        for hit in regex_hits:
            capped_count = min(int(hit["count"]), 3)
            score_boost = 0.6 * capped_count
            _add_score(scores, reasons, doc_type, score_boost, f"{hit['reason']} x{hit['count']}")

    # 3) Structural heuristics.
    if features["date_line_count"] >= 6 and features["transaction_line_count"] >= 4:
        _add_score(
            scores,
            reasons,
            "bank_statement",
            1.8,
            "beaucoup de lignes type transaction (dates + montants)",
        )

    if features["multi_amount_lines"] >= 3 and features["amount_line_count"] >= 6:
        _add_score(
            scores,
            reasons,
            "invoice",
            1.0,
            "structure tabulaire montants compatible facture",
        )
        _add_score(
            scores,
            reasons,
            "bank_statement",
            0.8,
            "structure tabulaire montants compatible releve",
        )

    has_iban = any("mot-cle 'iban'" in reason for reason in reasons["wire_transfer"])
    has_beneficiary = any("beneficiaire" in reason for reason in reasons["wire_transfer"])
    if has_iban and has_beneficiary:
        _add_score(scores, reasons, "wire_transfer", 1.2, "couple IBAN + beneficiaire detecte")

    has_ht = any("mot-cle 'total ht'" in reason for reason in reasons["invoice"])
    has_tva = any("mot-cle 'tva'" in reason for reason in reasons["invoice"])
    has_ttc = any("mot-cle 'ttc'" in reason for reason in reasons["invoice"])
    if has_ht and has_tva and has_ttc:
        _add_score(scores, reasons, "invoice", 1.4, "triplet HT/TVA/TTC detecte")

    has_channel = any("mot-cle 'canal'" in reason for reason in reasons["payment_receipt"])
    has_txn = any("txn-" in reason for reason in reasons["payment_receipt"])
    if has_channel and has_txn:
        _add_score(scores, reasons, "payment_receipt", 1.0, "canal + reference transaction detectes")

    # 4) Optional ML model blend (if model.pkl exists).
    ml_prediction = predict_with_optional_model(raw_text)
    if ml_prediction:
        ml_doc_type = _safe_doc_type(ml_prediction.get("doc_type"))
        ml_conf = float(ml_prediction.get("confidence", 0.0))
        if ml_doc_type != UNKNOWN_DOC_TYPE and ml_conf > 0.0:
            _add_score(
                scores,
                reasons,
                ml_doc_type,
                min(2.0, max(0.0, ml_conf * 2.0)),
                f"modele ML suggere {ml_doc_type} ({ml_conf:.2f})",
            )

    top_doc_type = max(scores, key=scores.get)
    top_score = scores[top_doc_type]
    confidence = _compute_confidence(scores, top_doc_type)

    if top_score < MIN_ABSOLUTE_SCORE or confidence < UNKNOWN_THRESHOLD:
        fallback_reasons = reasons[top_doc_type][:3]
        fallback_reasons.append(
            f"score/confiance insuffisants ({top_score:.2f}, {confidence:.2f})"
        )
        return {
            "doc_type": UNKNOWN_DOC_TYPE,
            "confidence": round(confidence, 4),
            "reasons": fallback_reasons[:6],
        }

    return {
        "doc_type": top_doc_type,
        "confidence": round(confidence, 4),
        "reasons": reasons[top_doc_type][:6],
    }


def choose_extractor_name(doc_type: str) -> str:
    if doc_type == "invoice":
        return "invoice_table"
    if doc_type in {"bank_statement", "payment_receipt", "wire_transfer"}:
        return "generic_text_json"
    return "raw_text_only"
