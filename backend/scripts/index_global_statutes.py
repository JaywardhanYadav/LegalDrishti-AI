import sys
import time
import asyncio
from pathlib import Path
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.vector_store import (
    get_weaviate_client,
    ensure_statute_collection_exists,
    STATUTE_COLLECTION_NAME,
)
from app.services.embeddings import get_embeddings_batch
from weaviate.classes.data import DataObject
from weaviate.classes.query import Filter

LEGAL_PDFS_DIR = BASE_DIR.parent / "Legal Pdfs"


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    if not text.strip():
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks


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
    print(f"\n[Librarian] Examining '{pdf_name}'...")

    existing_count = get_indexed_chunk_count(pdf_name)

    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    pages_to_process = min(total_pages, max_pages)
    print(f"  --> Reading {pages_to_process} of {total_pages} pages...")

    all_chunks: list[dict] = []
    chunk_counter = 0

    for page_idx in range(pages_to_process):
        page_num = page_idx + 1
        try:
            page_text = reader.pages[page_idx].extract_text() or ""
        except Exception:
            continue

        raw_chunks = chunk_text(page_text, chunk_size=800, overlap=150)
        for c in raw_chunks:
            if len(c) < 50:
                continue
            chunk_counter += 1
            all_chunks.append({
                "chunk_text": c,
                "pdf_name": pdf_name,
                "page_number": page_num,
                "chunk_index": chunk_counter,
            })

    if not all_chunks:
        print(f"  --> Warning: No extractable text found in '{pdf_name}'.")
        return

    # If already fully indexed, skip
    if existing_count >= len(all_chunks):
        print(f"  --> Skipping: '{pdf_name}' is already completely indexed ({existing_count} chunks in Weaviate).")
        return

    # If partially indexed due to network drop, clean up partials and re-insert cleanly
    if existing_count > 0:
        print(f"  --> Cleaning up previous partial index ({existing_count} chunks) to re-index cleanly...")
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

    print(f"✓ '{pdf_name}' indexed successfully ({len(all_chunks)} chunks placed on Weaviate shelves)!")


async def main():
    ensure_statute_collection_exists()

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        pdf_files = sorted([f for f in LEGAL_PDFS_DIR.iterdir() if f.suffix.lower() == ".pdf"])
        total = len(pdf_files)
        print(f"Resuming indexing for {total} PDF volumes from {LEGAL_PDFS_DIR}...")
        
        for idx, pdf_path in enumerate(pdf_files, 1):
            print(f"\n[{idx}/{total}] Checking: {pdf_path.name}")
            await index_pdf_file(pdf_path, max_pages=150)
            
        print("\n" + "=" * 70)
        print(f"✓ All {total} Legal PDF volumes are completely indexed and live in Weaviate!")
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
