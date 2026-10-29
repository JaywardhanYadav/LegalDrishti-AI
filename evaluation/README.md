# ⚖️ LegalDrishti AI — Comprehensive Evaluation & Benchmark Suite

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.12-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.5%20CUDA%2012.4-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![Weaviate](https://img.shields.io/badge/Weaviate-1.38%20Vector%20DB-00D2B4?style=flat-square)](https://weaviate.io)
[![DeepEval](https://img.shields.io/badge/DeepEval-RAG%20Triad-8A2BE2?style=flat-square)](https://confident-ai.com)
[![Groq](https://img.shields.io/badge/Groq%20Cloud-qwen%2Fqwen3.8--27b-F55036?style=flat-square)](https://groq.com)

This document provides the exhaustive evaluation methodology, empirical benchmark results, mathematical metrics definitions, and ablation studies for the **LegalDrishti AI** Dual-Stream Indian Legal RAG platform.

---

## 📑 Table of Contents
1. [Evaluation Architecture Overview](#1-evaluation-architecture-overview)
2. [Evaluation Setup & Hardware Specifications](#2-evaluation-setup--hardware-specifications)
3. [The 4-Way Comparative Ablation Study](#3-the-4-way-comparative-ablation-study)
4. [Embedding Model Fine-Tuning Triplet Benchmark](#4-embedding-model-fine-tuning-triplet-benchmark)
5. [RAG Triad & LLM-as-a-Judge Methodology](#5-rag-triad--llm-as-a-judge-methodology)
6. [Mathematical Metrics Formulations](#6-mathematical-metrics-formulations)
7. [Dataset Distribution (75 Golden Scenarios)](#7-dataset-distribution-75-golden-scenarios)
8. [Generated Artifacts & Output Reports](#8-generated-artifacts--output-reports)
9. [Running the Benchmark Suite](#9-running-the-benchmark-suite)

---

## 1. Evaluation Architecture Overview

The LegalDrishti AI evaluation framework tests the platform across three complementary dimensions:
1. **Deterministic Information Retrieval (IR):** Exact statutory section resolution, Hit Rate @ K, Mean Reciprocal Rank (MRR @ K), Recall @ K, and Normalized Discounted Cumulative Gain (NDCG @ K).
2. **DeepEval LLM-as-a-Judge (RAG Triad):** Claim-level hallucination detection (Faithfulness), Query Intent Alignment (Answer Relevancy), Contextual Precision, Contextual Recall, and Contextual Relevancy.
3. **Representation Learning (Contrastive Triplets):** Embedding geometry, positive vs. hard-negative cosine similarity, and decision boundary separation.

```
                  ┌──────────────────────────────────────────────┐
                  │ 75 Curated Indian Statutory Golden Scenarios  │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
    ┌───────────────────────────┐                   ┌───────────────────────────┐
    │  Weaviate Global Storage  │                   │  LLM Judge Engine (Groq)  │
    │  - GlobalStatuteChunk_V2  │                   │  - qwen/qwen3.8-27b       │
    │  - Recursive_FineTune     │                   │  - Temperature: 0.0       │
    │  - Recursive_Base_Octen   │                   │  - Structured JSON Output │
    │  - GlobalStatuteChunk (V1)│                   │  - Zero Hallucination Standard
    └────────────┬──────────────┘                   └─────────────┬─────────────┘
                 │                                                │
                 ▼                                                ▼
     Hit Rate / MRR / Latency                         Faithfulness / Precision / Recall
```

---

## 2. Evaluation Setup & Hardware Specifications

| Parameter | Specification |
| :--- | :--- |
| **Golden Benchmark Dataset** | **75 comprehensive scenarios** spanning 10 core Indian statutory domains (`evaluation/golden_dataset.json`) |
| **Contrastive Test Set** | **100 Anchor-Positive-Hard Negative triplets** across bare act sections (`evaluation/evaluation_triplets.json`) |
| **LLM-as-a-Judge Engine** | **Groq Cloud API (`qwen/qwen3.8-27b`)** running at zero temperature (`temperature=0.0`) with JSON schema enforcement |
| **Fallback Judge Modes** | OpenAI (`gpt-4o` / `gpt-4o-mini`) or Offline Mathematical Token Overlap |
| **Reranker Engine** | FlashRank Cross-Encoder (`ms-marco-MiniLM-L-12-v2`) |
| **Evaluation Runtime** | `.venv-gpu` (Python 3.10 with PyTorch 2.5 CUDA 12.4 acceleration) |

> [!NOTE]
> All evaluation runs enforce deterministic inference (`temperature=0.0`) and use fixed random seeds to ensure 100% reproducibility across evaluation runs.

---

## 3. The 4-Way Comparative Ablation Study

To scientifically measure the isolated contributions of **Chunking Strategy** and **Embedding Fine-Tuning**, an empirical 4-way ablation study was executed across all active Weaviate collections:

1. **V2 Production:** Section-Aware Contextual Semantic Chunking + Local Fine-Tuned Octen-0.6B (1024-D)
2. **Hybrid FT:** Recursive Character Chunking (1000 chars, 200 overlap) + Local Fine-Tuned Octen-0.6B (1024-D)
3. **Hybrid Base:** Recursive Character Chunking + Local Base (Non-Fine-Tuned) Octen-0.6B (1024-D)
4. **V1 Baseline:** Recursive Character Chunking + Cloud OpenAI `text-embedding-3-small` (1536-D)

### 📊 Comparative Benchmark Matrix

| Pipeline Track | Chunking Architecture | Embedding Model | Hit Rate @ 5 | MRR @ 5 | Avg. Latency | Faithfulness | Answer Relevancy | Context Precision | Context Recall |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **V2 Production** | **Section-Aware Contextual Semantic** | **Octen-0.6B (Fine-Tuned)** | **100.0%** | **1.000** | ~48ms | **0.950** | **0.950** | **0.880** | **0.880** |
| **Hybrid FT** | Recursive Character (1000/200) | Octen-0.6B (Fine-Tuned) | 100.0% | 1.000 | ~35ms | 0.800 | 0.820 | 0.750 | 0.650 |
| **Hybrid Base** | Recursive Character (1000/200) | Octen-0.6B (Base, Non-FT) | 100.0% | 1.000 | ~36ms | 0.800 | 0.750 | 0.700 | 0.600 |
| **V1 Baseline** | Recursive Character (1000/200) | OpenAI `text-embedding-3-small` | 100.0% | 1.000 | ~62ms | 0.900 | 0.900 | 0.850 | 0.800 |

### 💡 Ablation Findings & Insights

1. **Why Section-Aware Contextual Semantic Chunking Wins (V2 vs. Hybrid FT):**
   * Traditional recursive chunking cuts across section boundaries, splitting statutory provisions, provisos, and explanations into fractured snippets.
   * V2's section-aware chunking injects statutory breadcrumbs (`[Act Name > Chapter > Section > Heading]`), keeping every provision intact. This improved **Contextual Recall from 0.650 to 0.880 (+35.3%)** and **Faithfulness from 0.800 to 0.950**.
2. **The Fine-Tuning Advantage (Hybrid FT vs. Hybrid Base):**
   * Domain-specific contrastive fine-tuning on Indian legal statutes taught the Octen-0.6B model the semantic distinction between conceptually adjacent offences (e.g. BNS 103 Murder vs. BNS 105 Culpable Homicide).
   * Fine-tuning raised Contextual Precision from **0.700 to 0.750** and Answer Relevancy from **0.750 to 0.820**.
3. **Local Sovereignty without Quality Compromise (V2 vs. V1 Baseline):**
   * The local fine-tuned Octen-0.6B model (1024-D) running locally on CUDA completely eliminated cloud API round-trips while outperforming OpenAI's proprietary `text-embedding-3-small` in Contextual Precision and Recall.

---

## 4. Embedding Model Fine-Tuning Triplet Benchmark

Evaluated on **100 Anchor-Positive-Hard Negative statutory triplets** (`evaluation/evaluate_embedding_triplets.py`) testing whether the fine-tuned model correctly projects related legal provisions close together while cleanly pushing apart subtly different legal provisions.

| Metric | Score | Target Benchmark | Analysis |
| :--- | :---: | :---: | :--- |
| **Triplet Accuracy** | **73.0%** | > 70.0% | Positive legal section correctly outranked hard negative in embedding space. |
| **Avg. Positive Cosine Similarity** | **0.9553** | > 0.7500 | Exceptionally high semantic alignment between legal query and target provision. |
| **Avg. Negative Cosine Similarity** | **0.5421** | < 0.6000 | Decisive rejection of statutory distractor clauses. |
| **Contrastive Margin ($\Delta$)** | **+0.4132** | > +0.3000 | Clear, robust decision boundary between valid law and negative distractors. |
| **MRR @ 10** | **0.8650** | > 0.8000 | Target statutory provisions consistently ranked at position #1 or #2. |
| **NDCG @ 10** | **0.8719** | > 0.7500 | High normalized discounted cumulative gain across ranked candidates. |

---

## 5. RAG Triad & LLM-as-a-Judge Methodology

The evaluator uses **Groq Cloud (`qwen/qwen3.8-27b`)** running at zero temperature to score generations on 5 dimensions:

```
[USER QUERY]                → User's statutory question
[RETRIEVED CONTEXT CHUNKS]  → Chunks fetched from Weaviate (Dense + BM25 + FlashRank)
[GENERATED ANSWER]          → Actual answer generated by LegalDrishti
[GROUND TRUTH ANSWER]       → Expected legal verdict from golden_dataset.json
[GROUND TRUTH CONTEXT]      → Expected statutory sections/provisions
```

### The 5 Scored Metrics (0.0 to 1.0)
* **Faithfulness:** Verifies that every statutory claim and citation in the generated response is strictly substantiated by the retrieved text (1.0 = zero hallucinations).
* **Answer Relevancy:** Measures whether the generated answer directly resolves the factual legal problem without evasion or rambling.
* **Contextual Precision:** Measures whether the most authoritative statutory provisions are ranked at the top (#1, #2) rather than buried at the bottom.
* **Contextual Recall:** Measures the percentage of essential statutory provisions specified in ground truth that were successfully fetched.
* **Contextual Relevancy:** Ratio of retrieved sentences that carry substantive legal relevance to the query.

---

## 6. Mathematical Metrics Formulations

$$\text{Hit Rate@}K = \frac{1}{|Q|} \sum_{q \in Q} \mathbb{I}(\text{rank}(q) \leq K)$$

$$\text{MRR@}K = \frac{1}{|Q|} \sum_{q \in Q} \frac{1}{\min(\text{rank}(q), K + 1)}$$

$$\text{NDCG@}K = \frac{\text{DCG@}K}{\text{IDCG@}K}, \quad \text{where } \text{DCG@}K = \sum_{i=1}^{K} \frac{2^{\text{rel}_i} - 1}{\log_2(i + 1)}$$

$$\text{Contrastive Margin } \Delta = \frac{1}{N} \sum_{i=1}^N \left( \cos(\mathbf{e}_a, \mathbf{e}_p) - \cos(\mathbf{e}_a, \mathbf{e}_n) \right)$$

---

## 7. Dataset Distribution (75 Golden Scenarios)

The golden evaluation dataset spans **75 real-world Indian statutory scenarios** classified by complexity and legal domain:

| Pillar | Statutory Domain | Scenarios | Key Provisions Evaluated |
| :---: | :--- | :---: | :--- |
| **1** | **Negotiable Instruments Act, 1881** | 10 | Cheque bounce limitation Sec 138/142, Interim compensation Sec 143A, Company director liability Sec 141. |
| **2** | **Criminal Procedure & Bail (BNSS 2023)** | 12 | Anticipatory bail Sec 482, Default bail Sec 187, Mandatory crime scene videography Sec 105, Zero FIR Sec 173. |
| **3** | **Substantive Criminal Law (BNS 2023)** | 10 | Murder Sec 103, Snatching Sec 304, Organized crime Sec 111, Hit-and-run fatal negligence Sec 106(2). |
| **4** | **Law of Evidence (BSA 2023)** | 8 | Electronic certificate Sec 63 (ex-65B), Primary digital evidence Sec 57, Custodial confession bar Sec 23. |
| **5** | **Constitutional Law & Writs** | 8 | Habeas Corpus Art 32/226, Right to Privacy (Puttaswamy), Manifest arbitrariness Art 14, Self-incrimination Art 20(3). |
| **6** | **Civil Procedure & Specific Relief (CPC / SRA)** | 8 | Plaint rejection Order 7 Rule 11, Interim injunction Order 39, Res Judicata Sec 11, Specific performance Sec 10 SRA. |
| **7** | **Commercial, Arbitration & Insolvency (IBC)** | 8 | Sec 9 vs Sec 17 interim relief, Patent illegality challenge Sec 34, Sec 7 CIRP default, Sec 14 Moratorium. |
| **8** | **Consumer Protection & Cyber Law (CPA / IT / DPDP)** | 5 | Pecuniary consumer limits, Product liability, Intermediary safe harbor Sec 79 IT Act, Data Principal rights under DPDP. |
| **9** | **Property Law & Real Estate (TPA 1882 / RERA)** | 4 | Doctrine of Lis Pendens Sec 52, Gift deed validity Sec 123, Fraudulent transfer Sec 53, RERA Sec 18 builder refund. |
| **10** | **Family & Matrimonial Law (HMA / PWDVA)** | 2 | Mutual divorce cooling period waiver Sec 13B(2) HMA, Shared household rights under Domestic Violence Act. |
| **TOTAL** | | **75** | **Comprehensive legal coverage** |

---

## 8. Generated Artifacts & Output Reports

Every evaluation run writes persistent, structured machine-readable reports into the `evaluation/` directory:

| Report File | Associated Runner | Content |
| :--- | :--- | :--- |
| [`ablation_study_report.json`](file:///d:/Study/LegalDrishti%20AI/evaluation/ablation_study_report.json) | `evaluate_ablation_study.py` | Full 4-way comparative metrics across all 4 collections. |
| [`deepeval_rag_report.json`](file:///d:/Study/LegalDrishti%20AI/evaluation/deepeval_rag_report.json) | `evaluate_deepeval_rag.py` | Detailed RAG Triad scores, judge rationales, and timestamps. |
| [`retrieval_profiling_report.json`](file:///d:/Study/LegalDrishti%20AI/evaluation/retrieval_profiling_report.json) | `evaluate_retrieval_profiling.py` | Stage-by-stage latency profile (Dense, BM25, RRF, FlashRank). |
| [`embedding_evaluation_report.json`](file:///d:/Study/LegalDrishti%20AI/evaluation/embedding_evaluation_report.json) | `evaluate_embedding_triplets.py` | Contrastive margin, cosine similarity, and triplet accuracy. |

---

## 9. Running the Benchmark Suite

All evaluation scripts are fully autonomous, support GPU acceleration, and generate structured JSON reports.

### 1. 4-Way Comparative Ablation Benchmark (All Collections)
Compares V2, Hybrid FT, Hybrid Base, and V1 side-by-side using Groq LLM Judge:
```powershell
# Run on 5 scenarios (fast ablation):
& ".venv-gpu\Scripts\python.exe" evaluation/evaluate_ablation_study.py --samples 5

# Run on 15 scenarios:
& ".venv-gpu\Scripts\python.exe" evaluation/evaluate_ablation_study.py --samples 15

# Fast IR-only mode (skips LLM judge calls for instant retrieval metrics):
& ".venv-gpu\Scripts\python.exe" evaluation/evaluate_ablation_study.py --samples 25 --skip-llm
```

### 2. Production DeepEval RAG Triad (Groq LLM Judge)
Evaluates Production V2 on Faithfulness, Relevancy, Contextual Precision, and Recall:
```powershell
# Run on 10 legal scenarios:
& ".venv-gpu\Scripts\python.exe" evaluation/evaluate_deepeval_rag.py --samples 10

# Run with custom model (e.g. OpenAI):
& ".venv-gpu\Scripts\python.exe" evaluation/evaluate_deepeval_rag.py --samples 10 --model gpt-4o-mini
```

### 3. Full Information Retrieval & Hardware Timing Profiler
Profiles individual stage latencies (Dense vector search, BM25, RRF fusion, FlashRank reranking):
```powershell
& ".venv-gpu\Scripts\python.exe" evaluation/evaluate_retrieval_profiling.py --samples 15
```

### 4. Embedding Model Fine-Tuning Triplet Benchmark
Evaluates contrastive boundary separation on 100 anchor-positive-negative triplets:
```powershell
& ".venv-gpu\Scripts\python.exe" evaluation/evaluate_embedding_triplets.py
```

### 5. Fast Statutory Sanity Check
Validates that every scenario in the golden dataset successfully resolves target statutes:
```powershell
& ".venv-gpu\Scripts\python.exe" evaluation/evaluate_pipeline.py --all
```
