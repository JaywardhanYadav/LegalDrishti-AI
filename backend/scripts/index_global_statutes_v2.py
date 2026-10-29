import sys
import time
import asyncio
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.vector_store_v2 import (
    get_weaviate_client,
    ensure_statute_collection_v2_exists,
    STATUTE_COLLECTION_NAME_V2,
)
from app.services.embeddings_v2 import get_embeddings_batch_v2
from weaviate.classes.data import DataObject
from weaviate.classes.query import Filter

LEGAL_PDFS_DIR = BASE_DIR.parent / "Legal Pdfs"

from app.services.chunking_v2 import (
    parse_and_chunk_document_v2,
    is_statutory_text,
)


def get_indexed_chunk_count_v2(pdf_name: str) -> int:
    with get_weaviate_client() as client:
        collection = client.collections.get(STATUTE_COLLECTION_NAME_V2)
        res = collection.aggregate.over_all(
            filters=Filter.by_property("pdf_name").equal(pdf_name),
            total_count=True,
        )
        return res.total_count or 0


def delete_pdf_chunks_v2(pdf_name: str) -> None:
    with get_weaviate_client() as client:
        collection = client.collections.get(STATUTE_COLLECTION_NAME_V2)
        collection.data.delete_many(
            where=Filter.by_property("pdf_name").equal(pdf_name)
        )


async def index_pdf_file_v2(pdf_path: Path, max_pages: int = 150):
    pdf_name = pdf_path.name
    chunks = parse_and_chunk_document_v2(pdf_path, max_pages=max_pages)
    if not chunks:
        print(f"  --> Warning: No valid chunks extracted from '{pdf_name}'.", flush=True)
        return

    all_chunks: list[dict] = []
    for c in chunks:
        all_chunks.append({
            "chunk_text": c["chunk_text"],
            "pdf_name": pdf_name,
            "page_number": c["page_number"],
            "chunk_index": c["chunk_index"],
        })

    delete_pdf_chunks_v2(pdf_name)

    print(f"  --> Ingesting {len(all_chunks)} chunks into V2 Weaviate ({STATUTE_COLLECTION_NAME_V2}) via 1024-D Local Model...", flush=True)
    batch_size = 16
    total_chunks = len(all_chunks)

    with get_weaviate_client() as client:
        collection = client.collections.get(STATUTE_COLLECTION_NAME_V2)

        for i in range(0, total_chunks, batch_size):
            chunk_slice = all_chunks[i : i + batch_size]
            texts = [c["chunk_text"] for c in chunk_slice]

            vectors = get_embeddings_batch_v2(texts)

            data_objects = []
            for j, c in enumerate(chunk_slice):
                data_objects.append(
                    DataObject(
                        properties={
                            "chunk_text": c["chunk_text"],
                            "pdf_name": c["pdf_name"],
                            "page_number": c["page_number"],
                            "chunk_index": c["chunk_index"],
                        },
                        vector=vectors[j],
                    )
                )

            collection.data.insert_many(data_objects)
            print(f"      [V2 Indexed {min(i + batch_size, total_chunks)}/{total_chunks} chunks]", flush=True)

    print(f"  --> [Complete] '{pdf_name}' fully indexed in V2 collection!", flush=True)


async def main():
    print("=" * 60, flush=True)
    print("  LegalDrishti AI - V2 Bare Act Global Indexing Engine", flush=True)
    print("  (Local 1024-D Fine-Tuned Embeddings -> GlobalStatuteChunk_V2)", flush=True)
    print("=" * 60, flush=True)

    ensure_statute_collection_v2_exists()

    pdf_files = sorted(list(LEGAL_PDFS_DIR.glob("*.pdf")))
    print(f"\nDiscovered {len(pdf_files)} Bare Act PDFs in '{LEGAL_PDFS_DIR}'\n", flush=True)

    for idx, pdf in enumerate(pdf_files, start=1):
        print(f"[{idx}/{len(pdf_files)}] Processing {pdf.name}...", flush=True)
        try:
            await index_pdf_file_v2(pdf)
        except Exception as exc:
            print(f"  [ERROR] Failed to index {pdf.name} in V2: {exc}", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("  [SUCCESS] All Bare Acts Indexed in V2 Collection!", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
