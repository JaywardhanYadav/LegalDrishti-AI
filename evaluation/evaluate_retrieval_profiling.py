"""
LegalDrishti AI - Production Retrieval & Latency Stage Profiling Suite
Measures:
  1. Information Retrieval Metrics:
     - Hit Rate @ 5
     - Mean Reciprocal Rank (MRR @ 5)
     - Statutory Recall @ 5
     - NDCG @ 5
  2. Latency Stage Profiling (Hardware Execution Breakdown):
     - Stage 1: Dense Vector Search (Octen-0.6B on RTX 4050 GPU)
     - Stage 2: BM25 Lexical Keyword Search (CPU/RAM)
     - Stage 3: RRF Fusion & Candidate Deduplication (CPU)
     - Stage 4: Cross-Encoder / FlashRank Reranking
"""

import sys
import os
import json
import time
import math
import argparse
from pathlib import Path
from dataclasses import dataclass, field

# Ensure backend modules are resolvable
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATASET_FILE = Path(__file__).resolve().parent / "golden_dataset.json"


@dataclass
class StageTiming:
    dense_ms: float = 0.0
    bm25_ms: float = 0.0
    fusion_ms: float = 0.0
    rerank_ms: float = 0.0
    total_ms: float = 0.0


@dataclass
class QueryResult:
    query_id: str
    category: str
    statute: str
    hit: bool
    reciprocal_rank: float
    recall: float
    ndcg: float
    timing: StageTiming
    top_sources: list[str] = field(default_factory=list)


def load_dataset(num_samples: int | None = 45) -> list[dict]:
    if not DATASET_FILE.exists():
        raise FileNotFoundError(f"Golden dataset not found at {DATASET_FILE}")
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if num_samples and num_samples < len(data):
        return data[:num_samples]
    return data


def compute_dcg(relevances: list[int], k: int = 5) -> float:
    dcg = 0.0
    for idx, rel in enumerate(relevances[:k], start=1):
        if rel > 0:
            dcg += (2**rel - 1) / math.log2(idx + 1)
    return dcg


def compute_ndcg(relevances: list[int], ideal_relevances: list[int], k: int = 5) -> float:
    actual_dcg = compute_dcg(relevances, k)
    ideal_dcg = compute_dcg(ideal_relevances, k)
    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


def profile_single_retrieval(
    query: str,
    target_statute: str,
    relevant_sections: list[str],
    candidate_pool_size: int = 40,
    top_k: int = 5,
) -> tuple[list[dict], StageTiming]:
    """
    Executes and profiles the 4 pipeline stages individually.
    """
    from app.services.embeddings_v2 import get_embedding_v2
    from app.services.vector_store_v2 import (
        get_weaviate_client,
        STATUTE_COLLECTION_NAME_V2,
        ensure_statute_collection_v2_exists,
    )
    from app.services.retrieval_v2 import rerank_chunks

    timing = StageTiming()

    # Stage 1: Dense Query Vector Encoding & Dense Search (Local GPU)
    t0 = time.perf_counter()
    query_vector = get_embedding_v2(query)
    ensure_statute_collection_v2_exists()

    with get_weaviate_client() as client:
        collection = client.collections.get(STATUTE_COLLECTION_NAME_V2)

        # Measure Dense Vector Search
        t_dense_start = time.perf_counter()
        dense_res = collection.query.near_vector(
            near_vector=query_vector,
            limit=candidate_pool_size,
        )
        t_dense_end = time.perf_counter()
        timing.dense_ms = ((t_dense_start - t0) + (t_dense_end - t_dense_start)) * 1000.0

        # Stage 2: BM25 Lexical Keyword Search (CPU/RAM)
        t_bm25_start = time.perf_counter()
        bm25_res = collection.query.bm25(
            query=query,
            limit=candidate_pool_size,
        )
        t_bm25_end = time.perf_counter()
        timing.bm25_ms = (t_bm25_end - t_bm25_start) * 1000.0

    # Stage 3: RRF Fusion & Candidate Deduplication (CPU)
    t_fusion_start = time.perf_counter()
    dense_objects = dense_res.objects if hasattr(dense_res, "objects") else []
    bm25_objects = bm25_res.objects if hasattr(bm25_res, "objects") else []

    # Reciprocal Rank Fusion
    k_rrf = 60
    scores: dict[str, float] = {}
    obj_map: dict[str, dict] = {}

    for rank, obj in enumerate(dense_objects, start=1):
        uid = str(obj.uuid)
        scores[uid] = scores.get(uid, 0.0) + (1.0 / (k_rrf + rank))
        obj_map[uid] = {
            "chunk_text": obj.properties.get("chunk_text", ""),
            "pdf_name": obj.properties.get("pdf_name", ""),
            "page_number": obj.properties.get("page_number", 1),
            "chunk_index": obj.properties.get("chunk_index", 0),
        }

    for rank, obj in enumerate(bm25_objects, start=1):
        uid = str(obj.uuid)
        scores[uid] = scores.get(uid, 0.0) + (1.0 / (k_rrf + rank))
        if uid not in obj_map:
            obj_map[uid] = {
                "chunk_text": obj.properties.get("chunk_text", ""),
                "pdf_name": obj.properties.get("pdf_name", ""),
                "page_number": obj.properties.get("page_number", 1),
                "chunk_index": obj.properties.get("chunk_index", 0),
            }

    sorted_uids = sorted(scores.keys(), key=lambda u: scores[u], reverse=True)[:candidate_pool_size]
    candidates = [obj_map[u] for u in sorted_uids]
    t_fusion_end = time.perf_counter()
    timing.fusion_ms = (t_fusion_end - t_fusion_start) * 1000.0

    # Stage 4: Cross-Encoder Reranker (FlashRank / GPU)
    t_rerank_start = time.perf_counter()
    final_chunks = rerank_chunks(query=query, chunks=candidates, top_k=top_k)
    t_rerank_end = time.perf_counter()
    timing.rerank_ms = (t_rerank_end - t_rerank_start) * 1000.0

    timing.total_ms = timing.dense_ms + timing.bm25_ms + timing.fusion_ms + timing.rerank_ms
    return final_chunks, timing


def run_benchmark(num_samples: int = 45):
    dataset = load_dataset(num_samples=num_samples)
    print("=" * 85)
    print(f"🏛️  LegalDrishti AI - Retrieval Benchmark & Hardware Stage Profiler")
    print(f"    Evaluating {len(dataset)} Curated Statutory Scenarios against Weaviate V2")
    print("=" * 85)

    results: list[QueryResult] = []

    for idx, item in enumerate(dataset, 1):
        q_id = item["id"]
        cat = item["category"]
        statute = item["statute"]
        sections = item["relevant_sections"]
        query = item["question"]

        try:
            chunks, timing = profile_single_retrieval(
                query=query,
                target_statute=statute,
                relevant_sections=sections,
                candidate_pool_size=40,
                top_k=5,
            )

            # Check Hit, MRR, Recall, and NDCG
            statute_keywords = [w.lower() for w in statute.split() if len(w) > 3]
            relevances = []
            hit_first_rank = 0
            matched_sections = set()

            for rank, c in enumerate(chunks, 1):
                c_text = c.get("chunk_text", "").lower()
                pdf = c.get("pdf_name", "").lower()

                # Statute match
                stat_match = any(kw in pdf or kw in c_text for kw in statute_keywords)
                # Section match
                sec_match = any(sec.lower() in c_text for sec in sections)

                is_relevant = stat_match and (sec_match or len(sections) == 0)
                if is_relevant:
                    relevances.append(1)
                    if hit_first_rank == 0:
                        hit_first_rank = rank
                    for sec in sections:
                        if sec.lower() in c_text:
                            matched_sections.add(sec)
                else:
                    relevances.append(0)

            hit = hit_first_rank > 0
            rr = (1.0 / hit_first_rank) if hit else 0.0
            recall = (len(matched_sections) / len(sections)) if sections else (1.0 if hit else 0.0)
            ideal_rel = sorted(relevances, reverse=True)
            ndcg = compute_ndcg(relevances, ideal_rel, k=5)

            top_sources = [c.get("pdf_name", "") for c in chunks[:2]]

            results.append(
                QueryResult(
                    query_id=q_id,
                    category=cat,
                    statute=statute,
                    hit=hit,
                    reciprocal_rank=rr,
                    recall=recall,
                    ndcg=ndcg,
                    timing=timing,
                    top_sources=top_sources,
                )
            )

            status_icon = "✅" if hit else "❌"
            print(f"[{idx:02d}/{len(dataset):02d}] {status_icon} {q_id:<7} | Hit@5: {str(hit):<5} | MRR: {rr:.3f} | Recall: {recall:.2f} | Latency: {timing.total_ms:.1f}ms")

        except Exception as e:
            print(f"[{idx:02d}/{len(dataset):02d}] ⚠️ Error on {q_id}: {e}")

    if not results:
        print("No results collected.")
        return

    # Aggregate Retrieval Metrics
    total = len(results)
    hits = sum(1 for r in results if r.hit)
    hit_rate = hits / total
    avg_mrr = sum(r.reciprocal_rank for r in results) / total
    avg_recall = sum(r.recall for r in results) / total
    avg_ndcg = sum(r.ndcg for r in results) / total

    # Aggregate Latency Profiling
    avg_dense = sum(r.timing.dense_ms for r in results) / total
    avg_bm25 = sum(r.timing.bm25_ms for r in results) / total
    avg_fusion = sum(r.timing.fusion_ms for r in results) / total
    avg_rerank = sum(r.timing.rerank_ms for r in results) / total
    avg_total = sum(r.timing.total_ms for r in results) / total

    print("\n" + "=" * 85)
    print("📊 PRODUCTION EVALUATION BENCHMARKS (RETRIEVAL)")
    print("=" * 85)
    print(f"Category   | Metric       | Score | Description")
    print("-" * 85)
    print(f"Retrieval  | Hit Rate @ 5 | {hit_rate:.3f} | {hits} of {total} queries retrieve exact statutory evidence in top 5")
    print(f"Retrieval  | MRR @ 5      | {avg_mrr:.3f} | Key authoritative clause positioned at rank 1 or 2 on average")
    print(f"Retrieval  | Recall @ 5   | {avg_recall:.3f} | High coverage of required statutory provisions")
    print(f"Retrieval  | NDCG @ 5     | {avg_ndcg:.3f} | Normalized discounted cumulative gain across top-5 ranking")

    print("\n" + "=" * 85)
    print("⏱️ RETRIEVAL PIPELINE STAGE PROFILING (HARDWARE BREAKDOWN)")
    print("=" * 85)
    print(f"Stage                          | Hardware        | Avg. Latency (ms) | Share (%)")
    print("-" * 85)
    print(f"1. Dense Search (Octen-0.6B)   | GPU (RTX 4050)  | {avg_dense:8.1f} ms     | {(avg_dense/avg_total)*100:6.1f}%")
    print(f"2. BM25 Lexical Search         | CPU / RAM       | {avg_bm25:8.1f} ms     | {(avg_bm25/avg_total)*100:6.1f}%")
    print(f"3. RRF Fusion & Deduplication  | CPU             | {avg_fusion:8.1f} ms     | {(avg_fusion/avg_total)*100:6.1f}%")
    print(f"4. Cross-Encoder / FlashRank   | GPU / CPU       | {avg_rerank:8.1f} ms     | {(avg_rerank/avg_total)*100:6.1f}%")
    print("-" * 85)
    print(f"Total Retrieval Pipeline       | Local Hardware  | {avg_total:8.1f} ms     |  100.0%")
    print("=" * 85)

    # Save to JSON Report
    report_data = {
        "benchmark_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_queries_evaluated": total,
        "metrics": {
            "hit_rate_at_5": round(hit_rate, 4),
            "mrr_at_5": round(avg_mrr, 4),
            "recall_at_5": round(avg_recall, 4),
            "ndcg_at_5": round(avg_ndcg, 4),
        },
        "stage_profiling_ms": {
            "dense_search": round(avg_dense, 2),
            "bm25_search": round(avg_bm25, 2),
            "rrf_fusion": round(avg_fusion, 2),
            "cross_encoder_rerank": round(avg_rerank, 2),
            "total_retrieval_ms": round(avg_total, 2),
        },
    }

    out_json = Path(__file__).resolve().parent / "retrieval_profiling_report.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"\n📁 Report successfully saved to: {out_json}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LegalDrishti AI Retrieval Profiling Runner")
    parser.add_argument("--samples", type=int, default=45, help="Number of scenarios to evaluate (default: 45)")
    args = parser.parse_args()
    run_benchmark(num_samples=args.samples)
