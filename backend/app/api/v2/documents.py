# backend/app/api/v2/documents.py
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.core.upload import compute_sha256, save_vault_file, validate_upload
from app.models.case import Case
from app.models.case_document import CaseDocument
from app.models.document import Document
from app.models.user import User
from app.services.extraction import extract_document_text
from app.services.chunking_v2 import ingest_document_chunks_v2
from app.schemas.document import DocumentResponse

documents_router_v2 = APIRouter(prefix="/documents", tags=["V2 Documents (Local Fine-Tuned Embedding Pipeline)"])


@documents_router_v2.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a document into V2 (Local 1024-D Vectors)",
)
async def upload_document_v2(
    file: UploadFile = File(...),
    title: str | None = Form(default=None, description="Optional custom title for the document"),
    document_type: str = Form(
        default="general",
        description="Category: petition, order, evidence, contract, general",
    ),
    case_id: int | None = Form(
        default=None,
        description="Optional case ID to link this document to",
    ),
    exhibit_label: str | None = Form(
        default=None,
        description="Optional exhibit label (e.g. 'Exhibit A')",
    ),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Document:
    file_bytes = await file.read()
    file_size = len(file_bytes)

    ext = validate_upload(
        file_name=file.filename,
        content_type=file.content_type,
        file_size_bytes=file_size,
    )

    file_hash = compute_sha256(file_bytes)

    duplicate_query = select(Document).where(
        Document.user_id == current_user.id,
        Document.file_hash == file_hash,
    )
    dup_result = await session.execute(duplicate_query)
    existing_doc = dup_result.scalar_one_or_none()

    if existing_doc is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This exact file already exists in your vault with title: "
                f"'{existing_doc.title}' (ID: {existing_doc.id})"
            ),
        )

    if case_id is not None:
        case_query = select(Case).where(
            Case.id == case_id,
            Case.user_id == current_user.id,
        )
        case_result = await session.execute(case_query)
        case = case_result.scalar_one_or_none()

        if case is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target case not found or does not belong to you",
            )

    saved_path, _ = save_vault_file(
        user_id=current_user.id,
        file_bytes=file_bytes,
        extension=ext,
    )

    effective_title = (
        title.strip()
        if title and title.strip()
        else (file.filename or "Untitled Document")
    )

    extracted_text = None
    processing_status = "uploaded"
    try:
        extracted_text, _ = extract_document_text(saved_path)
        processing_status = "extracted" if extracted_text else "uploaded"
    except Exception:
        processing_status = "extraction_failed"

    new_doc = Document(
        user_id=current_user.id,
        title=effective_title,
        file_name=file.filename or "unknown",
        file_path=saved_path,
        file_size_bytes=file_size,
        mime_type=file.content_type or "application/octet-stream",
        file_hash=file_hash,
        document_type=document_type,
        extracted_text=extracted_text,
        processing_status=processing_status,
    )

    session.add(new_doc)
    await session.flush()

    if case_id is not None:
        case_doc = CaseDocument(
            case_id=case_id,
            document_id=new_doc.id,
            exhibit_label=exhibit_label,
        )
        session.add(case_doc)

    await session.commit()

    # V2 Ingestion: Common chunking + Local 1024-D Vectors into Weaviate V2
    if extracted_text:
        try:
            await ingest_document_chunks_v2(new_doc.id, session, generate_embeddings=True)
        except Exception as exc:
            print(f"[V2 Ingestion Notice] Failed to index document {new_doc.id} in V2: {exc}")

    await session.refresh(new_doc)
    return new_doc
