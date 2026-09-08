from openai import OpenAI
from app.core.config import get_settings

class EmbeddingError(Exception):
    pass

def _get_openai_client()->tuple[OpenAI, str]:

    settings = get_settings()

    if not settings.openai_api_key or not settings.openai_api_key.strip():
        raise EmbeddingError(
            "OPENAI_API_KEY is not configured in .env. Embedding generation requires an active API key."
        )

    client = OpenAI(api_key=settings.openai_api_key)
    model = settings.openai_embedding_model or "text-embedding-3-small"
    return client, model


def get_embedding(text: str) -> list[float]:

    cleaned_text = text.replace("\n"," ").strip()
    if not cleaned_text:
        raise EmbeddingError("Cannot generate embedding for empty text.")

    client, model = _get_openai_client()

    try:
        response = client.embeddings.create(
            input=cleaned_text,
            model=model,
        )
        return response.data[0].embedding

    except Exception as exc:
        raise EmbeddingError(f"Failed to generate embeddings :: {exc}") from exc


def get_embeddings_batch(
        texts: list[str],
        batch_size: int = 64,
) -> list[list[float]]:

    if not texts:
        return []

    cleaned_texts =  [t.replace("\n", " ").strip() for t in texts]

    sanitized_texts = [t if t else " " for t in cleaned_texts]

    client, model = _get_openai_client()
    all_embeddings: list[list[float]] = []

    try:
        for i in range(0, len(sanitized_texts), batch_size):
            chunks = sanitized_texts[i : i + batch_size]
            response = client.embeddings.create(
                input=chunks,
                model=model,
            )

        batch_vectors = [item.embedding for item in response.data]
        all_embeddings.extend(batch_vectors)

        return all_embeddings

    except Exception as exc:
        raise EmbeddingError(f"Failed to generate batch embeddings: {exc}") from exc


def get_embedding_dimension() -> int:

    settings = get_settings()
    model = settings.openai_embedding_model or "text-embedding-3-small"
    if "large" in model:
        return 3072
    return 1536