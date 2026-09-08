import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.case_document import CaseDocument
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embeddings import get_embeddings_batch
from app.services.vector_store import store_chunk_vector


def estimate_token_count(text: str)-> int:
    return max(1,len(text) // 4)


def split_legal_text(
        full_text: str,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
)-> list[tuple[str,int]]:

    if not full_text or not full_text.strip():
        return[]

    page_marker_regex = re.compile(r"---\s*\[Page\s*(\d+)\]\s*---", re.IGNORECASE)

    lines = full_text.splitlines()

    page_segments: list[tuple[str,int]] = []
    current_page = 1
    current_lines: list[str] = []

    for line in lines:
        match =  page_marker_regex.search(line)
        if match:
            if current_lines:
                page_text = "\n".join(current_lines).strip()
                if page_text:
                    page_segments.append((page_text, current_page))
                current_lines = []

            current_page = int(match.group(1))
        else:
            current_lines.append(line)


    if current_lines:
        page_text = "\n".join(current_lines).strip()
        if page_text:
            page_segments.append((page_text, current_page))       

    if not page_segments:
        page_segments = [(full_text.strip(), 1)]

    all_chunks: list[tuple[str, int]] = []

    for text, page_num in page_segments:
        if len(text) <= chunk_size:
            all_chunks.append((text, page_num))
            continue

        start = 0
        while start < len(text):
            end = start + chunk_size

            if end < len(text):
                
                break_point = text.rfind("\n\n", start, end)
                if break_point == -1:
                    break_point = text.rfind(". ", start, end)
                if break_point != -1 and break_point > start + (chunk_size // 2):
                    end = break_point + 1

            chunk_content = text[start:end].strip()
            if chunk_content:
                all_chunks.append((chunk_content, page_num))
            
            start = end - chunk_overlap
            if start < 0 or start >= len(text):
                break

    return all_chunks


async def ingest_document_chunks(
    document_id: int,
    session: AsyncSession,
) -> int:
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

    chunks_with_pages = split_legal_text(doc.extracted_text)

    if not chunks_with_pages:
        return 0

    chunk_texts = [chunk[0] for chunk in chunks_with_pages]

    vectors = get_embeddings_batch(chunk_texts)

    for idx, ((chunk_text, page_num), vector) in enumerate(
        zip(chunks_with_pages, vectors, strict=True)
    ):
        weaviate_uuid = store_chunk_vector(
            chunk_text=chunk_text,
            vector=vector,
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
            vector_id=weaviate_uuid,
        )

        session.add(db_chunk)

    doc.processing_status = "indexed"
    session.add(doc)

    await session.commit()

    return len(chunks_with_pages)