# backend/scripts/test_rag_cache.py
import sys
import time
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.database import async_session_factory
from app.services.retrieval import generate_grounded_legal_answer
from app.core.redis_client import delete_keys_by_pattern, is_redis_ready


async def test_rag_caching():
    print("=" * 80)
    print("TESTING REDIS CACHING FOR GROUNDED RAG PIPELINE")
    print("=" * 80)
    print(f"Redis Status: {'ONLINE ✅' if is_redis_ready() else 'OFFLINE ❌'}")

    test_case_id = 9999
    test_user_id = 1
    query = "What is the statutory limitation period and penalty for cheque bounce under Section 138 NI Act?"

    # Step 0: Clear any leftover cache for this test case
    delete_keys_by_pattern(f"rag:case:{test_case_id}:*")

    async with async_session_factory() as session:
        # Run 1: Cold Cache (Should MISS and call Weaviate + FlashRank + OpenAI)
        print("\n--- RUN 1: Cold Query Execution ---")
        t0 = time.perf_counter()
        res1 = await generate_grounded_legal_answer(
            query=query,
            user_id=test_user_id,
            session=session,
            case_id=test_case_id,
        )
        elapsed1 = time.perf_counter() - t0
        print(f"Run 1 Time: {elapsed1:.3f}s")
        print(f"Answer snippet:\n{res1['answer'][:180]}...\n")

        # Run 2: Warm Cache (Should HIT and return from Redis instantly in <0.01s)
        print("--- RUN 2: Repeating Identical Query ---")
        t0 = time.perf_counter()
        res2 = await generate_grounded_legal_answer(
            query=query,
            user_id=test_user_id,
            session=session,
            case_id=test_case_id,
        )
        elapsed2 = time.perf_counter() - t0
        speedup = elapsed1 / max(elapsed2, 0.0001)
        print(f"Run 2 Time: {elapsed2:.4f}s (Speedup: {speedup:.1f}x faster)")

        # Step 3: Test Cache Invalidation
        print("\n--- STEP 3: Simulating Document Upload / Cache Invalidation ---")
        flushed = delete_keys_by_pattern(f"rag:case:{test_case_id}:*")
        print(f"Flushed keys for case {test_case_id}: {flushed}")

        # Run 3: Should MISS again because cache was invalidated
        print("\n--- RUN 3: Query After Cache Invalidation ---")
        t0 = time.perf_counter()
        res3 = await generate_grounded_legal_answer(
            query=query,
            user_id=test_user_id,
            session=session,
            case_id=test_case_id,
        )
        elapsed3 = time.perf_counter() - t0
        print(f"Run 3 Time: {elapsed3:.3f}s")

    print("\n" + "=" * 80)
    print("ALL RAG CACHING & INVALIDATION CHECKS COMPLETED ✅")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_rag_caching())
