"""
LegalDrishti Quad-Track Comparative Evaluation Benchmarker
==========================================================
Compares retrieval and answer quality across all 4 architectures:
1. Track 1 (V1 Cloud):   LangChain Recursive Chunker + OpenAI 1536-D ('GlobalStatuteChunk')
2. Track 2 (V2 Local):   Contextual Section-Aware Chunker + Fine-Tuned Octen-0.6B ('GlobalStatuteChunk_V2')
3. Track 3 (Hybrid FT):  LangChain Recursive Chunker + Fine-Tuned Octen-0.6B ('Recursive_FineTune_Model')
4. Track 4 (Hybrid Base): LangChain Recursive Chunker + Base Non-Fine-Tuned Octen-0.6B ('Recursive_Base_Octen')
"""
from __future__ import annotations

import sys
import time
import asyncio
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.vector_store_v1 import get_weaviate_client
from app.services.retrieval_v1 import generate_grounded_legal_answer_v1
from app.services.retrieval_v2 import generate_grounded_legal_answer_v2
from app.services.hybrid_experiment import (
    generate_grounded_legal_answer_recursive_finetune,
    generate_grounded_legal_answer_recursive_base_octen,
)


async def run_quad_track_comparison(query: str):
    print("=" * 80)
    print("  LEGALDRISHTI AI: QUAD-TRACK RETRIEVAL & SYNTHESIS BENCHMARK")
    print(f"  Query: '{query}'")
    print("=" * 80)

    # 1. Track 1: Version 1
    print("\n" + "-" * 40)
    print(">> RUNNING TRACK 1: Version 1 (Recursive Chunker + OpenAI 1536-D)")
    print("-" * 40)
    t0 = time.time()
    try:
        res_v1 = await generate_grounded_legal_answer_v1(
            query=query,
            user_id=1,
            case_id=None,
        )
        t_v1 = time.time() - t0
        print(f"Status: OK ({t_v1:.2f}s)")
        print(f"Sources retrieved: {len(res_v1.get('sources', []))}")
        print("\nAnswer Snippet:")
        print(res_v1.get("answer", "")[:350] + "...\n")
    except Exception as e:
        res_v1 = {"error": str(e)}
        print(f"Track 1 Error: {e}")

    # 2. Track 2: Version 2
    print("-" * 40)
    print(">> RUNNING TRACK 2: Version 2 (Section-Aware + Fine-Tuned Octen-0.6B 1024-D)")
    print("-" * 40)
    t0 = time.time()
    try:
        res_v2 = await generate_grounded_legal_answer_v2(
            query=query,
            user_id=1,
            case_id=None,
            include_statutes=True,
        )
        t_v2 = time.time() - t0
        print(f"Status: OK ({t_v2:.2f}s)")
        print(f"Sources retrieved: {len(res_v2.get('sources', []))}")
        print("\nAnswer Snippet:")
        print(res_v2.get("answer", "")[:350] + "...\n")
    except Exception as e:
        res_v2 = {"error": str(e)}
        print(f"Track 2 Error: {e}")

    # 3. Track 3: Hybrid Track 1 (Recursive + Fine-Tuned Octen)
    print("-" * 40)
    print(">> RUNNING TRACK 3: Hybrid 1 (Recursive Chunker + Fine-Tuned Octen 1024-D)")
    print("-" * 40)
    t0 = time.time()
    try:
        res_h1 = generate_grounded_legal_answer_recursive_finetune(
            query=query,
            top_k=5,
        )
        t_h1 = time.time() - t0
        print(f"Status: OK ({t_h1:.2f}s)")
        print(f"Sources retrieved: {len(res_h1.get('sources', []))}")
        print("\nAnswer Snippet:")
        print(res_h1.get("answer", "")[:350] + "...\n")
    except Exception as e:
        res_h1 = {"error": str(e)}
        print(f"Track 3 Error: {e}")

    # 4. Track 4: Hybrid Track 2 (Recursive + Base Octen)
    print("-" * 40)
    print(">> RUNNING TRACK 4: Hybrid 2 (Recursive Chunker + Base Non-Fine-Tuned Octen 1024-D)")
    print("-" * 40)
    t0 = time.time()
    try:
        res_h2 = generate_grounded_legal_answer_recursive_base_octen(
            query=query,
            top_k=5,
        )
        t_h2 = time.time() - t0
        print(f"Status: OK ({t_h2:.2f}s)")
        print(f"Sources retrieved: {len(res_h2.get('sources', []))}")
        print("\nAnswer Snippet:")
        print(res_h2.get("answer", "")[:350] + "...\n")
    except Exception as e:
        res_h2 = {"error": str(e)}
        print(f"Track 4 Error: {e}")

    print("=" * 80)
    print("  QUAD-TRACK BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"1. V1 (Recursive + OpenAI 1536-D):           {len(res_v1.get('sources', []))} sources retrieved")
    print(f"2. V2 (Section-Aware + Fine-Tuned Octen):    {len(res_v2.get('sources', []))} sources retrieved")
    print(f"3. Hybrid 1 (Recursive + Fine-Tuned Octen):  {len(res_h1.get('sources', []))} sources retrieved")
    print(f"4. Hybrid 2 (Recursive + Base Non-FT Octen): {len(res_h2.get('sources', []))} sources retrieved")
    print("=" * 80)


if __name__ == "__main__":
    q = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "What are the essential ingredients and penalty for dishonour of cheque under Section 138 of the Negotiable Instruments Act?"
    )
    asyncio.run(run_quad_track_comparison(q))
