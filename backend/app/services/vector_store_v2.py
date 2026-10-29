import weaviate
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.query import Filter

from app.services.vector_store_v1 import get_weaviate_client

COLLECTION_NAME_V2 = "LegalDocumentChunk_V2"
STATUTE_COLLECTION_NAME_V2 = "GlobalStatuteChunk_V2"


def ensure_collection_v2_exists() -> None:
    """
    Creates the V2 tenant document chunk collection (1024-D) in Weaviate.
    """
    with get_weaviate_client() as client:
        if client.collections.exists(COLLECTION_NAME_V2):
            return

        client.collections.create(
            name=COLLECTION_NAME_V2,
            description="V2 Legal Document Chunks vectorized using local fine-tuned 1024-D model",
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="chunk_text", data_type=DataType.TEXT),
                Property(name="document_id", data_type=DataType.INT),
                Property(name="case_id", data_type=DataType.INT),
                Property(name="user_id", data_type=DataType.INT),
                Property(name="page_number", data_type=DataType.INT),
                Property(name="chunk_index", data_type=DataType.INT),
            ],
        )
        print(f"[VectorStore V2] Created collection '{COLLECTION_NAME_V2}' successfully.")


def ensure_statute_collection_v2_exists() -> None:
    """
    Creates the V2 global Indian Bare Acts collection (1024-D) in Weaviate.
    """
    with get_weaviate_client() as client:
        if client.collections.exists(STATUTE_COLLECTION_NAME_V2):
            return

        client.collections.create(
            name=STATUTE_COLLECTION_NAME_V2,
            description="V2 Global Indian Bare Acts vectorized using local fine-tuned 1024-D model",
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="chunk_text", data_type=DataType.TEXT),
                Property(name="pdf_name", data_type=DataType.TEXT),
                Property(name="page_number", data_type=DataType.INT),
                Property(name="chunk_index", data_type=DataType.INT),
            ],
        )
        print(f"[VectorStore V2] Created collection '{STATUTE_COLLECTION_NAME_V2}' successfully.")


def store_chunk_vector_v2(
    chunk_text: str,
    vector: list[float],
    document_id: int,
    user_id: int,
    page_number: int | None = None,
    chunk_index: int = 0,
    case_id: int | None = None,
) -> str:
    ensure_collection_v2_exists()

    with get_weaviate_client() as client:
        collection = client.collections.get(COLLECTION_NAME_V2)
        uuid = collection.data.insert(
            properties={
                "chunk_text": chunk_text,
                "document_id": document_id,
                "user_id": user_id,
                "page_number": page_number,
                "chunk_index": chunk_index,
                "case_id": case_id,
            },
            vector=vector,
        )
        return str(uuid)


def hybrid_search_statutes_v2(
    query_text: str,
    query_vector: list[float],
    target_pdf_names: list[str],
    alpha: float = 0.5,
    limit: int = 20,
) -> list[dict]:
    ensure_statute_collection_v2_exists()

    with get_weaviate_client() as client:
        collection = client.collections.get(STATUTE_COLLECTION_NAME_V2)

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
            limit=limit,
            filters=statute_filter,
            return_metadata=weaviate.classes.query.MetadataQuery(score=True),
        )

        results = []
        for obj in response.objects:
            results.append({
                "chunk_text": obj.properties.get("chunk_text", ""),
                "pdf_name": obj.properties.get("pdf_name", ""),
                "page_number": obj.properties.get("page_number", 1),
                "chunk_index": obj.properties.get("chunk_index", 0),
                "hybrid_score": obj.metadata.score if obj.metadata else 0.0,
            })
        return results


def hybrid_search_case_chunks_v2(
    query_text: str,
    query_vector: list[float],
    user_id: int,
    case_id: int | None = None,
    alpha: float = 0.5,
    limit: int = 10,
) -> list[dict]:
    ensure_collection_v2_exists()

    with get_weaviate_client() as client:
        collection = client.collections.get(COLLECTION_NAME_V2)

        user_filter = Filter.by_property("user_id").equal(user_id)
        if case_id is not None:
            combined_filter = user_filter & Filter.by_property("case_id").equal(case_id)
        else:
            combined_filter = user_filter

        response = collection.query.hybrid(
            query=query_text,
            vector=query_vector,
            alpha=alpha,
            limit=limit,
            filters=combined_filter,
            return_metadata=weaviate.classes.query.MetadataQuery(score=True),
        )

        results = []
        for obj in response.objects:
            results.append({
                "chunk_text": obj.properties.get("chunk_text", ""),
                "document_id": obj.properties.get("document_id"),
                "case_id": obj.properties.get("case_id"),
                "page_number": obj.properties.get("page_number", 1),
                "chunk_index": obj.properties.get("chunk_index", 0),
                "hybrid_score": obj.metadata.score if obj.metadata else 0.0,
            })
        return results
