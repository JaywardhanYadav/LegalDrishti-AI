"""
Version 1 Chunking Service: Docling Parser + LangChain Recursive Character Splitter
=====================================================================================
Uses IBM Docling for structural layout extraction (Markdown conversion preserving
tables, headers, and document hierarchy) followed by LangChain's
RecursiveCharacterTextSplitter for legal-aware character/clause chunking.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter


class DoclingChunkerError(Exception):
    """Raised when Docling parsing or LangChain chunking encounters an error."""
    pass


def estimate_token_count(text: str) -> int:
    """Rough estimation of token count (~4 characters per token)."""
    return max(1, len(text) // 4)


def parse_document_with_docling(
    file_path: str | Path,
    max_pages: int | None = None,
    do_ocr: bool = False,
) -> tuple[str, dict[str, Any]]:
    """
    Parses a PDF or DOCX file into structured Markdown using IBM Docling.
    
    Retains:
    - Tables in clean Markdown format
    - Document headings (#, ##, ###)
    - Structural hierarchy and paragraphs
    
    Returns:
        (markdown_text, metadata_dict)
    """
    path = Path(file_path)
    if not path.is_file():
        raise DoclingChunkerError(f"File not found: {path}")

    start_time = time.time()

    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = do_ocr

        converter = DocumentConverter(
            format_options={
                "pdf": PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        convert_kwargs: dict[str, Any] = {}
        if max_pages is not None and max_pages > 0:
            convert_kwargs["page_range"] = (1, max_pages)

        result = converter.convert(str(path), **convert_kwargs)
        markdown_text = result.document.export_to_markdown()

        total_pages = 1
        if hasattr(result.document, "pages") and result.document.pages:
            total_pages = len(result.document.pages)

        elapsed = time.time() - start_time

        metadata = {
            "file_name": path.name,
            "file_path": str(path.resolve()),
            "total_pages": total_pages,
            "markdown_chars": len(markdown_text),
            "parsing_time_seconds": round(elapsed, 2),
            "parser": "IBM Docling",
        }

        return markdown_text.strip(), metadata

    except Exception as exc:
        raise DoclingChunkerError(f"Docling parsing failed for '{path.name}': {exc}") from exc


def get_legal_recursive_splitter(
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> RecursiveCharacterTextSplitter:
    """
    Instantiates LangChain's RecursiveCharacterTextSplitter with separators
    tailored specifically for legal Markdown documents.
    """
    separators = [
        "\n# ",
        "\n## ",
        "\n### ",
        "\n#### ",
        "\n\n",
        "\n",
        ". ",
        "; ",
        " ",
        "",
    ]

    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
        length_function=len,
        is_separator_regex=False,
    )


def extract_heading_breadcrumb(chunk_text: str) -> str:
    """Extracts the first markdown heading found in a chunk as a breadcrumb context."""
    for line in chunk_text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return ""


def split_document_v1(
    file_path: str | Path,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    max_pages: int | None = None,
    do_ocr: bool = False,
    inject_context_header: bool = True,
) -> list[dict[str, Any]]:
    """
    V1 Chunking Pipeline:
    1. Parses document to structured Markdown via IBM Docling.
    2. Splits markdown via LangChain RecursiveCharacterTextSplitter.
    3. Injects breadcrumb context header.
    """
    markdown_text, doc_metadata = parse_document_with_docling(
        file_path=file_path,
        max_pages=max_pages,
        do_ocr=do_ocr,
    )

    if not markdown_text:
        return []

    splitter = get_legal_recursive_splitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    raw_chunks = splitter.split_text(markdown_text)

    doc_title = Path(file_path).stem.replace("_", " ").title()
    chunks: list[dict[str, Any]] = []
    current_active_heading = ""

    for idx, raw_chunk in enumerate(raw_chunks):
        cleaned = raw_chunk.strip()
        if not cleaned:
            continue

        detected_heading = extract_heading_breadcrumb(cleaned)
        if detected_heading:
            current_active_heading = detected_heading

        final_chunk_text = cleaned
        if inject_context_header and current_active_heading:
            header_prefix = f"[{doc_title} | {current_active_heading}]\n\n"
            if not final_chunk_text.startswith("["):
                final_chunk_text = f"{header_prefix}{final_chunk_text}"

        chunks.append({
            "chunk_index": idx,
            "chunk_text": final_chunk_text,
            "raw_text": cleaned,
            "token_count": estimate_token_count(final_chunk_text),
            "char_count": len(final_chunk_text),
            "heading": current_active_heading,
            "file_name": doc_metadata["file_name"],
            "total_pages": doc_metadata["total_pages"],
        })

    return chunks


# Alias for backwards compatibility
chunk_document_with_docling = split_document_v1
