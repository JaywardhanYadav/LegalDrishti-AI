import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FINETUNED_OCTEN_DIR = BASE_DIR / "models" / "octen-0.6b-finetuned"
BASE_OCTEN_DIR = BASE_DIR / "models" / "octen-0.6b"

_TOKENIZER_V2 = None
_MODEL_V2 = None
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
_ACTIVE_MODEL_PATH = None


class EmbeddingV2Error(Exception):
    pass


def _get_active_model_dir() -> Path:
    if FINETUNED_OCTEN_DIR.exists() and (FINETUNED_OCTEN_DIR / "model.safetensors").exists():
        return FINETUNED_OCTEN_DIR
    elif BASE_OCTEN_DIR.exists():
        return BASE_OCTEN_DIR
    else:
        raise EmbeddingV2Error(
            f"Neither fine-tuned nor base Octen model found in {BASE_OCTEN_DIR}. "
            "Please ensure weights are downloaded."
        )


def _load_v2_model():
    global _TOKENIZER_V2, _MODEL_V2, _ACTIVE_MODEL_PATH

    model_dir = _get_active_model_dir()

    # If already loaded and path hasn't changed to fine-tuned, reuse
    if _MODEL_V2 is not None and _TOKENIZER_V2 is not None and _ACTIVE_MODEL_PATH == model_dir:
        return _TOKENIZER_V2, _MODEL_V2

    try:
        print(f"[Embeddings V2] Loading 1024-D Local Model from: {model_dir.name} ({_DEVICE})...")
        _TOKENIZER_V2 = AutoTokenizer.from_pretrained(str(model_dir))
        _MODEL_V2 = AutoModel.from_pretrained(str(model_dir))
        _MODEL_V2.to(_DEVICE)
        _MODEL_V2.eval()
        _ACTIVE_MODEL_PATH = model_dir
        return _TOKENIZER_V2, _MODEL_V2
    except Exception as exc:
        raise EmbeddingV2Error(f"Failed to load V2 local model: {exc}") from exc


def get_embedding_v2(text: str) -> list[float]:
    """
    Generates a 1024-dimensional normalized dense vector for query search
    using the V2 fine-tuned/local Octen-0.6B model.
    """
    cleaned = text.replace("\n", " ").strip()
    if not cleaned:
        raise EmbeddingV2Error("Cannot generate embedding for empty text.")

    tokenizer, model = _load_v2_model()

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
        raise EmbeddingV2Error(f"V2 embedding generation failed: {exc}") from exc


def get_embeddings_batch_v2(
    texts: list[str],
    batch_size: int = 16,
) -> list[list[float]]:
    """
    Generates 1024-dimensional normalized dense vectors in batches
    for document chunks in V2.
    """
    if not texts:
        return []

    tokenizer, model = _load_v2_model()
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
        raise EmbeddingV2Error(f"V2 batch embedding generation failed: {exc}") from exc


def get_embedding_dimension_v2() -> int:
    """
    Returns vector dimension for V2 (1024).
    """
    return 1024
