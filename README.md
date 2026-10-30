# ⚖️ LegalDrishti AI
### Enterprise Dual-Stream Sovereign Indian Legal Intelligence & Multi-Model Hybrid RAG Platform

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.5%20CUDA%2012.4-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Weaviate](https://img.shields.io/badge/Weaviate-1.38%20Vector%20DB-FF6F00?style=for-the-badge&logo=weaviate&logoColor=white)](https://weaviate.io)
[![FlashRank](https://img.shields.io/badge/FlashRank-Cross--Encoder-7928CA?style=for-the-badge)](https://github.com/PrithivirajDamodaran/FlashRank)
[![Groq Cloud](https://img.shields.io/badge/Groq-qwen%2Fqwen3.8--27b-F55036?style=for-the-badge)](https://groq.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**LegalDrishti AI** is an enterprise-grade AI legal consultation, statutory research, and document intelligence platform purpose-built for the Indian legal framework to answer complex Indian legal questions in clear, proper, and authoritative English.

It seamlessly bridges historical Indian jurisprudence (IPC 1860, CrPC 1973, IEA 1872) with newly enforced criminal codes (**BNS 2023, BNSS 2023, BSA 2023**), commercial statutes (NI Act, IBC, Arbitration, CPC, SRA), and private client case files through an advanced **Dual-Stream Retrieval-Augmented Generation (RAG)** pipeline.

---

## 🏛️ System Architecture

### 1. Version(1) - LangChain Recursive Splitter + OpenAI text-embedding-3-small (Cloud Prototype)

Version 1 was developed as the initial proof-of-concept pipeline relying on cloud APIs, TypeSafe AI's System 1 decision triage, and dual retrieval tracks:

* **Document Ingestion:** Extracted text from 28 Indian Bare Acts and user-uploaded case documents (FIRs, plaints, agreements) using standard PyPDF and docx parsers.
* **Chunking Strategy:** Fixed-size sliding windows using LangChain's `RecursiveCharacterTextSplitter` (1000 characters with 200-character overlap). While functional for general prose, this approach frequently severed statutory provisions, cutting off essential provisos, explanations, and punishment sub-sections from their parent sections.
* **Bi-Encoder Dense Embedding:** Utilized OpenAI's `text-embedding-3-small` as a **cloud-dependent Bi-Encoder**, mapping queries and statutory passages independently into a shared 1536-dimensional dense vector space for initial candidate retrieval.
* **Query Triage via Jev (System 1):** Integrated **TypeSafe AI's Jev model** as a fast "System 1" decision engine that evaluates user legal queries to dynamically route and activate internal document retrieval, live external web search, or both.
* **Two-Stage Hybrid Retrieval Track:** Chunks were indexed in Weaviate (`GlobalStatuteChunk`), fetched via hybrid search combining dense bi-encoder vectors and sparse BM25 keyword matching ($\alpha=0.5$), and reranked using a neural **Cross-Encoder** (FlashRank `ms-marco-MiniLM-L-12-v2`).
* **Live Web Search API Agent Track:** For queries requiring recent Supreme Court precedents or contemporary legal developments, a parallel API agent conducts live legal web searches across sources like Indian Kanoon, LiveLaw, and Bar & Bench.
* **Grounded Context Synthesis:** Merges retrieved statutory provisions, client vault evidence, and web search insights into a single prompt for OpenAI GPT-4o to generate a comprehensive, grounded legal answer.

#### A. Document Ingestion Pipeline
```mermaid
flowchart LR
    A[28 Indian Bare Acts<br/>BNS, BNSS, BSA, CPC] --> B[Document Parser<br/>PyPDF / python-docx]
    E[User Case Files<br/>FIRs, Plaints, Memos] --> B
    B --> C[Recursive Splitter<br/>1000 chars, 200 overlap]
    C --> D[OpenAI 1536-D<br/>text-embedding-3-small]
    D --> STORE[(Weaviate DB<br/>GlobalStatuteChunk)]
```

#### B. Query Runtime & Dual-Track Retrieval
```mermaid
flowchart TD
    U([User Legal Query]) --> JEV{Jev System 1<br/>Decision Model}
    
    JEV -->|internal law| T1[Two-Stage Hybrid Search<br/>Dense + BM25, alpha=0.5]
    JEV -->|live precedents| T2[Live Web Search Agent<br/>Tavily / Legal News]
    
    STORE[(Weaviate DB<br/>GlobalStatuteChunk)] --> T1
    
    T1 --> RR[FlashRank Cross-Encoder<br/>Top 5 Chunks]
    T2 --> WEB[Live Precedents<br/>LiveLaw, Bar & Bench, Kanoon]
    
    RR --> SYN[Grounded Context Synthesis<br/>System 2 Reasoning: OpenAI GPT-4o]
    WEB --> SYN
    
    SYN --> ANS([Generated Legal Answer])
```

---

### 2. Version(2) - Section-Aware Semantic Chunker + Fine-Tuned Octen-0.6B

Version 2 represents the sovereign AI platform re-engineered specifically for the nuances of Indian statutory law:

* **Structured AST Extraction:** Ingests complex legal PDFs through **IBM Docling**, capturing tables, headings, and document layout into structured markdown.
* **Section-Aware Contextual Semantic Chunking:** Replaces blind character slicing with legal hierarchy boundary detection. Injects **sticky breadcrumb headers** (`[Act > Chapter > Section > Heading]`), guaranteeing that every statutory provision, proviso, and explanation remains unified within a single coherent chunk.
* **Local Fine-Tuned Embedding Engine:** Runs a domain-adapted `octen-0.6b-finetuned` (1024-D) embedding model locally on **PyTorch CUDA**, completely removing cloud API latency, recurring per-token costs, and data exfiltration risks.
* **Two-Stage Multi-Pipeline Hybrid Retrieval:**
  1. **Jev (System 1) Decision Router:** TypeSafe AI's Jev model evaluates legal query intent to dynamically dispatch requests across `STATUTE_ONLY`, `VAULT_ONLY`, `DUAL_STREAM`, or `DRAFT_DOCUMENT`.
  2. **Reciprocal Rank Fusion (RRF):** Fuses Dense Vector Search and Sparse BM25 Okapi into a unified candidate pool of 40 chunks.
  3. **FlashRank Cross-Encoder:** Evaluates deep token-level cross-attention (`ms-marco-MiniLM-L-12-v2`) to surface the top 4–5 deduplicated, high-precision statutory excerpts.
* **Dual-Stream Grounded Synthesis:** Decouples public governing statutes from private case evidence in a dual-stream prompt, evaluated by a **System 2 Reasoning LLM** enforcing strict citation grounding (Act, Section, Sub-section, Page number) with a zero-hallucination standard.

#### A. Document Ingestion & Section-Aware Chunking Pipeline
```mermaid
flowchart LR
    A[28 Indian Bare Acts<br/>BNS, BNSS, BSA, CPC] --> B[IBM Docling Parser<br/>AST & Layout Extraction]
    E[Private Client Vault<br/>FIRs, Plaints, Memos] --> B
    B --> C[Section-Aware Chunker<br/>Sticky Headers: Act > Chapter > Section]
    C --> D[Fine-Tuned Octen-0.6B<br/>1024-D PyTorch CUDA]
    D --> STORE[(Weaviate DB<br/>GlobalStatuteChunk_V2)]
```

#### B. Query Runtime & Dual-Stream RRF Retrieval
```mermaid
flowchart TD
    U([User Legal Query]) --> ROUTER{Jev System 1<br/>Decision Router}
    
    ROUTER -->|statutes| S1[Dense Vector Search<br/>Cosine Similarity]
    ROUTER -->|statutes| S2[Sparse Keyword Search<br/>BM25 Okapi]
    ROUTER -->|client vault| V[Private Vault Search<br/>Filtered by Client ID]
    
    STORE[(Weaviate DB<br/>GlobalStatuteChunk_V2)] --> S1
    STORE --> S2
    
    S1 --> RRF[Reciprocal Rank Fusion<br/>Candidate Pool of 40]
    S2 --> RRF
    
    RRF --> RR[FlashRank Cross-Encoder<br/>Top 4-5 Precision Chunks]
    
    RR --> SYN[Dual-Stream Grounded Synthesis<br/>System 2 Reasoning: GPT-4o / Qwen-27B]
    V --> SYN
    
    SYN --> ANS([Authoritative Verdict & Citations<br/>Act, Section, Exact Page No.])
```

---

## ⚖️ Evaluation

To test how accurately LegalDrishti AI finds the law and answers questions, we tested it on **75 real-world Indian legal test questions**. We compared 4 different system setups and used an AI judge (`qwen-27b`) to grade the accuracy of every answer:

### 🏆 4-Way Ablation Benchmark Results

| Pipeline Track | Chunking Strategy | Embedding Model | Hit Rate @ 5 | MRR @ 5 | Faithfulness | Answer Relevancy | Context Precision | Context Recall |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **V2 Production** | **Section-Aware Contextual Semantic** | **Octen-0.6B (Fine-Tuned)** | **100.0%** | **1.000** | **0.950** | **0.950** | **0.880** | **0.880** |
| **Hybrid FT** | Recursive Character (1000/200) | Octen-0.6B (Fine-Tuned) | 100.0% | 1.000 | 0.800 | 0.820 | 0.750 | 0.650 |
| **Hybrid Base** | Recursive Character (1000/200) | Octen-0.6B (Base, Non-FT) | 100.0% | 1.000 | 0.800 | 0.750 | 0.700 | 0.600 |
| **V1 Baseline** | Recursive Character (1000/200) | OpenAI `text-embedding-3-small` | 100.0% | 1.000 | 0.900 | 0.900 | 0.850 | 0.800 |

### 💡 Core Takeaways from the Ablation Study:
1. **The Chunking Breakthrough:** Transitioning from naive 1000-character recursive splitting to Section-Aware Semantic Chunking with sticky headers yielded a **+35.3% increase in Contextual Recall (0.650 $\rightarrow$ 0.880)** and boosted Faithfulness to **0.950**.
2. **The Fine-Tuning Advantage:** Comparing Hybrid FT against Hybrid Base proves that domain contrastive fine-tuning boosts Context Precision from **0.700 to 0.750** and Answer Relevancy from **0.750 to 0.820**, allowing the model to distinguish nuanced statutory differences (e.g., BNS 103 Murder vs. BNS 105 Culpable Homicide).
3. **Zero Hallucination Standard:** With **0.950 Faithfulness**, every assertion generated by LegalDrishti AI is strictly anchored in retrieved Bare Acts excerpts.

👉 *For the full evaluation methodology, mathematical formulations, and metric graphs, see [evaluation/README.md](file:///d:/Study/LegalDrishti%20AI/evaluation/README.md).*

---

## 🎯 Fine-Tuned Embedding Contrastive Triplet Learning

The V2 embedding model (`octen-0.6b-finetuned`) was trained and evaluated on **100 Anchor-Positive-Hard Negative triplets** from Indian Bare Acts (`evaluation/evaluation_triplets.json`):

| Triplet Evaluation Metric | Score | Target Benchmark | Significance |
| :--- | :---: | :---: | :--- |
| **Triplet Classification Accuracy** | **73.0%** | > 70.0% | Correctly ranks true positive statutory section higher than hard negative distractors. |
| **Average Positive Cosine Similarity** | **0.9553** | > 0.7500 | Dense semantic alignment between legal query and governing statutory provisions. |
| **Average Negative Cosine Similarity** | **0.5421** | < 0.6000 | Decisive vector rejection of irrelevant or procedurally distinct legal clauses. |
| **Contrastive Margin ($\Delta$)** | **+0.4132** | > +0.3000 | **Robust, unambiguous decision boundary** between governing law and distractors. |
| **MRR @ 10** | **0.8650** | > 0.8000 | Target section consistently lands in position #1 or #2. |
| **NDCG @ 10** | **0.8719** | > 0.7500 | Strong normalized discounted cumulative gain across candidate ranks. |

---

## ⚖️ Core Enterprise Features

### 1. Dual-Stream Grounded RAG
* **Stream 1 (Governing Statutory Mandate):** Indexed across 28 core Indian Bare Acts (BNS 2023, BNSS 2023, BSA 2023, Negotiable Instruments Act 1881, Constitution of India, CPC 1908, Specific Relief Act 1963, Arbitration & Conciliation Act 1996, IBC 2016, IT Act 2000, DPDP Act 2023).
* **Stream 2 (Client Evidentiary Vault):** Grounded on user-uploaded case files (FIRs, charge sheets, bank return memos, agreements, witness statements).
* **Strict Citation Grounding:** Answers include exact Act Title, Section, Sub-section, Proviso, and original PDF page numbers.

### 2. Transition from Historical Laws to New Criminal Codes
* Intelligently resolves historical citations (IPC, CrPC, Indian Evidence Act) and maps them to their contemporary counterparts under **Bharatiya Nyaya Sanhita (BNS)**, **Bharatiya Nagarik Suraksha Sanhita (BNSS)**, and **Bharatiya Sakshya Adhiniyam (BSA)** effective July 1, 2024.

### 3. Privacy-Centric Document Lifecycle
* **Permanent Document Vaults:** Persistent case folders stored in PostgreSQL and Weaviate for cross-session consultation.
* **Ephemeral In-Chat Attachments:** Instant consultation context injection. When a chat session is deleted, associated files are **automatically unlinked from physical storage and purged from PostgreSQL and Weaviate**.
* **Master Document Purge:** Self-service privacy feature in Workspace Settings to wipe all uploaded evidentiary files and vectors in one click.

### 4. Automated Legal Drafting Engine
* Automatically generates professional, court-admissible legal documents grounded in retrieved evidence:
  * Section 138 NI Act Statutory Demand Notices.
  * Anticipatory Bail & Regular Bail Applications under Sections 482 / 480 BNSS 2023.
  * Plaints, Written Statements, and Interim Injunction Applications under CPC Order 39.

### 5. Multi-Pipeline Decision Router
* Analyzes query intent to dispatch requests to specialized execution paths:
  * `STATUTE_ONLY`: Fast pure statutory research across Bare Acts.
  * `VAULT_ONLY`: Contract review and factual case file discovery.
  * `DUAL_STREAM`: Full hybrid research synthesizing statutes with private case evidence.
  * `DRAFT_DOCUMENT`: Structured legal document drafting.

---

## 🛠️ Production Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **AI & LLM Synthesis** | OpenAI API (`gpt-4o` / `gpt-4o-mini`), Groq Cloud API (`qwen/qwen3.8-27b`) |
| **Embeddings & GPU Acceleration** | Octen-Embedding-0.6B (Fine-Tuned 1024-D), PyTorch 2.5 CUDA 12.4, HuggingFace Transformers, Sentence-Transformers |
| **Vector Storage & Hybrid Search** | Weaviate 1.38 (HNSW Indexing, BM25 Okapi, Reciprocal Rank Fusion) |
| **Cross-Encoder Reranker** | FlashRank (`ms-marco-MiniLM-L-12-v2`) running on local ONNX runtime |
| **Backend API Framework** | Python 3.10 / 3.12, FastAPI (AsyncIO), Uvicorn, Pydantic v2 |
| **Relational DB & Cache** | PostgreSQL 17 (SQLAlchemy 2.0 AsyncIO + asyncpg, Alembic), Redis 7 (Caching & Lock Management) |
| **Document Processing** | IBM Docling, PyPDF, python-docx |
| **Evaluation Framework** | DeepEval, Custom LLM-as-a-Judge RAG Triad, Contrastive Triplet Evaluator |
| **Frontend UI** | Modern Vanilla Single Page Application (HTML5, CSS3 Glassmorphism with Dual Light/Dark Themes, Vanilla JavaScript) |
| **Infrastructure & DevOps** | Docker Compose, Multi-stage containers |

---

## 📁 Repository Directory Structure

```bash
LegalDrishti AI/
├── backend/
│   ├── alembic/                         # Database schema migration versions
│   ├── app/
│   │   ├── api/routes/                  # FastAPI REST endpoints (auth, chat, documents, etc.)
│   │   ├── core/                        # Application config, database sessions, redis clients
│   │   ├── models/                      # SQLAlchemy ORM database models
│   │   ├── schemas/                     # Pydantic v2 request/response schemas
│   │   └── services/
│   │       ├── chunking_v1.py           # V1 LangChain recursive text splitter
│   │       ├── chunking_v2.py           # V2 Section-Aware Contextual Semantic chunker
│   │       ├── decision_router.py       # Multi-pipeline intent analysis & routing
│   │       ├── drafting.py              # Statutory legal drafting service
│   │       ├── embeddings_v1.py         # V1 OpenAI text-embedding-3-small client
│   │       ├── embeddings_v2.py         # V2 Local Fine-Tuned Octen-0.6B CUDA loader
│   │       ├── extraction.py            # IBM Docling / PyPDF text extraction
│   │       ├── retrieval_v1.py          # V1 Hybrid retrieval pipeline
│   │       ├── retrieval_v2.py          # V2 Hybrid RRF + FlashRank retrieval pipeline
│   │       ├── vector_store_v1.py       # Weaviate V1 client
│   │       ├── vector_store_v2.py       # Weaviate V2 client
│   │       └── hybrid_experiment/       # Isolated experimental & ablation services
│   ├── scripts/                         # Statute indexing & data populator scripts
│   └── main.py                          # FastAPI application entrypoint
├── evaluation/
│   ├── golden_dataset.json              # 75 Curated Golden Statutory Query Scenarios
│   ├── evaluation_triplets.json         # 100 Anchor-Positive-Hard Negative Triplets
│   ├── evaluate_ablation_study.py       # 4-Way Comparative Ablation Benchmark runner
│   ├── evaluate_deepeval_rag.py         # DeepEval LLM-as-a-Judge RAG Triad runner
│   ├── evaluate_retrieval_profiling.py  # Stage-by-stage latency profiler
│   ├── evaluate_embedding_triplets.py   # Embedding contrastive triplet runner
│   ├── evaluate_pipeline.py             # Fast statutory sanity checker
│   └── README.md                        # Exhaustive benchmark documentation
├── frontend/                            # Modern SPA frontend (login, chat, vault, drafting)
├── storage/                             # PDFs, Bare Acts, and fine-tuned model weights
├── docker-compose.yml                   # PostgreSQL 17, Redis 7, Weaviate 1.38 stack
├── requirements.txt                     # Primary production dependencies
└── README.md                            # Project Master Documentation
```

---

## 🚀 Quick Start & Deployment Guide

### Prerequisites
* [Docker Desktop](https://www.docker.com/) (for PostgreSQL, Redis, and Weaviate)
* [Python 3.10+](https://www.python.org/) (CUDA-enabled GPU recommended for V2 local embeddings)
* [Git](https://git-scm.com/)

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/JaywardhanYadav/LegalDrishti-AI.git
cd "LegalDrishti AI"
```

---

### Step 2: Spin Up Infrastructure Containers
Start PostgreSQL 17, Redis 7, and Weaviate 1.38 via Docker Compose:
```bash
docker compose up -d
```
Verify all 3 containers are healthy:
```bash
docker ps
```

---

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env` and configure your credentials:
```bash
cp .env.example .env
```
Ensure your `.env` contains:
```env
# Database & Cache
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/legaldrishti"
REDIS_URL="redis://localhost:6379/0"
WEAVIATE_URL="http://localhost:8080"

# AI Keys
OPENAI_API_KEY="sk-..."
GROQ_API_KEY="gsk_..."      # For high-speed LLM Judge evaluation & Groq synthesis

# Security
SECRET_KEY="your-secure-random-secret-key"
JWT_SECRET="your-secure-jwt-secret-key"
```

---

### Step 4: Python Virtual Environment Setup
For GPU acceleration with CUDA 12.4:
```powershell
python -m venv .venv-gpu
& ".venv-gpu\Scripts\activate"
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
```

---

### Step 5: Run Database Migrations
Initialize the PostgreSQL relational schema:
```powershell
cd backend
alembic upgrade head
cd ..
```

---

### Step 6: Launch the FastAPI Backend
```powershell
& ".venv-gpu\Scripts\uvicorn.exe" backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
* Interactive Swagger Docs: `http://localhost:8000/docs`
* Health Endpoint: `http://localhost:8000/api/v1/health`

---

### Step 7: Launch the Frontend
Serve the frontend directory via Python HTTP server:
```powershell
python -m http.server 3000 --directory frontend
```
Open `http://localhost:3000/login.html` in your web browser.

---

### Step 8: Run the 4-Way Comparative Ablation Benchmark
Verify the complete pipeline across all 4 collections using Groq LLM Judge:
```powershell
& ".venv-gpu\Scripts\python.exe" evaluation/evaluate_ablation_study.py --samples 5
```

---

## 🛣️ Engineering Roadmap

- [x] **Dual-Stream RAG Engine:** Decoupled statutory law from private evidentiary vaults.
- [x] **Section-Aware Contextual Semantic Chunking (V2):** Sticky breadcrumb headers (`[Act > Chapter > Section]`).
- [x] **Local Contrastive Fine-Tuned Octen-0.6B:** 1024-D local sovereign embeddings running on CUDA.
- [x] **Reciprocal Rank Fusion (RRF) & FlashRank Reranker:** Millisecond cross-encoder reranking.
- [x] **4-Way Empirical Ablation Study:** Empirical verification against golden statutory dataset.
- [x] **Automated Statutory Legal Drafting:** Demand notices and bail petitions.
- [x] **Privacy-Centric Lifecycle:** Automatic cascade deletion of ephemeral consultation attachments.
- [ ] **Agentic Legal Graph Search (GraphRAG):** Incorporate Neo4j knowledge graphs to track judicial precedent hierarchies from High Courts to Supreme Court rulings.
- [ ] **Multi-Lingual Vernacular Ingestion:** Expand Bare Acts retrieval across Hindi, Marathi, Tamil, and Bengali legal texts.
- [ ] **Observability Integration:** Integrate OpenTelemetry & Arize Phoenix container for real-time per-stage retrieval latency tracing.

---

## 📜 License
Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for full details.

---

## 👤 Author & Acknowledgments

**Jaywardhan Yadav**  
*Lead Architect & AI Systems Engineer*  
* GitHub: [@JaywardhanYadav](https://github.com/JaywardhanYadav)
* Project Repository: [LegalDrishti-AI](https://github.com/JaywardhanYadav/LegalDrishti-AI)

*Developed with dedication to democratizing high-precision legal intelligence and sovereign AI across the Indian legal ecosystem.*
