import sys
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.config import get_settings
from app.services.statute_router import route_query_to_statutes
from app.services.embeddings import get_embedding
from app.services.vector_store import hybrid_search_statutes
from app.services.retrieval import rerank_chunks
from openai import OpenAI


async def test_statute_rag(query: str):
    print("=" * 80)
    print(f"LEGAL QUERY: {query}")
    print("=" * 80)

    routed = route_query_to_statutes(query, max_statutes=3)
    target_pdfs = [r["pdf_name"] for r in routed]

    print(f"\n[1. Router] Selected target statutes: {target_pdfs}")

    for r in routed:
        print(f"    - {r['pdf_name']} (Score: {r['score']}, Matched: {r['matched_keywords']})")

    print("\n[2. Bi-Encoder] Running Weaviate Hybrid Search (BM25 + Vector, alpha=0.5)...")

    query_vector = get_embedding(query)

    raw_candidates = hybrid_search_statutes(
        query_text=query,
        query_vector=query_vector,
        target_pdf_names=target_pdfs,
        alpha=0.5,
        limit=20,
    )

    print(f"    Retrieved {len(raw_candidates)} candidate chunks from Weaviate.")

    print("\n[3. Cross-Encoder] FlashRank re-ranking candidates into Top 5 chunks...")

    top_chunks = rerank_chunks(query=query, chunks=raw_candidates, top_n=5)

    print(f"    Selected {len(top_chunks)} final chunks. Top sources:")

    for idx, c in enumerate(top_chunks, 1):
        print(f"    [{idx}] {c['pdf_name']} (Page {c['page_number']}) - Score: {c.get('cross_encoder_score'):.4f}")

    context_blocks = []

    for idx, c in enumerate(top_chunks, 1):
        block = f"[{c['pdf_name']}, Page {c['page_number']}]\n{c['chunk_text']}"
        context_blocks.append(block)

    context_text = "\n\n---\n\n".join(context_blocks)

    print("\n[4. Generation] Calling Senior Advocate LLM...")

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

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
        "   'The statutory record before me does not disclose [specific topic/fact]. The provided provisions are silent on this point.'\n"
        "3. STRICT CITATION DISCIPLINE: Every legal requirement, period, penalty, or rule you state MUST be "
        "immediately anchored to its source in brackets: e.g., [Document Title, Page X].\n"
        "4. ZERO FABRICATION: Never invent section numbers, limitation periods, or penalties not supported by the excerpts.\n"
        "5. STRUCTURED REASONING: Present your opinion crisply—Statutory Ingredients, Procedural Mandates, and Strategic Observations."
    )

    user_prompt = (
        "STATUTORY BRIEF & EXCERPTS ON RECORD:\n"
        "======================================================================\n"
        f"{context_text}\n"
        "======================================================================\n\n"
        f"INQUIRY / COUNTER-QUESTION: {query}\n\n"
        "Counsel, review the statutory brief above and deliver your grounded legal analysis and opinion:"
    )

    response = client.chat.completions.create(
        model=settings.openai_model or "gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )


    print("\n" + "=" * 80)
    print("SENIOR ADVOCATE LEGAL OPINION:")
    print("=" * 80)
    print(response.choices[0].message.content)
    print("=" * 80)


if __name__ == "__main__":
    test_query = (
        "What are the essential conditions for dishonour of cheque under Section 138, "
        "and what is the statutory notice period required to be given to the drawer?"
    )

    asyncio.run(test_statute_rag(test_query))