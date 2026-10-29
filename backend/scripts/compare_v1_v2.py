"""
LegalDrishti AI - Live Comparison Runner: V1 (Cloud) vs V2 (Local Fine-Tuned GPU)
Runs the identical statutory query through both Version 1 and Version 2 pipelines.
"""

import sys
import os
import time
import asyncio
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def run_comparison(query: str):
    print("=" * 95)
    print("⚖️  LegalDrishti AI — Live Dual-Track Comparison (V1 Cloud vs V2 GPU)")
    print("=" * 95)
    print(f"QUERY: \"{query}\"\n")

    # -------------------------------------------------------------
    # TRACK 1: Version 1 (Cloud OpenAI Embeddings + Weaviate V1)
    # -------------------------------------------------------------
    print("-" * 95)
    print("🔹 EXECUTING VERSION 1 (Cloud Track: text-embedding-3-small + GlobalStatuteChunk)...")
    print("-" * 95)
    v1_answer = "N/A"
    v1_sources = []
    v1_latency = 0.0

    try:
        from app.services.retrieval_v1 import generate_grounded_legal_answer

        t0 = time.perf_counter()
        v1_result = await generate_grounded_legal_answer(
            query=query,
            user_id=1,
            case_id=None,
        )
        v1_latency = (time.perf_counter() - t0) * 1000.0
        v1_answer = v1_result.get("answer", "")
        v1_sources = v1_result.get("sources", [])
        print(f"✅ V1 Finished in {v1_latency:.1f} ms | Retrieved Sources: {len(v1_sources)}")
    except Exception as exc:
        print(f"⚠️ V1 Error: {exc}")

    # -------------------------------------------------------------
    # TRACK 2: Version 2 (Local Octen-0.6B GPU Embeddings + Weaviate V2 + Jev Router)
    # -------------------------------------------------------------
    print("\n" + "-" * 95)
    print("🟢 EXECUTING VERSION 2 (Local GPU Track: Octen-0.6B + GlobalStatuteChunk_V2 + Jev Router)...")
    print("-" * 95)
    v2_answer = "N/A"
    v2_sources = []
    v2_latency = 0.0
    v2_decision = {}

    try:
        from app.services.retrieval_v2 import generate_grounded_legal_answer_v2

        t0 = time.perf_counter()
        v2_result = await generate_grounded_legal_answer_v2(
            query=query,
            user_id=1,
            case_id=None,
            include_statutes=True,
        )
        v2_latency = (time.perf_counter() - t0) * 1000.0
        v2_answer = v2_result.get("answer", "")
        v2_sources = v2_result.get("sources", [])
        v2_decision = v2_result.get("decision", {})
        print(f"✅ V2 Finished in {v2_latency:.1f} ms | Retrieved Sources: {len(v2_sources)} | Decision: {v2_decision.get('reasoning', '')}")
    except Exception as exc:
        print(f"⚠️ V2 Error: {exc}")

    # -------------------------------------------------------------
    # PRINT RESULTS COMPARISON
    # -------------------------------------------------------------
    print("\n" + "=" * 95)
    print("📋 SIDE-BY-SIDE RESULT COMPARISON")
    print("=" * 95)

    print("\n" + "═" * 45 + " VERSION 1 ANSWER " + "═" * 45)
    print(v1_answer.strip())
    print("\n[V1 Sources]:")
    for s in v1_sources[:3]:
        print(f"  • {s.get('document_title')} (Page {s.get('page_number')}) - Score: {s.get('score')}")

    print("\n" + "═" * 45 + " VERSION 2 ANSWER " + "═" * 45)
    print(v2_answer.strip())
    print("\n[V2 Sources]:")
    for s in v2_sources[:3]:
        print(f"  • {s.get('document_title')} (Page {s.get('page_number')}) - Score: {s.get('score')}")

    print("\n" + "=" * 95)
    print(f"⏱️ Latency: V1 = {v1_latency:.1f} ms | V2 = {v2_latency:.1f} ms")
    print("=" * 95)


if __name__ == "__main__":
    test_query = (
        "What is the statutory limitation period to issue a legal demand notice and "
        "file a criminal complaint for cheque dishonour under Section 138 of the Negotiable Instruments Act?"
    )
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])

    asyncio.run(run_comparison(test_query))
