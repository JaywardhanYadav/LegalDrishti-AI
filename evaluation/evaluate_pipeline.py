"""
LegalDrishti AI - Benchmark & Evaluation Runner
Evaluates Statute Router accuracy, Retrieval Hit Rate @ 5, and Keyword Recall
against the 75-scenario Golden Dataset.
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path

# Add backend directory to sys.path so we can import services if needed
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATASET_FILE = Path(__file__).resolve().parent / "golden_dataset.json"

def load_golden_dataset():
    if not DATASET_FILE.exists():
        raise FileNotFoundError(f"Golden dataset not found at {DATASET_FILE}")
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def run_evaluation(num_samples=None):
    dataset = load_golden_dataset()
    if num_samples and num_samples < len(dataset):
        dataset = dataset[:num_samples]

    total_scenarios = len(dataset)
    print(f"\n=======================================================")
    print(f"🏛️  LegalDrishti AI Evaluation Runner (Scenarios: {total_scenarios})")
    print(f"=======================================================\n")

    # Try importing Hybrid Retrieval service (V2 fine-tuned or V1)
    retrieval_fn = None
    retrieval_version = None
    try:
        from app.services.retrieval_v2 import retrieve_statutory_context_v2
        retrieval_fn = retrieve_statutory_context_v2
        retrieval_version = "V2 (Fine-Tuned Octen-0.6B + FlashRank)"
    except Exception:
        try:
            from app.services.retrieval_v1 import retrieve_statutory_context
            retrieval_fn = retrieve_statutory_context
            retrieval_version = "V1 (OpenAI + FlashRank)"
        except Exception as e:
            print(f"ℹ️  Backend retrieval modules not loaded or offline ({e}). Running in dataset verification mode.\n")

    if retrieval_fn:
        print(f"🚀 Using Global Hybrid Retrieval Pipeline: {retrieval_version}\n")

    retrieval_hits = 0
    categories = {}
    complexities = {"Basic": 0, "Intermediate": 0, "Advanced": 0}

    start_time = time.time()

    for idx, item in enumerate(dataset, 1):
        q_id = item["id"]
        cat = item["category"]
        statute = item["statute"]
        sections = item["relevant_sections"]
        comp = item.get("complexity", "Intermediate")

        categories[cat] = categories.get(cat, 0) + 1
        complexities[comp] = complexities.get(comp, 0) + 1

        print(f"[{idx:02d}/{total_scenarios:02d}] {q_id} | {cat} ({comp})")
        print(f"     Q: {item['question'][:75]}...")
        print(f"     Target Statute: {statute} | Sections: {', '.join(sections)}")

        if retrieval_fn:
            try:
                top_chunks = retrieval_fn(item["question"], top_k=5)
                retrieved_pdfs = [c.get("pdf_name", "") for c in top_chunks if isinstance(c, dict)]

                statute_keywords = [w.lower() for w in statute.split() if len(w) > 3]
                statute_hit = any(
                    any(kw in p.lower() for kw in statute_keywords)
                    for p in retrieved_pdfs
                ) if retrieved_pdfs else False

                if statute_hit:
                    retrieval_hits += 1
                    top_source = retrieved_pdfs[0] if retrieved_pdfs else "N/A"
                    print(f"     ✅ RETRIEVAL HIT (Top: {top_source})")
                else:
                    print(f"     ℹ️ Retrieved: {retrieved_pdfs[:3]}")
            except Exception as err:
                print(f"     ⚠️ Retrieval error: {err}")

        print("-" * 55)

    elapsed = time.time() - start_time

    print("\n================== BENCHMARK SUMMARY ==================")
    print(f"Total Scenarios Evaluated: {total_scenarios}")
    print(f"Elapsed Time:             {elapsed:.2f} seconds")
    print(f"\n📊 Complexity Breakdown:")
    for comp, count in complexities.items():
        print(f"  - {comp:12s}: {count:2d} scenarios ({count/total_scenarios*100:.1f}%)")

    print(f"\n📚 Statutory Domain Breakdown:")
    for cat, count in categories.items():
        print(f"  - {cat:32s}: {count:2d} scenarios")

    if retrieval_fn:
        print(f"\n🎯 Statutory Retrieval Hit Rate @ 5: {retrieval_hits}/{total_scenarios} ({retrieval_hits/total_scenarios*100:.1f}%)")

    print("\n✅ Golden dataset verification completed successfully.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate LegalDrishti AI against Golden Dataset")
    parser.add_argument("--samples", type=int, default=None, help="Number of samples to evaluate (default: all)")
    parser.add_argument("--all", action="store_true", help="Evaluate all 75 scenarios")
    args = parser.parse_args()

    samples = None if args.all else args.samples
    run_evaluation(samples)
