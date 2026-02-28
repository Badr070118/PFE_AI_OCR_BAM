from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any


_MODEL_CACHE: dict[str, Any] = {"model": None, "loaded": False}


def _default_model_path() -> Path:
    env_path = (os.getenv("DOC_TYPE_MODEL_PATH") or "").strip()
    if env_path:
        return Path(env_path)
    # Repo root from services/ocr/app/document_router -> ../../../../
    return Path(__file__).resolve().parents[4] / "tools" / "doc_type_training" / "model.pkl"


def _load_model() -> Any | None:
    if _MODEL_CACHE["loaded"]:
        return _MODEL_CACHE["model"]

    model_path = _default_model_path()
    if not model_path.exists():
        _MODEL_CACHE["loaded"] = True
        _MODEL_CACHE["model"] = None
        return None

    try:
        with model_path.open("rb") as handle:
            model = pickle.load(handle)
    except Exception:
        model = None

    _MODEL_CACHE["loaded"] = True
    _MODEL_CACHE["model"] = model
    return model


def predict_with_optional_model(ocr_text: str) -> dict[str, Any] | None:
    model = _load_model()
    if model is None:
        return None

    try:
        # Expected payload shape:
        # {
        #   "vectorizer": fitted TfidfVectorizer,
        #   "classifier": fitted classifier with predict_proba,
        #   "labels": list[str]
        # }
        vectorizer = model.get("vectorizer")
        classifier = model.get("classifier")
        labels = model.get("labels")
        if vectorizer is None or classifier is None or not labels:
            return None

        vector = vectorizer.transform([ocr_text])
        probabilities = classifier.predict_proba(vector)[0]
        best_index = int(probabilities.argmax())
        return {
            "doc_type": str(labels[best_index]),
            "confidence": float(probabilities[best_index]),
        }
    except Exception:
        return None
