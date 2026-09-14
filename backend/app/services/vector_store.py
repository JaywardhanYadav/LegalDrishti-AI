from collections.abc import Generator
from contextlib import contextmanager

import weaviate
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.query import Filter, MetadataQuery

COLLECTION_NAME = "LegalDocumentChunk"


@contextmanager
def get_weaviate_client() -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.connect_to_local(
        host="127.0.0.1",
        port=8080,
        grpc_port=50051,
    )
    try:
        yield client
    finally:
        client.close()


def is_weaviate_ready() -> bool:
    try:
        with get_weaviate_client() as client:
            return bool(client.is_ready())
    except Exception:
        return False


def ensure_collection_exists() -> None:
    with get_weaviate_client() as client:
        if client.collections.exists(COLLECTION_NAME):
            return

        client.collections.create(
            name=COLLECTION_NAME,
            description="Vectorized legal document chunks for semantic search and citation RAG",
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(
                    name="chunk_text",
                    data_type=DataType.TEXT,
                    description="Legal text content of the chunk",
                ),
                Property(
                    name="document_id",
                    data_type=DataType.INT,
                    description="Parent document database ID",
                ),
                Property(
                    name="case_id",
                    data_type=DataType.INT,
                    description="Linked case ID if applicable",
                ),
                Property(
                    name="user_id",
                    data_type=DataType.INT,
                    description="Owner user ID for tenant isolation",
                ),
                Property(
                    name="page_number",
                    data_type=DataType.INT,
                    description="Source page number for court citations",
                ),
                Property(
                    name="chunk_index",
                    data_type=DataType.INT,
                    description="Sequential index of chunk in document",
                ),
            ],
        )


def store_chunk_vector(
    chunk_text: str,
    vector: list[float],
    document_id: int,
    user_id: int,
    page_number: int = 1,
    chunk_index: int = 0,
    case_id: int | None = None,
) -> str:
    ensure_collection_exists()

    with get_weaviate_client() as client:
        collection = client.collections.get(COLLECTION_NAME)

        properties = {
            "chunk_text": chunk_text,
            "document_id": document_id,
            "case_id": case_id,
            "user_id": user_id,
            "page_number": page_number,
            "chunk_index": chunk_index,
        }

        uuid_val = collection.data.insert(
            properties=properties,
            vector=vector,
        )

        return str(uuid_val)


def search_similar_chunks(
    query_vector: list[float],
    user_id: int,
    case_id: int | None = None,
    limit: int = 5,
) -> list[dict]:
    ensure_collection_exists()

    with get_weaviate_client() as client:
        collection = client.collections.get(COLLECTION_NAME)

        user_filter = Filter.by_property("user_id").equal(user_id)

        if case_id is not None:
            combined_filter = (
                user_filter & Filter.by_property("case_id").equal(case_id)
            )
        else:
            combined_filter = user_filter

        response = collection.query.near_vector(
            near_vector=query_vector,
            filters=combined_filter,
            limit=limit,
            return_metadata=MetadataQuery(distance=True),
        )

        results: list[dict] = []

        for obj in response.objects:
            results.append(
                {
                    "chunk_text": obj.properties.get("chunk_text"),
                    "document_id": obj.properties.get("document_id"),
                    "case_id": obj.properties.get("case_id"),
                    "page_number": obj.properties.get("page_number"),
                    "chunk_index": obj.properties.get("chunk_index"),
                    "distance": (
                        obj.metadata.distance
                        if obj.metadata
                        else None
                    ),
                }
            )

        return results


def hybrid_search_chunks(
    query_text: str,
    query_vector: list[float],
    user_id: int,
    case_id: int | None = None,
    alpha: float = 0.5,
    limit: int = 5,
) -> list[dict]:
    """
    Performs Hybrid Search (BM25 keyword + Dense Vector) in Weaviate.
    alpha=0.5 balances exact keyword matches (sections, names) with conceptual meaning.
    Strictly enforces tenant isolation via user_id.
    """
    ensure_collection_exists()
    with get_weaviate_client() as client:
        collection = client.collections.get(COLLECTION_NAME)
        user_filter = Filter.by_property("user_id").equal(user_id)
        if case_id is not None:
            combined_filter = user_filter & Filter.by_property("case_id").equal(case_id)
        else:
            combined_filter = user_filter
        response = collection.query.hybrid(
            query=query_text,
            vector=query_vector,
            alpha=alpha,
            filters=combined_filter,
            limit=limit,
            return_metadata=MetadataQuery(score=True),
        )
        results: list[dict] = []
        for obj in response.objects:
            results.append({
                "chunk_text": obj.properties.get("chunk_text"),
                "document_id": obj.properties.get("document_id"),
                "case_id": obj.properties.get("case_id"),
                "page_number": obj.properties.get("page_number"),
                "chunk_index": obj.properties.get("chunk_index"),
                "score": obj.metadata.score if obj.metadata else None,
            })
        return results


def delete_chunks_by_document(document_id: int) -> int:
    """Permanently deletes all vector embeddings and chunks for a document in Weaviate."""
    ensure_collection_exists()
    try:
        with get_weaviate_client() as client:
            collection = client.collections.get(COLLECTION_NAME)
            res = collection.data.delete_many(
                where=Filter.by_property("document_id").equal(document_id)
            )
            return getattr(res, "matches", 0) or 0
    except Exception as e:
        print(f"[Weaviate Vector Deletion Warning] Failed to delete chunks for document {document_id}: {e}")
        return 0


def delete_chunks_by_case(case_id: int) -> int:
    """Permanently deletes all vector embeddings and chunks for a case/vault in Weaviate."""
    ensure_collection_exists()
    try:
        with get_weaviate_client() as client:
            collection = client.collections.get(COLLECTION_NAME)
            res = collection.data.delete_many(
                where=Filter.by_property("case_id").equal(case_id)
            )
            return getattr(res, "matches", 0) or 0
    except Exception as e:
        print(f"[Weaviate Vector Deletion Warning] Failed to delete chunks for case {case_id}: {e}")
        return 0


def delete_all_chunks_by_user(user_id: int) -> int:
    """Permanently deletes all vector embeddings and chunks for a user in Weaviate."""
    ensure_collection_exists()
    try:
        with get_weaviate_client() as client:
            collection = client.collections.get(COLLECTION_NAME)
            res = collection.data.delete_many(
                where=Filter.by_property("user_id").equal(user_id)
            )
            return getattr(res, "matches", 0) or 0
    except Exception as e:
        print(f"[Weaviate Vector Deletion Warning] Failed to delete chunks for user {user_id}: {e}")
        return 0


STATUTE_COLLECTION_NAME = "GlobalStatuteChunk"


def ensure_statute_collection_exists() -> None:
    with get_weaviate_client() as client:
        if client.collections.exists(STATUTE_COLLECTION_NAME):
            return

        client.collections.create(
            name=STATUTE_COLLECTION_NAME,
            description="Global Indian Bare Acts and Legal Commentaries for statutory grounding",
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(
                    name="chunk_text",
                    data_type=DataType.TEXT,
                    description="Statutory text content of the chunk",
                ),
                Property(
                    name="pdf_name",
                    data_type=DataType.TEXT,
                    description="Name of the source PDF volume",
                ),
                Property(
                    name="page_number",
                    data_type=DataType.INT,
                    description="Source page number for statutory citation",
                ),
                Property(
                    name="chunk_index",
                    data_type=DataType.INT,
                    description="Sequential chunk index",
                ),
            ],
        )
        print(f"[VectorStore] Created collection '{STATUTE_COLLECTION_NAME}' successfully.")


def hybrid_search_statutes(
    query_text: str,
    query_vector: list[float],
    target_pdf_names: list[str],
    alpha: float = 0.5,
    limit: int = 20,
) -> list[dict]:
    ensure_statute_collection_exists()

    with get_weaviate_client() as client:
        collection = client.collections.get(STATUTE_COLLECTION_NAME)

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
                "score": obj.metadata.score if obj.metadata else None,
            })

        return results