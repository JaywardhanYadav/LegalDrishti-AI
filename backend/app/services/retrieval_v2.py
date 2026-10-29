from collections.abc import AsyncGenerator
from openai import AsyncOpenAI, OpenAI
from flashrank import Ranker, RerankRequest

from app.core.config import get_settings
from app.services.decision_router import decide_query_action, MultiPipelineDecision
from app.services.embeddings_v2 import get_embedding_v2
from app.services.vector_store_v2 import (
    hybrid_search_statutes_v2,
    hybrid_search_case_chunks_v2,
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


def retrieve_statutory_context_v2(
    query: str,
    target_statutes: list[str] | None = None,
    candidate_pool_size: int = 40,
    top_k: int = 5,
    alpha: float = 0.5,
) -> list[dict]:
    """
    V2 Retrieval using Local 1024-D Vectors + GlobalStatuteChunk_V2 + FlashRank.
    Pure end-to-end dense + BM25 hybrid retrieval across all statutes with zero regex / n-gram routing.
    """
    target_pdfs = target_statutes or []
    query_vector = get_embedding_v2(query)

    raw_candidates = hybrid_search_statutes_v2(
        query_text=query,
        query_vector=query_vector,
        target_pdf_names=target_pdfs,
        alpha=alpha,
        limit=candidate_pool_size,
    )

    if not raw_candidates:
        return []

    return rerank_chunks(query=query, chunks=raw_candidates, top_k=top_k)


def retrieve_case_context_v2(
    query: str,
    user_id: int,
    case_id: int | None = None,
    candidate_pool_size: int = 40,
    top_k: int = 5,
    alpha: float = 0.5,
) -> list[dict]:
    """
    V2 Vault Retrieval using Local 1024-D Vectors + LegalDocumentChunk_V2 + FlashRank.
    """
    query_vector = get_embedding_v2(query)

    raw_candidates = hybrid_search_case_chunks_v2(
        query_text=query,
        query_vector=query_vector,
        user_id=user_id,
        case_id=case_id,
        alpha=alpha,
        limit=candidate_pool_size,
    )

    if not raw_candidates:
        return []

    return rerank_chunks(query=query, chunks=raw_candidates, top_k=top_k)


async def generate_grounded_legal_answer_v2(
    query: str,
    user_id: int,
    case_id: int | None = None,
    include_statutes: bool = True,
    system_prompt_override: str | None = None,
) -> dict:
    """
    V2 Grounded Legal Synthesis (Structured Result):
    Uses Local 1024-D Retrieval + FlashRank Reranker + OpenAI GPT-4o LLM Generation.
    Returns: {"answer": str, "sources": list, "grounded": bool}
    """
    # 0. Triage & Route with Jev Multi-Pipeline Decision Engine
    decision = decide_query_action(query=query, has_vault_documents=bool(case_id))

    # Check if pure conversational/greeting without any active data pipeline
    is_pure_conversational = decision.is_conversational and not (
        decision.search_statutes or decision.search_vault or decision.search_web
    )

    if is_pure_conversational:
        clarification_msg = decision.suggested_clarification or (
            "Greetings. I am LegalDrishti AI. Please provide the details of your legal issue, "
            "relevant facts, or specific statutory provisions you wish to analyze."
        )
        return {
            "answer": clarification_msg,
            "sources": [],
            "grounded": True,
            "decision": decision.model_dump(),
        }

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    context_blocks = []
    sources = []

    # Branch 1: Dynamically execute Client Case Vault Search if switch is active
    if decision.search_vault and case_id:
        case_chunks = retrieve_case_context_v2(query=query, user_id=user_id, case_id=case_id, top_k=5)
        if case_chunks:
            case_texts = [f"[Document ID: {c.get('document_id')} | Page: {c.get('page_number')}]\n{c.get('chunk_text')}" for c in case_chunks]
            context_blocks.append("--- RELEVANT CASE DOCUMENTS & VAULT EVIDENCE ---\n" + "\n\n".join(case_texts))
            for c in case_chunks:
                sources.append({
                    "source_type": "case_vault",
                    "document_title": f"Case Document #{c.get('document_id')}",
                    "page_number": c.get("page_number", 1),
                    "score": float(c.get("rerank_score", 0.0)),
                })

    # Branch 2: Dynamically execute 28 Bare Acts Statutory Search if switch is active
    if include_statutes and decision.search_statutes:
        statute_chunks = retrieve_statutory_context_v2(query=query, top_k=5)
        if statute_chunks:
            statute_texts = [f"[{c.get('pdf_name')} | Page: {c.get('page_number')}]\n{c.get('chunk_text')}" for c in statute_chunks]
            context_blocks.append("--- STATUTORY PROVISIONS & BARE ACTS (28 ACTS RETRIEVAL) ---\n" + "\n\n".join(statute_texts))
            for c in statute_chunks:
                sources.append({
                    "source_type": "statute",
                    "document_title": c.get("pdf_name", "Indian Bare Act"),
                    "page_number": c.get("page_number", 1),
                    "score": float(c.get("rerank_score", 0.0)),
                })

    # Branch 3: Dynamically execute Contemporary Web Search via Tavily if switch is active
    if decision.search_web:
        try:
            from app.schemas.research import LegalResearchRequest
            from app.services.research import execute_tavily_legal_search
            req = LegalResearchRequest(query=query, max_results=5)
            web_results = execute_tavily_legal_search(req)
            if web_results:
                web_texts = [f"[{res.get('title')} | URL: {res.get('url')}]\n{res.get('content')}" for res in web_results]
                context_blocks.append("--- CONTEMPORARY LEGAL UPDATES & PRECEDENTS (WEB) ---\n" + "\n\n".join(web_texts))
                for res in web_results:
                    sources.append({
                        "source_type": "web_search",
                        "document_title": res.get("title", "Web Precedent"),
                        "page_number": 1,
                        "score": float(res.get("score", 0.9)),
                    })
        except Exception as err:
            logger.warning(f"Web search execution skipped: {err}")

    context_str = "\n\n".join(context_blocks) if context_blocks else "No relevant documents or statutory provisions found in database."

    default_system = (
        "You are LegalDrishti AI (Version 2 - Local Fine-Tuned Retrieval Engine), an advanced AI Legal Intelligence system specializing in Indian law.\n"
        "You are an artificial intelligence platform designed to synthesize and analyze verified statutory laws, Bare Acts, and legal provisions. "
        "You are NOT a court, judge, advocate, lawyer, or law firm, and you do not provide legal representation.\n\n"
        "CORE OPERATIONAL MANDATE & 0% HALLUCINATION CONSTRAINTS:\n"
        "1. STRICT STATUTORY ANCHORING (0% HALLUCINATION):\n"
        "   - Base your legal analysis strictly and exclusively on the available statutory provisions and case records provided below.\n"
        "   - Never invent, assume, extrapolate, or hallucinate statutory sections, penalties, limitations, or legal procedures not substantiated by the legal text.\n"
        "   - If the retrieved context does not contain the specific statutory section or sufficient facts to resolve the query, clearly state that the indexed statute repository does not disclose the necessary provisions rather than guessing.\n\n"
        "2. OBJECTIVE & FACTUAL VOICE:\n"
        "   - Synthesize legal principles, definitions, and procedures in an objective, professional, and third-person tone.\n"
        "   - Never say 'I advise you', 'as your advocate', 'according to the provided text', or 'based on supplied files'. Provide direct statutory intelligence.\n\n"
        "3. PRECISE STATUTORY CITATION:\n"
        "   - Cite exact Act titles, Sections, Sub-sections, and Clauses wherever applicable (e.g., Section 138 proviso (b) of the Negotiable Instruments Act, 1881; Section 482 of the Bharatiya Nagarik Suraksha Sanhita, 2023).\n"
        "   - Maintain clear demarcations between Substantive Penal Law (BNS/IPC), Criminal Procedure (BNSS/CrPC), and Law of Evidence (BSA/IEA).\n\n"
        "4. STRUCTURED BREAKDOWN:\n"
        "   - Present answers with structured, clear headings: Statutory Overview, Core Ingredients & Limitations, Statutory Exceptions & Procedural Application."
    )

    system_instruction = system_prompt_override or default_system

    prompt_messages = [
        {"role": "system", "content": system_instruction},
        {
            "role": "user",
            "content": f"RETRIEVED LEGAL CONTEXT:\n{context_str}\n\nLEGAL QUERY / ISSUE:\n{query}\n\nLEGAL OPINION & STATUTORY ANALYSIS:",
        },
    ]

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=prompt_messages,
        temperature=0.1,
    )
    answer_text = response.choices[0].message.content or ""
    return {
        "answer": answer_text,
        "sources": sources[:5],
        "grounded": bool(context_blocks),
        "decision": decision.model_dump(),
    }


async def stream_grounded_legal_answer_v2(
    query: str,
    user_id: int,
    case_id: int | None = None,
    include_statutes: bool = True,
    system_prompt_override: str | None = None,
) -> AsyncGenerator[dict, None]:
    """
    V2 Streaming Grounded Legal Synthesis:
    Yields SSE-compatible event dictionaries:
    - {"type": "sources", "sources": [...]}
    - {"type": "content", "delta": "..."}
    - {"type": "done", "full_answer": "...", "sources": [...]}
    """
    # 0. Triage & Route with Jev Multi-Pipeline Decision Engine
    decision = decide_query_action(query=query, has_vault_documents=bool(case_id))

    # Check if pure conversational/greeting without any active data pipeline
    is_pure_conversational = decision.is_conversational and not (
        decision.search_statutes or decision.search_vault or decision.search_web
    )

    if is_pure_conversational:
        clarification_msg = decision.suggested_clarification or (
            "Greetings. I am LegalDrishti AI. Please provide the details of your legal issue, "
            "relevant facts, or specific statutory provisions you wish to analyze."
        )
        yield {"type": "sources", "sources": []}
        yield {"type": "content", "delta": clarification_msg}
        yield {"type": "done", "full_answer": clarification_msg, "sources": []}
        return

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    context_blocks = []
    sources = []

    # Branch 1: Dynamically execute Client Case Vault Search if switch is active
    if decision.search_vault and case_id:
        case_chunks = retrieve_case_context_v2(query=query, user_id=user_id, case_id=case_id, top_k=5)
        if case_chunks:
            case_texts = [f"[Document ID: {c.get('document_id')} | Page: {c.get('page_number')}]\n{c.get('chunk_text')}" for c in case_chunks]
            context_blocks.append("--- RELEVANT CASE DOCUMENTS & VAULT EVIDENCE ---\n" + "\n\n".join(case_texts))
            for c in case_chunks:
                sources.append({
                    "source_type": "case_vault",
                    "document_title": f"Case Document #{c.get('document_id')}",
                    "page_number": c.get("page_number", 1),
                    "score": float(c.get("rerank_score", 0.0)),
                })

    # Branch 2: Dynamically execute 28 Bare Acts Statutory Search if switch is active
    if include_statutes and decision.search_statutes:
        statute_chunks = retrieve_statutory_context_v2(query=query, top_k=5)
        if statute_chunks:
            statute_texts = [f"[{c.get('pdf_name')} | Page: {c.get('page_number')}]\n{c.get('chunk_text')}" for c in statute_chunks]
            context_blocks.append("--- STATUTORY PROVISIONS & BARE ACTS (28 ACTS RETRIEVAL) ---\n" + "\n\n".join(statute_texts))
            for c in statute_chunks:
                sources.append({
                    "source_type": "statute",
                    "document_title": c.get("pdf_name", "Indian Bare Act"),
                    "page_number": c.get("page_number", 1),
                    "score": float(c.get("rerank_score", 0.0)),
                })

    # Branch 3: Dynamically execute Contemporary Web Search via Tavily if switch is active
    if decision.search_web:
        try:
            from app.schemas.research import LegalResearchRequest
            from app.services.research import execute_tavily_legal_search
            req = LegalResearchRequest(query=query, max_results=5)
            web_results = execute_tavily_legal_search(req)
            if web_results:
                web_texts = [f"[{res.get('title')} | URL: {res.get('url')}]\n{res.get('content')}" for res in web_results]
                context_blocks.append("--- CONTEMPORARY LEGAL UPDATES & PRECEDENTS (WEB) ---\n" + "\n\n".join(web_texts))
                for res in web_results:
                    sources.append({
                        "source_type": "web_search",
                        "document_title": res.get("title", "Web Precedent"),
                        "page_number": 1,
                        "score": float(res.get("score", 0.9)),
                    })
        except Exception as err:
            logger.warning(f"Web search execution skipped: {err}")

    top_sources = sources[:5]
    yield {"type": "sources", "sources": top_sources}

    context_str = "\n\n".join(context_blocks) if context_blocks else "No relevant documents or statutory provisions found in database."

    default_system = (
        "You are LegalDrishti AI (Version 2 - Local Fine-Tuned Retrieval Engine), an advanced AI Legal Intelligence system specializing in Indian law.\n"
        "You are an artificial intelligence platform designed to synthesize and analyze verified statutory laws, Bare Acts, and legal provisions. "
        "You are NOT a court, judge, advocate, lawyer, or law firm, and you do not provide legal representation.\n\n"
        "CORE OPERATIONAL MANDATE & 0% HALLUCINATION CONSTRAINTS:\n"
        "1. STRICT STATUTORY ANCHORING (0% HALLUCINATION):\n"
        "   - Base your legal analysis strictly and exclusively on the available statutory provisions and case records provided below.\n"
        "   - Never invent, assume, extrapolate, or hallucinate statutory sections, penalties, limitations, or legal procedures not substantiated by the legal text.\n"
        "   - If the retrieved context does not contain the specific statutory section or sufficient facts to resolve the query, clearly state that the indexed statute repository does not disclose the necessary provisions rather than guessing.\n\n"
        "2. OBJECTIVE & FACTUAL VOICE:\n"
        "   - Synthesize legal principles, definitions, and procedures in an objective, professional, and third-person tone.\n"
        "   - Never say 'I advise you', 'as your advocate', 'according to the provided text', or 'based on supplied files'. Provide direct statutory intelligence.\n\n"
        "3. PRECISE STATUTORY CITATION:\n"
        "   - Cite exact Act titles, Sections, Sub-sections, and Clauses wherever applicable (e.g., Section 138 proviso (b) of the Negotiable Instruments Act, 1881; Section 482 of the Bharatiya Nagarik Suraksha Sanhita, 2023).\n"
        "   - Maintain clear demarcations between Substantive Penal Law (BNS/IPC), Criminal Procedure (BNSS/CrPC), and Law of Evidence (BSA/IEA).\n\n"
        "4. STRUCTURED BREAKDOWN:\n"
        "   - Present answers with structured, clear headings: Statutory Overview, Core Ingredients & Limitations, Statutory Exceptions & Procedural Application."
    )

    system_instruction = system_prompt_override or default_system

    prompt_messages = [
        {"role": "system", "content": system_instruction},
        {
            "role": "user",
            "content": f"RETRIEVED LEGAL CONTEXT:\n{context_str}\n\nLEGAL QUERY / ISSUE:\n{query}\n\nLEGAL OPINION & STATUTORY ANALYSIS:",
        },
    ]

    response_stream = await client.chat.completions.create(
        model="gpt-4o",
        messages=prompt_messages,
        temperature=0.1,
        stream=True,
    )

    full_answer_parts = []
    async for chunk in response_stream:
        content = chunk.choices[0].delta.content or ""
        if content:
            full_answer_parts.append(content)
            yield {"type": "content", "delta": content}

    full_answer = "".join(full_answer_parts).strip()
    yield {"type": "done", "full_answer": full_answer, "sources": top_sources}

