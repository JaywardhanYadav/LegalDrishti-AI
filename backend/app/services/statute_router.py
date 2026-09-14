import json
import re
from pathlib import Path
from typing import Optional

CATALOG_PATH = Path(__file__).resolve().parent.parent / "core" / "statute_keywords.json"

_STATUTE_CATALOG: Optional[dict] = None
_KEYWORD_INDEX: Optional[dict[str, list[str]]] = None


def load_statute_catalog() -> dict:
    global _STATUTE_CATALOG, _KEYWORD_INDEX

    if _STATUTE_CATALOG is not None:
        return _STATUTE_CATALOG

    if not CATALOG_PATH.exists():
        print(f"[StatuteRouter Warning] Catalog not found at {CATALOG_PATH}. Run extract_statute_keywords.py first.")
        _STATUTE_CATALOG = {}
        _KEYWORD_INDEX = {}
        return _STATUTE_CATALOG

    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            _STATUTE_CATALOG = json.load(f)

        _KEYWORD_INDEX = {}

        for pdf_name, data in _STATUTE_CATALOG.items():
            keywords = data.get("top_100_keywords", [])

            for kw in keywords:
                kw_norm = kw.strip().lower()

                if kw_norm not in _KEYWORD_INDEX:
                    _KEYWORD_INDEX[kw_norm] = []

                _KEYWORD_INDEX[kw_norm].append(pdf_name)

        print(f"[StatuteRouter] Loaded {len(_STATUTE_CATALOG)} statutes and {len(_KEYWORD_INDEX)} indexed phrases.")

    except Exception as exc:
        print(f"[StatuteRouter Error] Failed to load catalog: {exc}")
        _STATUTE_CATALOG = {}
        _KEYWORD_INDEX = {}

    return _STATUTE_CATALOG


# Explicit Statute Intent Matchers
EXPLICIT_INTENT_MAP = [
    {
        "patterns": [r"\bbns\b", r"\bbharatiya nyaya\b", r"\bipc\b", r"\bindian penal code\b", r"\bpenal code\b"],
        "pdf_name": "Bharatiya Nyaya Sanhita, 2023.pdf",
        "category": "substantive",
    },
    {
        "patterns": [r"\bbnss\b", r"\bbharatiya nagarik\b", r"\bcrpc\b", r"\bcriminal procedure\b", r"\banticipatory bail\b", r"\bbail\b", r"\bfir\b"],
        "pdf_name": "THE BHARATIYA NAGARIK SURAKSHA SANHITA, 2023.pdf",
        "category": "procedure",
    },
    {
        "patterns": [r"\bbsa\b", r"\bbharatiya sakshya\b", r"\bevidence act\b", r"\belectronic evidence\b"],
        "pdf_name": "THE BHARATIYA SAKSHYA ADHINIYAM,2023.pdf",
        "category": "evidence",
    },
    {
        "patterns": [r"\bni act\b", r"\bnegotiable instruments\b", r"\bcheque bounce\b", r"\bsection 138\b", r"\bsec 138\b"],
        "pdf_name": "The Negotiable Instruments Act, 1881.PDF",
        "category": "commercial",
    },
    {
        "patterns": [r"\bconstitution\b", r"\barticle 21\b", r"\barticle 32\b", r"\barticle 226\b", r"\bfundamental rights\b"],
        "pdf_name": "THE CONSTITUTION OF INDIA.pdf",
        "category": "constitutional",
    },
]


def route_query_to_statutes(query: str, max_statutes: int = 5) -> list[dict]:
    load_statute_catalog()

    if not _STATUTE_CATALOG:
        return []

    query_clean = query.lower()

    # 1. Check for specific explicit statute intents
    explicit_matches = []
    for item in EXPLICIT_INTENT_MAP:
        for pat in item["patterns"]:
            if re.search(pat, query_clean):
                if item["pdf_name"] in _STATUTE_CATALOG:
                    explicit_matches.append({
                        "pdf_name": item["pdf_name"],
                        "score": 100.0,
                        "matched_keywords": [f"intent_{item['category']}"],
                    })
                break

    if explicit_matches:
        # If user explicitly asked for specific statutes (e.g. BNS only), route strictly to them
        return explicit_matches[:max_statutes]

    # 2. General keyword-based fallback routing
    words = re.findall(r"\b[a-z0-9][a-z0-9\-]*[a-z0-9]\b|\b[a-z0-9]\b", query_clean)
    query_phrases = set(words)

    for i in range(len(words) - 1):
        query_phrases.add(f"{words[i]} {words[i + 1]}")

    for i in range(len(words) - 2):
        query_phrases.add(f"{words[i]} {words[i + 1]} {words[i + 2]}")

    pdf_scores: dict[str, float] = {pdf: 0.0 for pdf in _STATUTE_CATALOG.keys()}
    pdf_matches: dict[str, list[str]] = {pdf: [] for pdf in _STATUTE_CATALOG.keys()}

    for phrase in query_phrases:
        if phrase in _KEYWORD_INDEX:
            matching_pdfs = _KEYWORD_INDEX[phrase]
            phrase_length = len(phrase.split())

            weight = 1.0 if phrase_length == 1 else (2.5 if phrase_length == 2 else 4.0)

            for pdf in matching_pdfs:
                pdf_scores[pdf] += weight

                if phrase not in pdf_matches[pdf]:
                    pdf_matches[pdf].append(phrase)

    scored_candidates = [
        {
            "pdf_name": pdf,
            "score": pdf_scores[pdf],
            "matched_keywords": pdf_matches[pdf],
        }
        for pdf in pdf_scores
        if pdf_scores[pdf] > 0
    ]

    scored_candidates.sort(key=lambda x: x["score"], reverse=True)

    selected = scored_candidates[:max_statutes]

    if not selected:
        default_statutes = [
            "THE CONSTITUTION OF INDIA.pdf",
            "Bharatiya Nyaya Sanhita, 2023.pdf",
            "THE BHARATIYA NAGARIK SURAKSHA SANHITA, 2023.pdf",
            "Code of Civil Procedure & Limitation Act.pdf",
        ]

        selected = [
            {
                "pdf_name": pdf,
                "score": 1.0,
                "matched_keywords": ["fallback_general_statute"],
            }
            for pdf in default_statutes[:max_statutes]
        ]

    return selected