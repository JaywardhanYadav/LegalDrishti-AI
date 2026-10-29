import sys
import re
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.case_document import CaseDocument
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embeddings_v1 import get_embeddings_batch
from app.services.vector_store_v1 import store_chunk_vector

PAGE_MARKER_REGEX = re.compile(r"---\s*\[Page\s*(\d+)\]\s*---", re.IGNORECASE)

# Legal regex patterns for Indian Statutory Acts
SECTION_SPLIT_REGEX = re.compile(
    r"(?:^|\n)(?=(?:(?:Section|Sec\.)\s*\d+[A-Z]?|\d+[A-Z]?\.)\s+)",
    re.IGNORECASE,
)
ARTICLE_SPLIT_REGEX = re.compile(
    r"(?:^|\n)(?=(?:(?:Article|Art\.)\s*\d+[A-Z]?|\d+[A-Z]?\.)\s+)",
    re.IGNORECASE,
)
ORDER_SPLIT_REGEX = re.compile(
    r"(?:^|\n)(?=(?:Order\s+[IVXLCDM\d]+))",
    re.IGNORECASE,
)

SECTION_HEADER_EXTRACT = re.compile(
    r"^(?:(?:Section|Sec\.)\s*(\d+[A-Z]?)|(\d+[A-Z]?)\.)\s*[:\.\-]?\s*([^\n\r]+)",
    re.IGNORECASE,
)
ARTICLE_HEADER_EXTRACT = re.compile(
    r"^(?:(?:Article|Art\.)\s*(\d+[A-Z]?)|(\d+[A-Z]?)\.)\s*[:\.\-]?\s*([^\n\r]+)",
    re.IGNORECASE,
)
ORDER_HEADER_EXTRACT = re.compile(
    r"^(?:Order\s+([IVXLCDM\d]+))\s*,?\s*(?:Rule\s+(\d+))?\s*[:\.\-]?\s*([^\n\r]+)",
    re.IGNORECASE,
)
CHAPTER_REGEX = re.compile(
    r"^(?:CHAPTER|PART)\s+([IVXLCDM\d]+)[\s:\.\-]*(.*)$",
    re.IGNORECASE,
)
MARKDOWN_OR_CAPS_HEADING = re.compile(
    r"^(?:#{1,4}\s+(.+)|([A-Z\s]{4,60}))\s*$"
)


def estimate_token_count(text: str) -> int:
    return max(1, len(text) // 4)


def build_context_header(
    document_title: str = "",
    chapter_title: str = "",
    section_heading: str = "",
    page_number: int | None = None,
    part_info: str = "",
) -> str:
    parts = []
    if document_title:
        clean_title = document_title.replace(".pdf", "").replace(".PDF", "").strip()
        parts.append(clean_title)
    if chapter_title:
        parts.append(chapter_title.strip())
    if section_heading:
        h = section_heading.strip()
        if part_info:
            h += f" ({part_info})"
        parts.append(h)
    elif page_number is not None:
        p = f"Page {page_number}"
        if part_info:
            p += f" ({part_info})"
        parts.append(p)

    if not parts:
        return ""
    return f"[{' | '.join(parts)}]\n\n"


def is_statutory_text(text: str) -> bool:
    """
    Checks if text has statutory structural markers like Section 138, Article 21, etc.
    """
    sample = text[:15000]
    section_matches = len(re.findall(r"(?:Section|Sec\.)\s*\d+[A-Z]?", sample, re.IGNORECASE))
    article_matches = len(re.findall(r"(?:Article|Art\.)\s*\d+[A-Z]?", sample, re.IGNORECASE))
    order_matches = len(re.findall(r"Order\s+[IVXLCDM\d]+", sample, re.IGNORECASE))
    return (section_matches >= 2) or (article_matches >= 2) or (order_matches >= 2)


def extract_page_segments(full_text: str) -> list[tuple[str, int]]:
    """
    Parses --- [Page X] --- markers into a list of (page_text, page_number).
    """
    lines = full_text.splitlines()
    segments: list[tuple[str, int]] = []
    current_page = 1
    current_lines: list[str] = []

    for line in lines:
        match = PAGE_MARKER_REGEX.search(line)
        if match:
            if current_lines:
                page_text = "\n".join(current_lines).strip()
                if page_text:
                    segments.append((page_text, current_page))
                current_lines = []
            current_page = int(match.group(1))
        else:
            current_lines.append(line)

    if current_lines:
        page_text = "\n".join(current_lines).strip()
        if page_text:
            segments.append((page_text, current_page))

    if not segments:
        segments = [(full_text.strip(), 1)]

    return segments


def split_section_into_subchunks(
    section_body: str,
    base_header: str,
    page_number: int,
    max_tokens: int = 600,
    overlap_tokens: int = 50,
) -> list[tuple[str, int]]:
    """
    Splits an oversized legal section into cohesive sub-chunks, prepending
    the sticky context header with Part numbers to every slice.
    """
    # Try splitting along sub-section boundaries: e.g. (1), (2), (a), (b), or double newlines
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|(?<=\n)(?=\(\d+\))", section_body) if p.strip()]
    if not paragraphs:
        paragraphs = [section_body]

    slices: list[str] = []
    current_slice: list[str] = []
    current_tokens = 0

    for p in paragraphs:
        p_tokens = estimate_token_count(p)
        if current_tokens + p_tokens > max_tokens and current_slice:
            slices.append("\n\n".join(current_slice))
            current_slice = [p]
            current_tokens = p_tokens
        else:
            current_slice.append(p)
            current_tokens += p_tokens

    if current_slice:
        slices.append("\n\n".join(current_slice))

    total_parts = len(slices)
    results: list[tuple[str, int]] = []

    for idx, s in enumerate(slices, start=1):
        part_tag = f"Part {idx}/{total_parts}" if total_parts > 1 else ""
        header = base_header.replace("]\n\n", f" | {part_tag}]\n\n") if (part_tag and "]" in base_header) else base_header
        results.append((f"{header}{s}".strip(), page_number))

    return results


def split_legal_statute_text(
    full_text: str,
    statute_name: str = "",
    max_chunk_tokens: int = 600,
) -> list[tuple[str, int, str]]:
    """
    Section-Aware Legal Chunker:
    Extracts Sections, Articles, and Orders as atomic units with sticky headers.
    Returns: list of (chunk_text_with_header, page_number, section_heading)
    """
    page_segments = extract_page_segments(full_text)
    chunks_with_metadata: list[tuple[str, int, str]] = []

    current_chapter = ""
    current_section_heading = ""
    current_section_lines: list[str] = []
    section_start_page = 1

    for page_text, page_num in page_segments:
        lines = page_text.splitlines()

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_section_lines:
                    current_section_lines.append("")
                continue

            # Check Chapter marker
            chap_match = CHAPTER_REGEX.match(stripped)
            if chap_match:
                chap_num = chap_match.group(1)
                chap_title = chap_match.group(2).strip()
                current_chapter = f"Chapter {chap_num}" + (f": {chap_title}" if chap_title else "")

            # Check Section / Article / Order boundary
            sec_match = SECTION_HEADER_EXTRACT.match(stripped)
            art_match = ARTICLE_HEADER_EXTRACT.match(stripped) if not sec_match else None
            ord_match = ORDER_HEADER_EXTRACT.match(stripped) if not (sec_match or art_match) else None

            detected_heading = None
            if sec_match:
                s_num = sec_match.group(1) or sec_match.group(2)
                s_title = sec_match.group(3).strip()
                detected_heading = f"Section {s_num}" + (f": {s_title}" if s_title else "")
            elif art_match:
                a_num = art_match.group(1) or art_match.group(2)
                a_title = art_match.group(3).strip()
                detected_heading = f"Article {a_num}" + (f": {a_title}" if a_title else "")
            elif ord_match:
                o_num = ord_match.group(1)
                r_num = ord_match.group(2)
                o_title = ord_match.group(3).strip()
                sub = f" Rule {r_num}" if r_num else ""
                detected_heading = f"Order {o_num}{sub}" + (f": {o_title}" if o_title else "")

            if detected_heading:
                # Flush previous section
                if current_section_lines:
                    sec_body = "\n".join(current_section_lines).strip()
                    if sec_body and (current_section_heading or estimate_token_count(sec_body) >= 25):
                        tokens = estimate_token_count(sec_body)
                        base_header = build_context_header(
                            document_title=statute_name,
                            chapter_title=current_chapter,
                            section_heading=current_section_heading or "Preliminary",
                            page_number=section_start_page,
                        )
                        if tokens <= max_chunk_tokens:
                            chunk_text = f"{base_header}{sec_body}".strip()
                            chunks_with_metadata.append((chunk_text, section_start_page, current_section_heading))
                        else:
                            subchunks = split_section_into_subchunks(
                                section_body=sec_body,
                                base_header=base_header,
                                page_number=section_start_page,
                                max_tokens=max_chunk_tokens,
                            )
                            for sc_text, sc_page in subchunks:
                                chunks_with_metadata.append((sc_text, sc_page, current_section_heading))

                current_section_heading = detected_heading
                current_section_lines = [stripped]
                section_start_page = page_num
            else:
                # If this line was purely a chapter marker and we don't have an active section yet, don't accumulate it as body text
                if not current_section_heading and chap_match:
                    continue
                current_section_lines.append(stripped)

    # Flush final section
    if current_section_lines:
        sec_body = "\n".join(current_section_lines).strip()
        if sec_body:
            tokens = estimate_token_count(sec_body)
            base_header = build_context_header(
                document_title=statute_name,
                chapter_title=current_chapter,
                section_heading=current_section_heading or "Concluding Provisions",
                page_number=section_start_page,
            )
            if tokens <= max_chunk_tokens:
                chunk_text = f"{base_header}{sec_body}".strip()
                chunks_with_metadata.append((chunk_text, section_start_page, current_section_heading))
            else:
                subchunks = split_section_into_subchunks(
                    section_body=sec_body,
                    base_header=base_header,
                    page_number=section_start_page,
                    max_tokens=max_chunk_tokens,
                )
                for sc_text, sc_page in subchunks:
                    chunks_with_metadata.append((sc_text, sc_page, current_section_heading))

    return chunks_with_metadata


def split_legal_document_text(
    full_text: str,
    document_title: str = "",
    target_tokens: int = 400,
    max_tokens: int = 650,
    min_tokens: int = 50,
) -> list[tuple[str, int, str]]:
    """
    Paragraph & Heading-Aware Semantic Chunker:
    For contracts, petitions, judgments, textbooks, and Docling markdown.
    Returns: list of (chunk_text_with_header, page_number, section_heading)
    """
    page_segments = extract_page_segments(full_text)
    chunks_with_metadata: list[tuple[str, int, str]] = []

    active_heading = ""

    for page_text, page_num in page_segments:
        # Split by paragraphs or markdown headers
        raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", page_text) if p.strip()]

        current_group: list[str] = []
        current_tokens = 0
        group_heading = active_heading

        for p in raw_paragraphs:
            # Check if this paragraph is a Heading (e.g. ## Clause 4 or ALL CAPS line)
            h_match = MARKDOWN_OR_CAPS_HEADING.match(p)
            if h_match and len(p.splitlines()) == 1 and len(p) < 80:
                # Flush existing group
                if current_group:
                    body = "\n\n".join(current_group).strip()
                    header = build_context_header(
                        document_title=document_title,
                        section_heading=group_heading,
                        page_number=page_num,
                    )
                    chunks_with_metadata.append((f"{header}{body}".strip(), page_num, group_heading))
                    current_group = []
                    current_tokens = 0

                active_heading = p.lstrip("#").strip()
                group_heading = active_heading
                continue

            p_tokens = estimate_token_count(p)

            # If single paragraph exceeds max_tokens, split it by sentences
            if p_tokens > max_tokens:
                if current_group:
                    body = "\n\n".join(current_group).strip()
                    header = build_context_header(
                        document_title=document_title,
                        section_heading=group_heading,
                        page_number=page_num,
                    )
                    chunks_with_metadata.append((f"{header}{body}".strip(), page_num, group_heading))
                    current_group = []
                    current_tokens = 0

                sentences = re.split(r"(?<=[.!?])\s+", p)
                s_group: list[str] = []
                s_tokens = 0
                for s in sentences:
                    st = estimate_token_count(s)
                    if s_tokens + st > target_tokens and s_group:
                        s_body = " ".join(s_group).strip()
                        header = build_context_header(
                            document_title=document_title,
                            section_heading=group_heading,
                            page_number=page_num,
                        )
                        chunks_with_metadata.append((f"{header}{s_body}".strip(), page_num, group_heading))
                        s_group = [s]
                        s_tokens = st
                    else:
                        s_group.append(s)
                        s_tokens += st

                if s_group:
                    s_body = " ".join(s_group).strip()
                    header = build_context_header(
                        document_title=document_title,
                        section_heading=group_heading,
                        page_number=page_num,
                    )
                    chunks_with_metadata.append((f"{header}{s_body}".strip(), page_num, group_heading))
                continue

            if current_tokens + p_tokens > max_tokens and current_group:
                body = "\n\n".join(current_group).strip()
                header = build_context_header(
                    document_title=document_title,
                    section_heading=group_heading,
                    page_number=page_num,
                )
                chunks_with_metadata.append((f"{header}{body}".strip(), page_num, group_heading))
                current_group = [p]
                current_tokens = p_tokens
            else:
                current_group.append(p)
                current_tokens += p_tokens

        if current_group:
            body = "\n\n".join(current_group).strip()
            header = build_context_header(
                document_title=document_title,
                section_heading=group_heading,
                page_number=page_num,
            )
            chunks_with_metadata.append((f"{header}{body}".strip(), page_num, group_heading))

    return chunks_with_metadata


def split_legal_text(
    full_text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    document_title: str = "",
) -> list[tuple[str, int]]:
    """
    Unified Contextual Semantic Chunker:
    Auto-detects whether the document is a Bare Act / Statute or a General Document,
    applies structural parsing, and injects contextual sticky headers.
    Returns: list of (chunk_text_with_context, page_number)
    """
    if not full_text or not full_text.strip():
        return []

    if is_statutory_text(full_text):
        metadata_chunks = split_legal_statute_text(full_text, statute_name=document_title)
        return [(c[0], c[1]) for c in metadata_chunks]
    else:
        metadata_chunks = split_legal_document_text(full_text, document_title=document_title)
        return [(c[0], c[1]) for c in metadata_chunks]


async def ingest_document_chunks(
    document_id: int,
    session: AsyncSession,
    generate_embeddings: bool = False,
) -> int:
    """
    Ingests chunks into PostgreSQL with optional Weaviate vector embedding.
    When generate_embeddings is False, skips vector API calls and saves
    chunks directly with vector_id=None.
    """
    doc_query = select(Document).where(Document.id == document_id)
    doc_result = await session.execute(doc_query)
    doc = doc_result.scalar_one_or_none()

    if doc is None or not doc.extracted_text or not doc.extracted_text.strip():
        return 0

    case_query = select(CaseDocument.case_id).where(
        CaseDocument.document_id == document_id
    )
    case_result = await session.execute(case_query)
    case_id = case_result.scalar_one_or_none()

    # Apply contextual semantic chunking
    if is_statutory_text(doc.extracted_text):
        chunks_with_meta = split_legal_statute_text(doc.extracted_text, statute_name=doc.title)
    else:
        chunks_with_meta = split_legal_document_text(doc.extracted_text, document_title=doc.title)

    if not chunks_with_meta:
        return 0

    chunk_texts = [chunk[0] for chunk in chunks_with_meta]

    vectors: list[list[float]] | None = None
    if generate_embeddings:
        vectors = get_embeddings_batch(chunk_texts)

    for idx, (chunk_text, page_num, sec_heading) in enumerate(chunks_with_meta):
        weaviate_uuid = None
        if generate_embeddings and vectors:
            weaviate_uuid = store_chunk_vector(
                chunk_text=chunk_text,
                vector=vectors[idx],
                document_id=doc.id,
                user_id=doc.user_id,
                page_number=page_num,
                chunk_index=idx,
                case_id=case_id,
            )

        db_chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=idx,
            content=chunk_text,
            token_count=estimate_token_count(chunk_text),
            page_number=page_num,
            section_heading=sec_heading,
            vector_id=weaviate_uuid,
        )
        session.add(db_chunk)

    doc.processing_status = "indexed" if generate_embeddings else "chunked"
    session.add(doc)

    await session.commit()

    return len(chunks_with_meta)


async def ingest_document_chunks_v2(
    document_id: int,
    session: AsyncSession,
    generate_embeddings: bool = True,
) -> int:
    """
    V2 Document Ingestion:
    Uses the exact same common legal chunking logic, but routes post-chunking vectors
    to the V2 local 1024-D embedding pipeline (Octen-0.6B) and Weaviate LegalDocumentChunk_V2.
    """
    from app.services.embeddings_v2 import get_embeddings_batch_v2
    from app.services.vector_store_v2 import store_chunk_vector_v2

    doc_query = select(Document).where(Document.id == document_id)
    doc_result = await session.execute(doc_query)
    doc = doc_result.scalar_one_or_none()

    if doc is None or not doc.extracted_text or not doc.extracted_text.strip():
        return 0

    case_query = select(CaseDocument.case_id).where(
        CaseDocument.document_id == document_id
    )
    case_result = await session.execute(case_query)
    case_id = case_result.scalar_one_or_none()

    # Reuse COMMON contextual semantic chunking
    if is_statutory_text(doc.extracted_text):
        chunks_with_meta = split_legal_statute_text(doc.extracted_text, statute_name=doc.title)
    else:
        chunks_with_meta = split_legal_document_text(doc.extracted_text, document_title=doc.title)

    if not chunks_with_meta:
        return 0

    chunk_texts = [chunk[0] for chunk in chunks_with_meta]

    vectors: list[list[float]] | None = None
    if generate_embeddings:
        vectors = get_embeddings_batch_v2(chunk_texts)

    for idx, (chunk_text, page_num, sec_heading) in enumerate(chunks_with_meta):
        weaviate_uuid = None
        if generate_embeddings and vectors:
            weaviate_uuid = store_chunk_vector_v2(
                chunk_text=chunk_text,
                vector=vectors[idx],
                document_id=doc.id,
                user_id=doc.user_id,
                page_number=page_num,
                chunk_index=idx,
                case_id=case_id,
            )

        db_chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=idx,
            content=chunk_text,
            token_count=estimate_token_count(chunk_text),
            page_number=page_num,
            section_heading=sec_heading,
            vector_id=weaviate_uuid,
        )
        session.add(db_chunk)

    doc.processing_status = "indexed_v2" if generate_embeddings else "chunked"
    session.add(doc)

    await session.commit()

    return len(chunks_with_meta)


def parse_document_for_v2(
    file_path: str | Path,
    max_pages: int | None = None,
) -> tuple[str, int]:
    """
    V2 Document Parser:
    Extracts text from PDF, DOCX, or TXT preserving '--- [Page X] ---' markers.
    Fast, high-fidelity native statutory parser.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Document file not found at: {path}")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(str(path))
        total_pages = len(reader.pages)
        pages_to_process = min(total_pages, max_pages) if max_pages and max_pages > 0 else total_pages

        page_segments: list[str] = []
        for page_idx in range(pages_to_process):
            page_num = page_idx + 1
            try:
                page_text = reader.pages[page_idx].extract_text() or ""
                if page_text.strip():
                    page_segments.append(f"--- [Page {page_num}] ---\n{page_text.strip()}")
            except Exception:
                continue

        full_text = "\n\n".join(page_segments)
        return full_text, total_pages

    else:
        # Fallback to extraction service for DOCX, TXT, images
        from app.services.extraction import extract_document_text
        return extract_document_text(path)


def parse_and_chunk_document_v2(
    file_path: str | Path,
    document_title: str = "",
    max_pages: int | None = None,
    max_chunk_tokens: int = 600,
) -> list[dict[str, Any]]:
    """
    End-to-End V2 Pipeline:
    1. Parses document directly from file (extracting pages & markers).
    2. Auto-detects statutory vs general legal document.
    3. Runs section-aware semantic chunking with sticky breadcrumb header injection.
    
    Returns:
        List of structured chunk dictionaries.
    """
    path = Path(file_path)
    title = document_title or path.stem.replace("_", " ").title()

    full_text, total_pages = parse_document_for_v2(path, max_pages=max_pages)
    if not full_text or not full_text.strip():
        return []

    is_stat = is_statutory_text(full_text)
    if is_stat:
        chunk_tuples = split_legal_statute_text(full_text, statute_name=title, max_chunk_tokens=max_chunk_tokens)
    else:
        chunk_tuples = split_legal_document_text(full_text, document_title=title, max_tokens=max_chunk_tokens)

    all_chunks: list[dict[str, Any]] = []
    for idx, (chunk_text, page_num, sec_heading) in enumerate(chunk_tuples, start=1):
        all_chunks.append({
            "chunk_index": idx,
            "chunk_text": chunk_text,
            "page_number": page_num,
            "section_heading": sec_heading,
            "token_count": estimate_token_count(chunk_text),
            "char_count": len(chunk_text),
            "file_name": path.name,
            "total_pages": total_pages,
            "is_statutory": is_stat,
        })

    return all_chunks


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Parse and chunk legal documents using V2 Section-Aware Legal Chunker"
    )
    parser.add_argument(
        "--file",
        type=str,
        default="Legal Pdfs/the negotiable instruments act, 1881.pdf",
        help="Path to PDF or legal document to parse and chunk",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="Max pages to parse (default: 5)",
    )

    args = parser.parse_args()

    target_file = Path(args.file)
    if not target_file.is_file():
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        target_file = project_root / args.file

    print(f"\n=======================================================")
    print(f" V2 Legal Document Parser + Section-Aware Chunker Test")
    print(f"=======================================================")
    print(f"File:      {target_file}")
    print(f"Max Pages: {args.max_pages}")
    print(f"-------------------------------------------------------")

    chunks = parse_and_chunk_document_v2(target_file, max_pages=args.max_pages)
    print(f"[Success] Generated {len(chunks)} V2 semantic chunks!\n")

    preview_count = min(3, len(chunks))
    for i in range(preview_count):
        c = chunks[i]
        print(f"--- Chunk #{c['chunk_index']} (Page {c['page_number']} | Heading: '{c['section_heading']}' | Tokens: ~{c['token_count']}) ---")
        lines = c['chunk_text'].splitlines()
        preview = "\n".join(lines[:7])
        if len(lines) > 7:
            preview += f"\n... [{len(lines) - 7} more lines]"
        print(preview + "\n")