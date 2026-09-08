import uuid
from flashrank import Ranker, RerankRequest
from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.document import Document
from app.services.embeddings import get_embedding
from app.services.vector_store import (
    hybrid_search_chunks,
    hybrid_search_statutes,
)
from app.services.statute_router import route_query_to_statutes

_ranker: Ranker | None = None


def get_ranker() -> Ranker:
    global _ranker
    if _ranker is None:
        _ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
    return _ranker


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_n: int = 5,
) -> list[dict]:
    if not chunks:
        return []

    if len(chunks) <= top_n:
        return chunks

    ranker = get_ranker()

    passages = [
        {
            "id": idx,
            "text": c.get("chunk_text", ""),
            "meta": c,
        }
        for idx, c in enumerate(chunks)
    ]

    rerank_request = RerankRequest(query=query, passages=passages)
    ranked_passages = ranker.rerank(rerank_request)

    reranked: list[dict] = []
    for item in ranked_passages[:top_n]:
        chunk_data = item["meta"]
        chunk_data["cross_encoder_score"] = item.get("score")
        reranked.append(chunk_data)

    return reranked


async def retrieve_case_context(
    query: str,
    user_id: int,
    session: AsyncSession,
    case_id: int | None = None,
    candidate_pool_size: int = 20,
    top_k: int = 5,
    alpha: float = 0.5,
) -> list[dict]:
    query_vector = get_embedding(query)

    raw_candidates = hybrid_search_chunks(
        query_text=query,
        query_vector=query_vector,
        user_id=user_id,
        case_id=case_id,
        alpha=alpha,
        limit=candidate_pool_size,
    )

    if not raw_candidates:
        return []

    top_chunks = rerank_chunks(query=query, chunks=raw_candidates, top_n=top_k)

    doc_ids = {c["document_id"] for c in top_chunks if c.get("document_id")}
    titles_map: dict[int, str] = {}

    if doc_ids:
        stmt = select(Document.id, Document.title).where(Document.id.in_(doc_ids))
        res = await session.execute(stmt)
        for d_id, d_title in res.all():
            titles_map[d_id] = d_title

    enriched: list[dict] = []
    for c in top_chunks:
        d_id = c.get("document_id")
        enriched.append({
            "source_type": "case_document",
            "document_id": d_id,
            "document_title": titles_map.get(d_id, "Case Brief Document"),
            "page_number": c.get("page_number", 1),
            "chunk_text": c.get("chunk_text", ""),
            "score": c.get("cross_encoder_score") or c.get("score"),
        })

    return enriched


def retrieve_statutory_context(
    query: str,
    max_statutes: int = 5,
    candidate_pool_size: int = 20,
    top_k: int = 5,
    alpha: float = 0.5,
) -> list[dict]:
    routed = route_query_to_statutes(query, max_statutes=max_statutes)
    if not routed:
        return []

    target_pdfs = [r["pdf_name"] for r in routed]
    query_vector = get_embedding(query)

    raw_candidates = hybrid_search_statutes(
        query_text=query,
        query_vector=query_vector,
        target_pdf_names=target_pdfs,
        alpha=alpha,
        limit=candidate_pool_size,
    )

    if not raw_candidates:
        return []

    top_chunks = rerank_chunks(query=query, chunks=raw_candidates, top_n=top_k)

    results: list[dict] = []
    for c in top_chunks:
        results.append({
            "source_type": "global_statute",
            "document_title": c.get("pdf_name", "Indian Bare Act"),
            "page_number": c.get("page_number", 1),
            "chunk_text": c.get("chunk_text", ""),
            "score": c.get("cross_encoder_score") or c.get("score"),
        })

    return results


def format_dual_stream_context(
    case_chunks: list[dict],
    statute_chunks: list[dict],
) -> str:
    sections = []

    if case_chunks:
        case_blocks = []
        for idx, c in enumerate(case_chunks, 1):
            block = f"[Case Record Source {idx}: '{c['document_title']}', Page {c['page_number']}]\n{c['chunk_text']}"
            case_blocks.append(block)
        sections.append("EVIDENTIARY BRIEF ON RECORD (CLIENT CASE FILES):\n" + "\n\n".join(case_blocks))

    if statute_chunks:
        statute_blocks = []
        for idx, c in enumerate(statute_chunks, 1):
            block = f"[Statutory Source {idx}: '{c['document_title']}', Page {c['page_number']}]\n{c['chunk_text']}"
            statute_blocks.append(block)
        sections.append("GOVERNING STATUTORY PROVISIONS & BARE ACT EXCERPTS:\n" + "\n\n".join(statute_blocks))

    return "\n\n======================================================================\n\n".join(sections)


async def generate_grounded_legal_answer(
    query: str,
    user_id: int,
    session: AsyncSession,
    case_id: int | None = None,
    candidate_pool_size: int = 20,
    top_k: int = 5,
    alpha: float = 0.5,
) -> dict:
    settings = get_settings()

    case_chunks = await retrieve_case_context(
        query=query,
        user_id=user_id,
        session=session,
        case_id=case_id,
        candidate_pool_size=candidate_pool_size,
        top_k=top_k,
        alpha=alpha,
    )

    statute_chunks = retrieve_statutory_context(
        query=query,
        max_statutes=5,
        candidate_pool_size=candidate_pool_size,
        top_k=top_k,
        alpha=alpha,
    )

    all_chunks = case_chunks + statute_chunks

    if not all_chunks:
        return {
            "answer": "The brief placed on record and the statutory repository do not disclose information matching this inquiry.",
            "sources": [],
            "grounded": False,
        }

    context_text = format_dual_stream_context(case_chunks, statute_chunks)

    system_prompt = (
        "You are LegalDrishti AI, acting as a distinguished Senior Advocate of the Indian Bar with decades "
        "of courtroom and chamber advisory experience.\n\n"
        "YOUR PERSONA & DEMEANOR:\n"
        "- Tone: Poised, incisive, intellectually rigorous, yet remarkably lucid. You communicate with the dignified "
        "clarity of a seasoned counsel who values substance and precision over hollow jargon.\n"
        "- Legal Mindset: Think like an astute trial and appellate counsel. Distinguish sharply between mere averments (claims), "
        "documentary evidence, statutory requirements, and judicial findings.\n"
        "- Intellectual Engagement: When the user raises a penetrating counter-question or challenges an interpretation, "
        "acknowledge the acumen of their inquiry with professional courtesy before analyzing what the brief actually substantiates.\n\n"
        "THE CARDINAL RULE — UNCOMPROMISING CANDOR & ZERO HALLUCINATION:\n"
        "1. NO APOLOGIES, NO WEAK ARGUMENTS: If a fact, date, clause, or answer is NOT present in the provided excerpts, "
        "NEVER say 'I am sorry', 'I apologize', or 'As an AI...'. Never produce vague, confusing, or speculative fluff "
        "to fill the silence. A Senior Advocate states the absence of evidence firmly, plainly, and directly.\n"
        "2. DIRECT STATEMENT ON ABSENCE OF RECORD: If the excerpts do not contain the answer, state decisively:\n"
        "   'The record before me does not disclose [specific topic/fact]. The provided documents are silent on this point.'\n"
        "3. STRICT CITATION DISCIPLINE: Every factual claim, date, monetary figure, or statutory rule you affirm MUST be "
        "immediately anchored to its source in brackets: e.g., [Document Title, Page X]. An unreferenced assertion is invalid.\n"
        "4. ZERO FABRICATION: Never invent FIR numbers, police stations, dates, names of parties, penal sections, "
        "or lower court orders.\n"
        "5. DUAL SYNTHESIS: When both Case Record and Statutory Excerpts are provided, apply the statutory provisions "
        "directly to the facts on record. If only Statutory Excerpts are provided, deliver a structured analysis of the law."
    )

    user_prompt = (
        "BRIEF & EXCERPTS ON RECORD:\n"
        "======================================================================\n"
        f"{context_text}\n"
        "======================================================================\n\n"
        f"INQUIRY / COUNTER-QUESTION: {query}\n\n"
        "Counsel, review the brief above and deliver your grounded legal analysis and opinion. "
        "If the record is silent on any point, state it directly without apology or speculation:"
    )

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model or "gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    answer_text = response.choices[0].message.content or ""

    sources = [
        {
            "source_type": c.get("source_type"),
            "document_title": c["document_title"],
            "page_number": c["page_number"],
            "score": c.get("score"),
        }
        for c in all_chunks
    ]

    return {
        "answer": answer_text.strip(),
        "sources": sources,
        "grounded": True,
    }
