"""
GPU-Accelerated Populator for Recursive_Base_Octen Hybrid Collection
===================================================================
Combines:
- Chunking: LangChain Recursive Character Splitter (from GlobalStatuteChunk, 14,225 chunks)
- Embeddings: Base (Non-Fine-Tuned) Octen-Embedding-0.6B (1024-D) running on CUDA GPU
- Target Collection: 'Recursive_Base_Octen'
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.vector_store_v1 import get_weaviate_client
from app.services.hybrid_experiment import (
    ensure_recursive_base_octen_collection_exists,
    get_embeddings_batch_base_octen,
    RECURSIVE_BASE_OCTEN_COLLECTION_NAME,
)
from weaviate.classes.data import DataObject

SOURCE_COLLECTION_NAME = "GlobalStatuteChunk"


def main():
    print("=" * 75, flush=True)
    print("  Populating 'Recursive_Base_Octen' Collection via CUDA GPU", flush=True)
    print(f"  Source (V1 Recursive Chunks): '{SOURCE_COLLECTION_NAME}'", flush=True)
    print(f"  Target (Base Octen 1024-D): '{RECURSIVE_BASE_OCTEN_COLLECTION_NAME}'", flush=True)
    print("=" * 75, flush=True)

    ensure_recursive_base_octen_collection_exists()

    with get_weaviate_client() as client:
        src_coll = client.collections.get(SOURCE_COLLECTION_NAME)
        dst_coll = client.collections.get(RECURSIVE_BASE_OCTEN_COLLECTION_NAME)

        # Clear any partial chunks to ensure clean full run
        dst_count = dst_coll.aggregate.over_all(total_count=True).total_count or 0
        if dst_count > 0:
            print(f"[Reset] Clearing {dst_count} preliminary chunks from '{RECURSIVE_BASE_OCTEN_COLLECTION_NAME}'...", flush=True)
            client.collections.delete(RECURSIVE_BASE_OCTEN_COLLECTION_NAME)
            ensure_recursive_base_octen_collection_exists()
            dst_coll = client.collections.get(RECURSIVE_BASE_OCTEN_COLLECTION_NAME)

        src_count = src_coll.aggregate.over_all(total_count=True).total_count or 0
        print(f"[Status] Reading all {src_count} V1 Docling/LangChain chunks from '{SOURCE_COLLECTION_NAME}'...", flush=True)

        batch_texts = []
        batch_items = []
        batch_size = 32
        processed = 0

        start_time = time.time()

        for obj in src_coll.iterator():
            props = obj.properties
            batch_texts.append(props.get("chunk_text", ""))
            batch_items.append({
                "chunk_text": props.get("chunk_text", ""),
                "pdf_name": props.get("pdf_name", ""),
                "page_number": props.get("page_number", 1),
                "chunk_index": props.get("chunk_index", 0),
                "heading": props.get("heading", ""),
            })

            if len(batch_texts) >= batch_size:
                vectors = get_embeddings_batch_base_octen(batch_texts, batch_size=batch_size)
                data_objs = [
                    DataObject(
                        properties=item,
                        vector=vec,
                    )
                    for item, vec in zip(batch_items, vectors)
                ]
                dst_coll.data.insert_many(data_objs)
                processed += len(batch_texts)
                elapsed = time.time() - start_time
                rate = processed / max(1, elapsed)
                print(f"  --> [GPU Ingested {processed}/{src_count} chunks] ({rate:.1f} chunks/sec)", flush=True)
                batch_texts.clear()
                batch_items.clear()

        # Final trailing batch
        if batch_texts:
            vectors = get_embeddings_batch_base_octen(batch_texts, batch_size=batch_size)
            data_objs = [
                DataObject(
                    properties=item,
                    vector=vec,
                )
                for item, vec in zip(batch_items, vectors)
            ]
            dst_coll.data.insert_many(data_objs)
            processed += len(batch_texts)

        total_final = dst_coll.aggregate.over_all(total_count=True).total_count or 0
        print(f"\n[OK] Complete! '{RECURSIVE_BASE_OCTEN_COLLECTION_NAME}' now holds {total_final} chunks with Base (Non-Fine-Tuned) Octen embeddings!\n", flush=True)


if __name__ == "__main__":
    main()
