"""
LegalDrishti AI — Automated Statute Keyword Extractor
=====================================================
Analyzes all PDFs in 'Legal Pdfs' using TF-IDF and N-Gram phrase mining
to extract the Top 100 defining, repetitive, and unique keywords per book.
Outputs a structured catalog to backend/app/core/statute_keywords.json.
"""

import os
import re
import math
import json
from collections import Counter
from pathlib import Path
from pypdf import PdfReader

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LEGAL_PDFS_DIR = BASE_DIR / "Legal Pdfs"
OUTPUT_JSON_PATH = BASE_DIR / "backend" / "app" / "core" / "statute_keywords.json"

# Common generic legal boilerplate words to filter out
GENERIC_LEGAL_STOPWORDS = {
    "shall", "section", "act", "provided", "order", "court", "sub", "case", "state", 
    "central", "government", "person", "may", "herein", "thereof", "whereas", 
    "notwithstanding", "made", "part", "time", "date", "law", "india", "high", 
    "supreme", "matter", "rules", "rule", "provisions", "clause", "specified", 
    "apply", "manner", "every", "within", "one", "two", "three", "first", "second", 
    "third", "day", "year", "years", "number", "also", "any", "all", "such", "said", 
    "under", "upon", "with", "from", "into", "through", "after", "before", "during", 
    "without", "between", "among", "against", "towards", "above", "below", "following", 
    "given", "including", "relating", "respect", "regard", "accordance", "purpose", 
    "purposes", "power", "powers", "officer", "authority", "prescribed", "deemed", 
    "therein", "hereto", "thereunder", "means", "includes", "defined", "meaning",
    "page", "chapter", "schedule", "table", "annexure", "title", "extent", "commencement",
    "the", "and", "for", "that", "this", "are", "not", "have", "has", "been", "was",
    "were", "will", "would", "could", "should", "their", "they", "them", "his", "her",
    "its", "which", "who", "whom", "whose", "what", "where", "when", "why", "how"
}


def extract_pdf_text_sample(pdf_path: Path, max_pages: int = 150) -> str:
    """Extracts text from PDF, sampling up to max_pages to balance depth and speed."""
    print(f"--> Reading: {pdf_path.name}...")
    try:
        reader = PdfReader(str(pdf_path))
        num_pages = len(reader.pages)
        pages_to_read = min(num_pages, max_pages)
        
        extracted = []
        for i in range(pages_to_read):
            try:
                page_text = reader.pages[i].extract_text() or ""
                extracted.append(page_text)
            except Exception:
                continue
        return "\n".join(extracted)
    except Exception as exc:
        print(f"    [Warning] Failed to read {pdf_path.name}: {exc}")
        return ""


def tokenize_and_extract_ngrams(text: str) -> list[str]:
    """Cleans text and extracts 1-grams, 2-grams, and 3-grams with legal stopword filtering."""
    # Normalize text
    text = text.lower()
    # Replace non-alphanumeric (keep hyphens inside words)
    tokens = re.findall(r"\b[a-z0-9][a-z0-9\-]*[a-z0-9]\b|\b[a-z0-9]\b", text)

    # Filter single tokens
    valid_tokens = []
    for tok in tokens:
        # Keep key statutory section numbers (e.g., 138, 438, 482, 302, 65b) or words with length >= 3
        if tok.isdigit() and len(tok) >= 2:
            valid_tokens.append(tok)
        elif len(tok) >= 3 and tok not in GENERIC_LEGAL_STOPWORDS and not tok.isdigit():
            valid_tokens.append(tok)
        else:
            valid_tokens.append(None)  # Placeholder to break multi-word phrases across stopwords

    ngrams = []
    # 1. Unigrams
    for tok in valid_tokens:
        if tok is not None:
            ngrams.append(tok)

    # 2. Bigrams (2-word phrases)
    for i in range(len(valid_tokens) - 1):
        w1, w2 = valid_tokens[i], valid_tokens[i + 1]
        if w1 and w2:
            ngrams.append(f"{w1} {w2}")

    # 3. Trigrams (3-word phrases)
    for i in range(len(valid_tokens) - 2):
        w1, w2, w3 = valid_tokens[i], valid_tokens[i + 1], valid_tokens[i + 2]
        if w1 and w2 and w3:
            ngrams.append(f"{w1} {w2} {w3}")

    return ngrams


def build_statute_keywords_catalog():
    print("=" * 70)
    print("LegalDrishti AI: Mining Top 100 Keywords for all 28 Legal PDFs")
    print("=" * 70)

    pdf_files = sorted([f for f in LEGAL_PDFS_DIR.iterdir() if f.suffix.lower() == ".pdf"])
    if not pdf_files:
        print(f"Error: No PDF files found in: {LEGAL_PDFS_DIR}")
        return

    total_docs = len(pdf_files)
    print(f"Found {total_docs} legal PDF volumes to analyze.\n")

    # Step 1: Extract and count ngrams for each document
    doc_ngram_counts = {}
    document_frequency = Counter()

    for pdf_file in pdf_files:
        text = extract_pdf_text_sample(pdf_file)
        if not text.strip():
            continue
        
        ngrams = tokenize_and_extract_ngrams(text)
        counts = Counter(ngrams)
        doc_ngram_counts[pdf_file.name] = counts

        # Update Document Frequency (in how many PDFs does this phrase appear?)
        for phrase in counts.keys():
            document_frequency[phrase] += 1

    print("\nText extraction complete. Calculating TF-IDF and uniqueness scores...")

    # Step 2: Compute TF-IDF scores
    # Threshold: If a phrase appears in more than 60% of all PDFs, it's too generic
    max_doc_cutoff = max(2, int(total_docs * 0.60))

    catalog = {}

    for pdf_name, counts in doc_ngram_counts.items():
        total_terms = sum(counts.values()) or 1
        scored_phrases = []

        for phrase, tf in counts.items():
            df = document_frequency[phrase]
            # Skip phrases that are ubiquitous across all legal subjects
            if df > max_doc_cutoff:
                continue
            
            # Skip ultra-rare typos (must appear at least 3 times in this book)
            if tf < 3:
                continue

            # TF-IDF Formula
            tf_norm = tf / total_terms
            idf = math.log((1 + total_docs) / (1 + df)) + 1.0
            
            # Bonus boost for 2-word and 3-word specific legal terms
            phrase_length_boost = 1.0 + (0.25 * (len(phrase.split()) - 1))
            
            final_score = tf_norm * idf * phrase_length_boost
            scored_phrases.append((phrase, final_score, tf, df))

        # Sort by highest score and pick top 100
        scored_phrases.sort(key=lambda x: x[1], reverse=True)
        top_100 = [phrase for phrase, score, tf, df in scored_phrases[:100]]

        catalog[pdf_name] = {
            "total_extracted_unique_phrases": len(scored_phrases),
            "top_100_keywords": top_100,
        }
        print(f"✓ {pdf_name}: Extracted {len(top_100)} top keywords (Top 3: {top_100[:3]})")

    # Step 3: Save catalog to JSON
    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"SUCCESS! Saved Top 100 keywords for all {len(catalog)} PDFs to:")
    print(f"{OUTPUT_JSON_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    build_statute_keywords_catalog()
