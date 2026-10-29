
import hashlib
import re
import uuid
from typing import Any
from flashrank import Ranker, RerankRequest
from openai import OpenAI
from app.core.config import PROJECT_ROOT, get_settings
from app.core.redis_client import get_cache, set_cache
from app.services.embeddings_v1 import get_embedding
from app.services.decision_router import decide_query_action, MultiPipelineDecision
from app.services.vector_store_v1 import (
    hybrid_search_chunks,
    hybrid_search_statutes,
)

MODELS_CACHE_DIR = PROJECT_ROOT / "storage" / "models"
_ranker: Ranker | None = None


def get_ranker() -> Ranker:
    global _ranker
    if _ranker is None:
        _ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir=str(MODELS_CACHE_DIR))
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
    session: Any = None,
    case_id: int | None = None,
    candidate_pool_size: int = 40,
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
        # Only include if the document actually exists in the database
        if not d_id or d_id not in titles_map:
            continue
        enriched.append({
            "source_type": "case_document",
            "document_id": d_id,
            "document_title": titles_map[d_id],
            "page_number": c.get("page_number", 1),
            "chunk_text": c.get("chunk_text", ""),
            "score": c.get("cross_encoder_score") or c.get("score"),
        })

    return enriched


def retrieve_statutory_context(
    query: str,
    target_statutes: list[str] | None = None,
    candidate_pool_size: int = 40,
    top_k: int = 5,
    alpha: float = 0.5,
) -> list[dict]:
    """
    V1 Statutory Retrieval:
    Pure end-to-end dense + BM25 hybrid search across all statutes with zero regex / n-gram routing.
    """
    target_pdfs = target_statutes or []
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
    session_chunks: list[dict] | None = None,
) -> str:
    sections = []

    if session_chunks:
        session_blocks = []
        for idx, c in enumerate(session_chunks, 1):
            block = f"[Consultation Attached Document {idx}: '{c['document_title']}']\n{c['chunk_text']}"
            session_blocks.append(block)
        sections.append("DOCUMENTS ATTACHED SPECIFICALLY TO THIS CONSULTATION:\n" + "\n\n".join(session_blocks))

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


STANDARD_NON_LEGAL_RESPONSE = (
    "I am LegalDrishti AI, an AI legal intelligence assistant. "
    "I can only assist with inquiries regarding Indian law, legal procedures, statutory provisions, or your case briefs. "
    "Please feel free to ask any question regarding Indian legal matters."
)


def check_conversational_or_meta_query(query: str) -> str | None:
    q = query.strip().lower()
    q_clean = re.sub(r"[^\w\s]", "", q).strip()

    # 1. Personal, Silly, or Relationship queries (e.g. friend, age, feelings, jokes, etc.)
    personal_and_silly_patterns = [
        r"\b(friend|friends|bestie|girlfriend|boyfriend|partner|wife|husband|crush|marry|dating|love)\b",
        r"\b(how old are you|your age|your birthday|when were you born|where do you live|your home|your address)\b",
        r"\b(your gender|are you male|are you female|are you human|do you have feelings|are you happy|are you sad)\b",
        r"\b(favorite|favourite|hobbies|hobby|what do you eat|can you eat|do you sleep|what do you drink)\b",
        r"\b(tell me a joke|tell a joke|write a poem|sing a song|sing for me|dance|who won|how to cook|recipe)\b",
        r"\b(tell me your personal|your personal life|your phone|your email|your salary)\b",
    ]
    for pat in personal_and_silly_patterns:
        if re.search(pat, q):
            return STANDARD_NON_LEGAL_RESPONSE

    # 2. Greetings & Pleasantries
    greetings = {
        "hi", "hello", "hey", "hiya", "howdy", "good morning", "good afternoon",
        "good evening", "how are you", "how r u", "how are you doing", "hows it going",
        "whats up", "sup", "namaste", "namaskar"
    }
    if q_clean in greetings or any(q_clean.startswith(g + " ") for g in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]):
        return "Hello! I am LegalDrishti AI, your legal research and intelligence assistant. How may I assist you with Indian law or your case briefs today?"

    # 3. Identity & Name
    identity_patterns = [
        r"\b(who are you|what is your name|tell me your name|introduce yourself|whats your name)\b",
        r"\b(who made you|who created you|who developed you)\b",
    ]
    for pat in identity_patterns:
        if re.search(pat, q):
            return (
                "I am **LegalDrishti AI**, an authoritative legal intelligence platform specializing in Indian jurisprudence. "
                "I assist legal practitioners, corporate counsels, and citizens with substantive and procedural statutory research, "
                "precedent analysis, and evidentiary document evaluation."
            )

    # 4. Scope & Capabilities
    capability_patterns = [
        r"\b(what can you do|how can you help|what are your features|what do you do|help me)\b",
    ]
    for pat in capability_patterns:
        if re.search(pat, q) and len(q_clean.split()) <= 6:
            return (
                "Here is how I can assist you:\n\n"
                "- **Statutory Analysis**: Guidance on Indian criminal statutes (BNS, BNSS, BSA, IPC, CrPC), civil law, and commercial statutes (NI Act, Arbitration, Companies Act).\n"
                "- **Judicial Precedents**: Synthesizing landmark judgments, legal doctrines, and section conversions.\n"
                "- **Case Brief & Evidentiary Vault**: Reviewing contracts, FIRs, bank memos, and case briefs placed in your workspace.\n\n"
                "You can type any legal query or select a matter from the Cases tab to begin."
            )

    # 5. Inquiries regarding indexed PDFs / documents / knowledge base
    docs_patterns = [
        r"\b(tell me pdf names|what pdfs|which pdfs|list pdfs|what bare acts|what documents do you use|what data do you use)\b",
    ]
    for pat in docs_patterns:
        if re.search(pat, q):
            return (
                "LegalDrishti AI operates on an indexed repository of foundational Indian Bare Acts and governing statutes, including:\n\n"
                "- **Criminal Law**: Bharatiya Nyaya Sanhita (BNS) 2023, Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023, Bharatiya Sakshya Adhiniyam (BSA) 2023.\n"
                "- **Constitutional & Civil Framework**: The Constitution of India, Code of Civil Procedure (CPC) & Limitation Act.\n"
                "- **Commercial & Special Enactments**: Negotiable Instruments Act 1881, Arbitration & Conciliation Act, and related regulatory statutes.\n\n"
                "Additionally, when working in a matter, I analyze the specific evidentiary files uploaded to your active case vault."
            )

    # 6. Gratitude / Salutations
    gratitude = {"thank you", "thanks", "thx", "thank u", "ok thanks", "okay thanks", "bye", "goodbye"}
    if q_clean in gratitude:
        return "You're welcome! Please let me know whenever you need further statutory research or case analysis."

    return None


async def generate_grounded_legal_answer(
    query: str,
    user_id: int,
    session: Any = None,
    case_id: int | None = None,
    candidate_pool_size: int = 40,
    top_k: int = 5,
    alpha: float = 0.5,
    session_id: int | None = None,
) -> dict:
    # 0. Triage & Route with Jev Multi-Pipeline Decision Engine
    has_vault = bool(case_id or session_id)
    decision = decide_query_action(query=query, has_vault_documents=has_vault)

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

    query_hash = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:16]
    if session_id:
        cache_key = f"rag:session:{session_id}:{query_hash}"
    elif case_id:
        cache_key = f"rag:case:{case_id}:{query_hash}"
    else:
        cache_key = f"rag:global:{user_id}:{query_hash}"

    cached_result = get_cache(cache_key)
    if cached_result is not None:
        cached_ans = cached_result.get("answer", "")
        if "I can only assist with inquiries regarding Indian law" not in cached_ans:
            print(f"[Redis Cache HIT] Serving instant Grounded RAG answer from RAM: '{query[:40]}...'")
            return cached_result

    print(f"[Redis Cache MISS] Executing Dual-Stream RAG pipeline: '{query[:40]}...'")

    settings = get_settings()

    # Retrieve session-scoped attached documents if this is a chat session
    session_chunks: list[dict] = []
    if session_id:
        try:
            doc_stmt = select(Document).where(
                Document.session_id == session_id,
                Document.user_id == user_id,
            )
            doc_res = await session.execute(doc_stmt)
            session_docs = doc_res.scalars().all()
            for s_doc in session_docs:
                if s_doc.extracted_text:
                    session_chunks.append({
                        "source_type": "session_document",
                        "document_id": s_doc.id,
                        "document_title": s_doc.title or s_doc.file_name,
                        "page_number": 1,
                        "chunk_text": s_doc.extracted_text[:4000],
                        "score": 1.0,
                    })
        except Exception as sess_err:
            pass

    case_chunks: list[dict] = []
    if decision.search_vault and case_id is not None:
        case_chunks = await retrieve_case_context(
            query=query,
            user_id=user_id,
            session=session,
            case_id=case_id,
            candidate_pool_size=candidate_pool_size,
            top_k=top_k,
            alpha=alpha,
        )

    statute_chunks: list[dict] = []
    if decision.search_statutes:
        statute_chunks = retrieve_statutory_context(
            query=query,
            candidate_pool_size=candidate_pool_size,
            top_k=top_k,
            alpha=alpha,
        )

    all_chunks = session_chunks + case_chunks + statute_chunks

    if not all_chunks:
        empty_response = {
            "answer": "The brief placed on record and the statutory repository do not disclose information matching this inquiry.",
            "sources": [],
            "grounded": False,
        }
        set_cache(cache_key, empty_response, expire_seconds=3600)
        return empty_response

    context_text = format_dual_stream_context(case_chunks, statute_chunks, session_chunks=session_chunks)

    system_prompt = (
        "You are LegalDrishti AI (Version 1 - Cloud Retrieval Engine), an advanced AI Legal Intelligence system specializing in Indian law.\n"
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

    user_prompt = (
        f"<user_legal_query>\n{query}\n</user_legal_query>\n\n"
        f"<statutory_and_case_context>\n{context_text}\n</statutory_and_case_context>\n\n"
        "Deliver an authoritative, well-structured legal breakdown answering the user's legal query:"
    )

    model_to_use = settings.openai_model or "gpt-4o-mini"
    if "terra" in model_to_use or "5.6" in model_to_use:
        model_to_use = "gpt-4o-mini"

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=model_to_use,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    answer_text = response.choices[0].message.content or ""

    seen_sources = set()
    sources = []
    for c in all_chunks:
        doc_title = c.get("document_title") or "Indian Bare Act"
        page_num = c.get("page_number", 1)
        key = (doc_title, page_num)
        if key not in seen_sources:
            seen_sources.add(key)
            sources.append({
                "source_type": c.get("source_type"),
                "document_title": doc_title,
                "page_number": page_num,
                "score": float(c["score"]) if c.get("score") is not None else None,
            })
    # Limit to top 3 most relevant source citations
    sources = sources[:3]


    result_payload = {
        "answer": answer_text.strip(),
        "sources": sources,
        "grounded": True,
        "decision": decision.model_dump(),
    }

    # Cache response for 2 hours (7200 seconds) only if it is a genuine legal answer
    if "I can only assist with inquiries regarding Indian law" not in answer_text:
        set_cache(cache_key, result_payload, expire_seconds=7200)

    return result_payload


async def stream_grounded_legal_answer(
    query: str,
    user_id: int,
    session: Any = None,
    case_id: int | None = None,
    candidate_pool_size: int = 40,
    top_k: int = 5,
    alpha: float = 0.5,
    session_id: int | None = None,
):
    """
    Asynchronous generator streaming the legal answer word-by-word
    over Server-Sent Events (SSE).
    """
    # 0. Triage & Route with Jev Multi-Pipeline Decision Engine
    has_vault = bool(case_id or session_id)
    decision = decide_query_action(query=query, has_vault_documents=has_vault)

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

    query_hash = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:16]
    if session_id:
        cache_key = f"rag:session:{session_id}:{query_hash}"
    elif case_id:
        cache_key = f"rag:case:{case_id}:{query_hash}"
    else:
        cache_key = f"rag:global:{user_id}:{query_hash}"

    cached_result = get_cache(cache_key)
    if cached_result is not None:
        cached_ans = cached_result.get("answer", "")
        if "I can only assist with inquiries regarding Indian law" not in cached_ans:
            print(f"[Redis Cache HIT - Stream] Serving from RAM: '{query[:40]}...'")
            cached_sources = cached_result.get("sources", [])
            yield {"type": "sources", "sources": cached_sources}
            yield {"type": "content", "delta": cached_ans}
            yield {"type": "done", "full_answer": cached_ans, "sources": cached_sources}
            return

    settings = get_settings()

    session_chunks: list[dict] = []
    if session_id:
        try:
            doc_stmt = select(Document).where(
                Document.session_id == session_id,
                Document.user_id == user_id,
            )
            doc_res = await session.execute(doc_stmt)
            session_docs = doc_res.scalars().all()
            for s_doc in session_docs:
                if s_doc.extracted_text:
                    session_chunks.append({
                        "source_type": "session_document",
                        "document_id": s_doc.id,
                        "document_title": s_doc.title or s_doc.file_name,
                        "page_number": 1,
                        "chunk_text": s_doc.extracted_text[:4000],
                        "score": 1.0,
                    })
        except Exception:
            pass

    case_chunks: list[dict] = []
    if decision.search_vault and case_id is not None:
        case_chunks = await retrieve_case_context(
            query=query,
            user_id=user_id,
            session=session,
            case_id=case_id,
            candidate_pool_size=candidate_pool_size,
            top_k=top_k,
            alpha=alpha,
        )

    statute_chunks: list[dict] = []
    if decision.search_statutes:
        statute_chunks = retrieve_statutory_context(
            query=query,
            candidate_pool_size=candidate_pool_size,
            top_k=top_k,
            alpha=alpha,
        )

    all_chunks = session_chunks + case_chunks + statute_chunks

    seen_sources = set()
    sources = []
    for c in all_chunks:
        doc_title = c.get("document_title") or "Indian Bare Act"
        page_num = c.get("page_number", 1)
        key = (doc_title, page_num)
        if key not in seen_sources:
            seen_sources.add(key)
            sources.append({
                "source_type": c.get("source_type"),
                "document_title": doc_title,
                "page_number": page_num,
                "score": float(c["score"]) if c.get("score") is not None else None,
            })
    sources = sources[:3]

    if not all_chunks:
        empty_answer = "The brief placed on record and the statutory repository do not disclose information matching this inquiry."
        set_cache(cache_key, {"answer": empty_answer, "sources": [], "grounded": False}, expire_seconds=3600)
        yield {"type": "sources", "sources": []}
        yield {"type": "content", "delta": empty_answer}
        yield {"type": "done", "full_answer": empty_answer, "sources": []}
        return

    # Yield sources first so the UI displays them immediately
    yield {"type": "sources", "sources": sources}

    context_text = format_dual_stream_context(case_chunks, statute_chunks, session_chunks=session_chunks)

    system_prompt = (
        "You are LegalDrishti AI (Version 1 - Cloud Retrieval Engine), an advanced AI Legal Intelligence system specializing in Indian law.\n"
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

    user_prompt = (
        f"<user_legal_query>\n{query}\n</user_legal_query>\n\n"
        f"<statutory_and_case_context>\n{context_text}\n</statutory_and_case_context>\n\n"
        "Deliver an authoritative, well-structured legal breakdown answering the user's legal query:"
    )

    model_to_use = settings.openai_model or "gpt-4o-mini"
    if "terra" in model_to_use or "5.6" in model_to_use:
        model_to_use = "gpt-4o-mini"

    client = OpenAI(api_key=settings.openai_api_key)
    stream_response = client.chat.completions.create(
        model=model_to_use,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
    )

    full_answer_parts = []
    for chunk in stream_response:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            full_answer_parts.append(delta)
            yield {"type": "content", "delta": delta}

    full_answer_text = "".join(full_answer_parts).strip()
    if "I can only assist with inquiries regarding Indian law" not in full_answer_text:
        set_cache(cache_key, {"answer": full_answer_text, "sources": sources, "grounded": True}, expire_seconds=7200)

    yield {"type": "done", "full_answer": full_answer_text, "sources": sources}


# Version 1 Alias
generate_grounded_legal_answer_v1 = generate_grounded_legal_answer
