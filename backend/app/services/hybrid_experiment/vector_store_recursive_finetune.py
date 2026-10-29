"""
Vector Store for Recursive+fine_tune Model Hybrid Pipeline (Testing / Evaluation Track)
=======================================================================================
Combines:
- V1 Chunking: IBM Docling Parser + LangChain RecursiveCharacterTextSplitter
- V2 Embeddings: Local GPU Fine-Tuned Octen-Embedding-0.6B (1024-D)

Collection Name: 'Recursive_FineTune_Model'
"""
from __future__ import annotations

import weaviate
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.query import Filter, MetadataQuery

from app.services.vector_store_v1 import get_weaviate_client

RECURSIVE_FINETUNE_COLLECTION_NAME = "Recursive_FineTune_Model"


def ensure_recursive_finetune_collection_exists() -> None:
    """
    Creates the 'Recursive_FineTune_Model' collection in Weaviate (1024-D vectors).
    """
    with get_weaviate_client() as client:
        if client.collections.exists(RECURSIVE_FINETUNE_COLLECTION_NAME):
            return

        client.collections.create(
            name=RECURSIVE_FINETUNE_COLLECTION_NAME,
            description="Recursive+fine_tune model: LangChain Recursive Character Chunking + Octen 1024-D Fine-Tuned Local Embeddings",
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="chunk_text", data_type=DataType.TEXT, description="Legal Markdown chunk text"),
                Property(name="pdf_name", data_type=DataType.TEXT, description="Source PDF name"),
                Property(name="page_number", data_type=DataType.INT, description="Source page number"),
                Property(name="chunk_index", data_type=DataType.INT, description="Sequential chunk index"),
                Property(name="heading", data_type=DataType.TEXT, description="Detected Markdown heading"),
            ],
        )
        print(f"[VectorStore] Created collection '{RECURSIVE_FINETUNE_COLLECTION_NAME}' successfully.")


def hybrid_search_recursive_finetune(
    query_text: str,
    query_vector: list[float],
    target_pdf_names: list[str] | None = None,
    alpha: float = 0.5,
    limit: int = 20,
) -> list[dict]:
    """
    Performs hybrid dense (Octen 1024-D) + sparse BM25 search over 'Recursive_FineTune_Model'.
    """
    ensure_recursive_finetune_collection_exists()

    with get_weaviate_client() as client:
        collection = client.collections.get(RECURSIVE_FINETUNE_COLLECTION_NAME)

        statute_filter = None
        if target_pdf_names:
            if len(target_pdf_names) == 1:
                statute_filter = Filter.by_property("pdf_name").equal(target_pdf_names[0])
            else:
                statute_filter = Filter.by_property("pdf_name").contains_any(target_pdf_names)

        response = collection.query.hybrid(
            query=query_text,
            vector=query_vector,
            alpha=alpha,
            filters=statute_filter,
            limit=limit,
            return_metadata=MetadataQuery(score=True),
        )

        results: list[dict] = []
        for obj in response.objects:
            results.append({
                "chunk_text": obj.properties.get("chunk_text"),
                "pdf_name": obj.properties.get("pdf_name"),
                "page_number": obj.properties.get("page_number"),
                "chunk_index": obj.properties.get("chunk_index"),
                "heading": obj.properties.get("heading"),
                "score": obj.metadata.score if obj.metadata else None,
            })

        return results
