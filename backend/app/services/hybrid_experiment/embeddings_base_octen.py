"""
Base (Non-Fine-Tuned) Octen-0.6B Embeddings Engine
===================================================
Generates 1024-dimensional normalized dense vectors using the original,
unmodified base Octen-0.6B weights (non-fine-tuned) located in `backend/models/octen-0.6b`.
"""
from __future__ import annotations

import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModel

# backend/app/services/hybrid_experiment/embeddings_base_octen.py
# parent(1)=hybrid_experiment, parent(2)=services, parent(3)=app, parent(4)=backend
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
BASE_OCTEN_DIR = BACKEND_DIR / "models" / "octen-0.6b"
if not BASE_OCTEN_DIR.exists():
    BASE_OCTEN_DIR = BACKEND_DIR.parent / "backend" / "models" / "octen-0.6b"

_TOKENIZER_BASE = None
_MODEL_BASE = None
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class EmbeddingBaseOctenError(Exception):
    pass


def _load_base_octen_model():
    global _TOKENIZER_BASE, _MODEL_BASE

    if _MODEL_BASE is not None and _TOKENIZER_BASE is not None:
        return _TOKENIZER_BASE, _MODEL_BASE

    if not BASE_OCTEN_DIR.exists():
        raise EmbeddingBaseOctenError(f"Base Octen model directory not found at: {BASE_OCTEN_DIR}")

    try:
        print(f"[Embeddings Base Octen] Loading Base (Non-Fine-Tuned) Model from: {BASE_OCTEN_DIR.name} ({_DEVICE})...", flush=True)
        _TOKENIZER_BASE = AutoTokenizer.from_pretrained(str(BASE_OCTEN_DIR))
        _MODEL_BASE = AutoModel.from_pretrained(str(BASE_OCTEN_DIR))
        _MODEL_BASE.to(_DEVICE)
        _MODEL_BASE.eval()
        return _TOKENIZER_BASE, _MODEL_BASE
    except Exception as exc:
        raise EmbeddingBaseOctenError(f"Failed to load Base Octen model: {exc}") from exc


def get_embedding_base_octen(text: str) -> list[float]:
    """
    Generates a 1024-dimensional dense vector using the Base (Non-Fine-Tuned) Octen model.
    """
    cleaned = text.replace("\n", " ").strip()
    if not cleaned:
        raise EmbeddingBaseOctenError("Cannot generate embedding for empty text.")

    tokenizer, model = _load_base_octen_model()

    try:
        inputs = tokenizer(
            cleaned,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=4096,
        ).to(_DEVICE)

        with torch.no_grad():
            outputs = model(**inputs)
            emb = outputs.last_hidden_state[:, 0]
            normalized = torch.nn.functional.normalize(emb, p=2, dim=1)

        return normalized[0].cpu().tolist()

    except Exception as exc:
        raise EmbeddingBaseOctenError(f"Base Octen embedding generation failed: {exc}") from exc


def get_embeddings_batch_base_octen(
    texts: list[str],
    batch_size: int = 32,
) -> list[list[float]]:
    """
    Generates 1024-dimensional dense vectors in batches on GPU using Base Octen.
    """
    if not texts:
        return []

    tokenizer, model = _load_base_octen_model()
    all_embeddings: list[list[float]] = []

    cleaned_texts = [t.replace("\n", " ").strip() for t in texts]
    sanitized = [t if t else " " for t in cleaned_texts]

    try:
        for i in range(0, len(sanitized), batch_size):
            batch = sanitized[i : i + batch_size]
            inputs = tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=1536,
            ).to(_DEVICE)

            with torch.no_grad():
                outputs = model(**inputs)
                emb = outputs.last_hidden_state[:, 0]
                normalized = torch.nn.functional.normalize(emb, p=2, dim=1)

            all_embeddings.extend(normalized.cpu().tolist())

        return all_embeddings

    except Exception as exc:
        raise EmbeddingBaseOctenError(f"Base Octen batch embedding generation failed: {exc}") from exc
