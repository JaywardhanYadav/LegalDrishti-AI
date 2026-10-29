"""
Retrieval & RAG Pipeline for Recursive_Base_Octen Hybrid (Testing Track)
========================================================================
Architecture:
- Chunking: V1 IBM Docling + LangChain RecursiveCharacterTextSplitter
- Embedding: Base (Non-Fine-Tuned) Octen-Embedding-0.6B (1024-D Dense)
- Storage: Weaviate collection 'Recursive_Base_Octen'
- Reranker: FlashRank ms-marco-MiniLM-L-12-v2
- Synthesis: OpenAI GPT-4o / GPT-4o-mini grounded in retrieved statutory text
"""
from __future__ import annotations

import os
from openai import OpenAI
from flashrank import Ranker, RerankRequest

from app.core.config import get_settings
from app.services.hybrid_experiment.embeddings_base_octen import get_embedding_base_octen
from app.services.hybrid_experiment.vector_store_recursive_base_octen import (
    hybrid_search_recursive_base_octen,
    RECURSIVE_BASE_OCTEN_COLLECTION_NAME,
)

_RERANKER_MODEL = "ms-marco-MiniLM-L-12-v2"
_ranker: Ranker | None = None


def get_ranker() -> Ranker:
    global _ranker
    if _ranker is None:
        _ranker = Ranker(model_name=_RERANKER_MODEL, cache_dir="/tmp/flashrank")
    return _ranker


def rerank_chunks(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    if not chunks:
        return []

    ranker = get_ranker()
    passages = [
        {"id": idx, "text": chunk.get("chunk_text", "")}
        for idx, chunk in enumerate(chunks)
    ]

    rerank_request = RerankRequest(query=query, passages=passages)
    ranked_results = ranker.rerank(rerank_request)

    top_results = ranked_results[:top_k]
    reranked_chunks = []
    for r in top_results:
        original_chunk = chunks[r["id"]].copy()
        original_chunk["rerank_score"] = r["score"]
        reranked_chunks.append(original_chunk)

    return reranked_chunks


def retrieve_statutory_context_recursive_base_octen(
    query: str,
    target_statutes: list[str] | None = None,
    candidate_pool_size: int = 40,
    top_k: int = 5,
    alpha: float = 0.5,
) -> list[dict]:
    """
    Hybrid dense (Base Octen 1024-D) + BM25 sparse search over 'Recursive_Base_Octen'
    followed by FlashRank neural reranking.
    """
    target_pdfs = target_statutes or []
    query_vector = get_embedding_base_octen(query)

    raw_candidates = hybrid_search_recursive_base_octen(
        query_text=query,
        query_vector=query_vector,
        target_pdf_names=target_pdfs,
        alpha=alpha,
        limit=candidate_pool_size,
    )

    if not raw_candidates:
        return []

    return rerank_chunks(query=query, chunks=raw_candidates, top_k=top_k)


def format_context_for_prompt(statute_chunks: list[dict]) -> str:
    sections = []
    if statute_chunks:
        statute_text = "\n\n".join(
            f"--- STATUTE SOURCE: {c.get('pdf_name')} (Page {c.get('page_number', 'N/A')}, Chunk {c.get('chunk_index')}) ---\n{c.get('chunk_text')}"
            for c in statute_chunks
        )
        sections.append(f"### STATUTORY ENACTMENTS:\n{statute_text}")

    return "\n\n".join(sections) if sections else "No statutory context available."


def generate_grounded_legal_answer_recursive_base_octen(
    query: str,
    target_statutes: list[str] | None = None,
    top_k: int = 5,
) -> dict:
    """
    Executes end-to-end RAG over the Recursive_Base_Octen collection.
    """
    retrieved_chunks = retrieve_statutory_context_recursive_base_octen(
        query=query,
        target_statutes=target_statutes,
        candidate_pool_size=40,
        top_k=top_k,
    )

    context_str = format_context_for_prompt(retrieved_chunks)

    system_prompt = (
        "You are LegalDrishti AI (Recursive_Base_Octen Hybrid Track), an advanced legal research system.\n"
        "This pipeline evaluates the performance of LangChain Recursive Character Chunking paired with "
        "the BASE (non-fine-tuned) Octen-Embedding-0.6B (1024-D) vector model.\n"
        "STRICT INSTRUCTIONS:\n"
        "1. Ground your answer solely on the provided statutory context.\n"
        "2. Cite the exact Act name, Section, and Page numbers explicitly.\n"
        "3. If the context does not contain the answer, explicitly state that statutory grounds are insufficient.\n"
        "4. Never hallucinate provisions or cite unverified sections."
    )

    user_prompt = f"### USER QUERY:\n{query}\n\n### RETRIEVED STATUTORY CONTEXT:\n{context_str}\n\n### ANALYSIS:"

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )

    answer = response.choices[0].message.content or ""

    return {
        "pipeline": "Recursive_Base_Octen (Docling/LangChain + Base Octen 1024-D)",
        "collection": RECURSIVE_BASE_OCTEN_COLLECTION_NAME,
        "query": query,
        "answer": answer,
        "sources": [
            {
                "pdf_name": c.get("pdf_name"),
                "page_number": c.get("page_number"),
                "chunk_index": c.get("chunk_index"),
                "rerank_score": c.get("rerank_score"),
                "heading": c.get("heading", ""),
                "snippet": c.get("chunk_text", "")[:300] + "...",
            }
            for c in retrieved_chunks
        ],
    }
