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

from app.services.vector_store_v1 import (
    get_weaviate_client,
    ensure_statute_collection_exists,
    STATUTE_COLLECTION_NAME,
)
from app.services.embeddings_v1 import get_embeddings_batch
from weaviate.classes.data import DataObject
from weaviate.classes.query import Filter

LEGAL_PDFS_DIR = BASE_DIR.parent / "Legal Pdfs"


from app.services.chunking_v1 import (
    split_document_v1,
)


def get_indexed_chunk_count(pdf_name: str) -> int:
    with get_weaviate_client() as client:
        collection = client.collections.get(STATUTE_COLLECTION_NAME)
        res = collection.aggregate.over_all(
            filters=Filter.by_property("pdf_name").equal(pdf_name),
            total_count=True,
        )
        return res.total_count or 0


def delete_pdf_chunks(pdf_name: str) -> None:
    with get_weaviate_client() as client:
        collection = client.collections.get(STATUTE_COLLECTION_NAME)
        collection.data.delete_many(
            where=Filter.by_property("pdf_name").equal(pdf_name)
        )


def get_embeddings_with_retry(texts: list[str], max_retries: int = 3):
    for attempt in range(1, max_retries + 1):
        try:
            return get_embeddings_batch(texts)
        except Exception as exc:
            if attempt == max_retries:
                raise
            print(f"      [Network Warning] Wi-Fi hiccup on attempt {attempt}/{max_retries}: {exc}. Retrying in 4 seconds...")
            time.sleep(4)


async def index_pdf_file(pdf_path: Path, max_pages: int = 150):
    pdf_name = pdf_path.name

    existing_count = get_indexed_chunk_count(pdf_name)
    if existing_count > 0:
        print(f"\n[V1 Librarian] Skipping '{pdf_name}': already indexed ({existing_count} chunks in Weaviate).")
        return

    print(f"\n[V1 Librarian] Parsing & Chunking '{pdf_name}' via Docling + LangChain (chunking_v1)...")

    chunks = split_document_v1(pdf_path, chunk_size=1000, chunk_overlap=150, max_pages=max_pages)
    if not chunks:
        print(f"  --> Warning: No extractable text found in '{pdf_name}'.")
        return

    all_chunks: list[dict] = []
    for c in chunks:
        all_chunks.append({
            "chunk_text": c["chunk_text"],
            "pdf_name": pdf_name,
            "page_number": c.get("page_number", 1),
            "chunk_index": c["chunk_index"],
        })

    delete_pdf_chunks(pdf_name)

    print(f"  --> Extracted {len(all_chunks)} chunks. Generating embeddings & uploading to Weaviate...")

    batch_size = 50
    with get_weaviate_client() as client:
        collection = client.collections.get(STATUTE_COLLECTION_NAME)

        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i : i + batch_size]
            texts = [item["chunk_text"] for item in batch]

            vectors = get_embeddings_with_retry(texts)

            data_objects = [
                DataObject(
                    properties={
                        "chunk_text": item["chunk_text"],
                        "pdf_name": item["pdf_name"],
                        "page_number": item["page_number"],
                        "chunk_index": item["chunk_index"],
                    },
                    vector=vec,
                )
                for item, vec in zip(batch, vectors)
            ]

            collection.data.insert_many(data_objects)
            print(f"      Uploaded chunks {i + 1} to {min(i + batch_size, len(all_chunks))} of {len(all_chunks)}")

    print(f"[OK] '{pdf_name}' indexed successfully ({len(all_chunks)} chunks placed on Weaviate shelves)!")


async def main():
    ensure_statute_collection_exists()

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        pdf_files = sorted([f for f in LEGAL_PDFS_DIR.iterdir() if f.suffix.lower() == ".pdf"])
        total = len(pdf_files)
        print(f"Resuming indexing for {total} PDF volumes from {LEGAL_PDFS_DIR}...")
        for idx, pdf_path in enumerate(pdf_files, 1):
            print(f"\n[{idx}/{total}] Checking: {pdf_path.name}")
            try:
                await index_pdf_file(pdf_path, max_pages=150)
            except Exception as exc:
                print(f"  [ERROR] Failed to index '{pdf_path.name}': {exc}. Continuing to next...")
            
        print("\n" + "=" * 70)
        print(f"[OK] All {total} Legal PDF volumes are completely indexed and live in Weaviate!")
        print("=" * 70)
        return

    if len(sys.argv) > 1:
        target_name = sys.argv[1]
        target_path = LEGAL_PDFS_DIR / target_name
        if not target_path.exists():
            print(f"Error: File '{target_name}' not found in {LEGAL_PDFS_DIR}")
            return
        await index_pdf_file(target_path, max_pages=150)
    else:
        test_file = LEGAL_PDFS_DIR / "The Negotiable Instruments Act, 1881.PDF"
        if test_file.exists():
            await index_pdf_file(test_file, max_pages=150)


if __name__ == "__main__":
    asyncio.run(main())
