
import hashlib
import re
import uuid
from flashrank import Ranker, RerankRequest
from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PROJECT_ROOT, get_settings
from app.core.redis_client import get_cache, set_cache
from app.models.document import Document
from app.services.embeddings import get_embedding
from app.services.vector_store import (
    hybrid_search_chunks,
    hybrid_search_statutes,
)
from app.services.statute_router import route_query_to_statutes

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
    session: AsyncSession,
    case_id: int | None = None,
    candidate_pool_size: int = 20,
    top_k: int = 5,
    alpha: float = 0.5,
    session_id: int | None = None,
) -> dict:
    # 1. Fast conversational / meta-intent check (Zero vector latency, 0 token waste)
    quick_reply = check_conversational_or_meta_query(query)
    if quick_reply:
        return {
            "answer": quick_reply,
            "sources": [],
            "grounded": True,
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
    if case_id is not None:
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
        "You are LegalDrishti AI, an authoritative, precise legal intelligence assistant specializing in Indian law.\n"
        "Provide direct, professional, and meaningful legal analysis without fluff, filler, or excessive length.\n\n"
        "CRITICAL INSTRUCTIONS & EDITORIAL CONSTRAINTS:\n"
        "1. CONCISE & FOCUSED LENGTH:\n"
        "   - Keep your entire response concise, sharp, and strictly under 300-350 words.\n"
        "   - Deliver maximum legal value in minimal words.\n\n"
        "2. ZERO CONTEXT LEAKS (STRICT):\n"
        "   - NEVER use phrases such as 'according to the provided text', 'as stated in the course material', "
        "'as identified in the statutory materials', 'based on the documents', 'the brief is silent', or 'supplied records'.\n"
        "   - Synthesize all facts, legal principles, and statutory rules directly in an objective, authoritative third-person voice.\n\n"
        "3. STATUTORY INTERPLAY & DEMARCATION:\n"
        "   - Maintain clear demarcations between substantive penal law (BNS: offences and punishments), "
        "criminal procedure (BNSS: FIR, arrest, bail, investigation, and trial), and evidentiary rules (BSA: proof and electronic admissibility).\n\n"
        "4. HIGH PRECISION & LEGAL NUANCE:\n"
        "   - Cite exact sections and subsections (e.g., Section 103(2) BNS for group murder/mob lynching, Section 69 BNS for deceitful intercourse, Section 152 BNS for acts endangering sovereignty, Section 4 BNS for community service).\n"
        "   - Note temporal applicability: Article 20(1) of the Constitution guarantees non-retrospectivity (acts committed before 1 July 2024 remain governed by IPC).\n"
        "   - Mention key administrative status: e.g., Section 106(2) hit-and-run provisions held in abeyance pending implementation.\n\n"
        "5. CLEAN, SCANNABLE FORMATTING:\n"
        "   - Structure with: a crisp Executive Summary, Key Highlights (bullet points), a compact 4-5 row IPC vs. BNS comparison table, and a brief procedural note.\n"
        "   - Avoid excessive nested symbols or bloated text.\n\n"
        "6. ETHICAL BOUNDARY:\n"
        "   - Provide objective legal intelligence. Never state 'I advise you as your advocate'.\n\n"
        "7. NON-LEGAL OR SILLY INQUIRIES (CRITICAL):\n"
        "   - If the user query is non-legal, personal, casual chit-chat, or asking about friends, feelings, personal life, or non-legal topics, NEVER generate legal tables, statutory sections, executive summaries, or procedural notes.\n"
        "   - Instead, output ONLY this standard response verbatim:\n"
        "     \"I am LegalDrishti AI, an AI legal intelligence assistant. I can only assist with inquiries regarding Indian law, legal procedures, statutory provisions, or your case briefs. Please feel free to ask any question regarding Indian legal matters.\""
    )

    user_prompt = (
        f"<user_legal_query>\n{query}\n</user_legal_query>\n\n"
        f"<statutory_and_case_context>\n{context_text}\n</statutory_and_case_context>\n\n"
        "Deliver a concise, authoritative, and scannable legal breakdown answering the query, "
        "incorporating statutory interplay and a compact section comparison table where helpful. "
        "(If the inquiry is non-legal, personal, or silly, output ONLY the standard non-legal response without any tables or legal notes):"
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
    }

    # Cache response for 2 hours (7200 seconds)
    set_cache(cache_key, result_payload, expire_seconds=7200)

    return result_payload
