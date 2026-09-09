import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.schemas.research import LegalResearchRequest
from app.services.research import perform_legal_research


def test_tavily_legal_research():
    query = (
        "Section 138 Negotiable Instruments Act vicarious liability of "
        "non-executive independent director who resigned before cheque issuance"
    )

    print("=" * 80)
    print("LEGAL RESEARCH QUERY:")
    print(query)
    print("=" * 80)
    print("\nExecuting Tavily Search across Indian Kanoon, LiveLaw, Bar & Bench, CaseMine...")

    request_payload = LegalResearchRequest(
        query=query,
        court_filter="Supreme Court",
        max_results=4,
    )

    response = perform_legal_research(request_payload)

    print("\n" + "=" * 80)
    print(f"IDENTIFIED PRECEDENTS ({len(response.precedents)} found):")
    print("=" * 80)

    for idx, p in enumerate(response.precedents, 1):
        print(f"\n[{idx}] {p.case_title}")
        print(f"    Citation: {p.citation or 'Neutral / Not formally reported'}")
        print(f"    Court:    {p.court} ({p.year or 'N/A'})")
        print(f"    Ratio Decidendi:\n    --> {p.ratio_decidendi}")
        print(f"    Source:   {p.source_url}")

    print("\n" + "=" * 80)
    print("SENIOR ADVOCATE RESEARCH MEMORANDUM & STRATEGY:")
    print("=" * 80)
    print(response.synthesis)
    print("=" * 80)


if __name__ == "__main__":
    test_tavily_legal_research()
