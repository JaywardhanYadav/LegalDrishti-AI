# backend/app/api/v1/documents.py
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.core.upload import compute_sha256, save_vault_file, validate_upload
from app.core.redis_client import delete_keys_by_pattern
from app.models.case import Case
from app.models.case_document import CaseDocument
from app.models.document import Document
from app.models.user import User
from app.services.extraction import extract_document_text
from app.services.chunking import ingest_document_chunks
from app.services.vector_store import delete_chunks_by_document
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
)

documents_router = APIRouter(prefix="/documents", tags=["Documents"])


@documents_router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new legal document to the vault",
)
async def upload_document(
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

    if extracted_text:
        try:
            await ingest_document_chunks(new_doc.id, session)
        except Exception:
            pass

    # Invalidate cached RAG queries for this case
    if case_id is not None:
        flushed = delete_keys_by_pattern(f"rag:case:{case_id}:*")
        if flushed > 0:
            print(f"[Redis Cache Invalidation] Flushed {flushed} cached RAG entries for Case {case_id}")

    await session.refresh(new_doc)
    return new_doc


@documents_router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all documents in the user's vault",
)
async def list_documents(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    document_type: str | None = Query(default=None, description="Filter by document type"),
    search: str | None = Query(default=None, description="Search across title and file name"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentListResponse:
    filters = [Document.user_id == current_user.id]

    if document_type:
        filters.append(Document.document_type == document_type)

    if search:
        search_term = f"%{search}%"
        filters.append(
            or_(
                Document.title.ilike(search_term),
                Document.file_name.ilike(search_term),
            )
        )

    count_query = select(func.count()).select_from(Document).where(*filters)
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    items_query = (
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    items_result = await session.execute(items_query)
    items = list(items_result.scalars().all())

    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@documents_router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get details of a single document including extracted text",
)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Document:
    query = select(Document).where(
        Document.id == document_id,
        Document.user_id == current_user.id,
    )

    result = await session.execute(query)
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return doc


@documents_router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Update document title or document type",
)
async def update_document(
    document_id: int,
    payload: DocumentUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Document:
    query = select(Document).where(
        Document.id == document_id,
        Document.user_id == current_user.id,
    )

    result = await session.execute(query)
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(doc, field_name, value)

    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    return doc


@documents_router.delete(
    "/purge-all",
    summary="Permanently delete all documents uploaded by the current user",
)
async def purge_all_user_documents(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Safely and permanently deletes all uploaded documents, linked case records, 
    and physical files belonging to the authenticated user."""
    query = select(Document).where(Document.user_id == current_user.id)
    res = await session.execute(query)
    user_docs = res.scalars().all()

    for doc in user_docs:
        # Find cases linked to this doc to invalidate cache
        case_query = select(CaseDocument.case_id).where(CaseDocument.document_id == doc.id)
        case_res = await session.execute(case_query)
        linked_case_ids = case_res.scalars().all()

        try:
            if doc.file_path:
                Path(doc.file_path).unlink(missing_ok=True)
        except OSError:
            pass

        await session.delete(doc)

        for c_id in linked_case_ids:
            try:
                delete_keys_by_pattern(f"rag:case:{c_id}:*")
            except Exception:
                pass

    await session.commit()
    return {"status": "success", "message": "All user uploaded documents have been permanently deleted."}


@documents_router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document permanently",
)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    query = select(Document).where(
        Document.id == document_id,
        Document.user_id == current_user.id,
    )

    result = await session.execute(query)
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Find cases linked to this document to invalidate their cache
    case_query = select(CaseDocument.case_id).where(CaseDocument.document_id == document_id)
    case_res = await session.execute(case_query)
    linked_case_ids = case_res.scalars().all()

    try:
        Path(doc.file_path).unlink(missing_ok=True)
    except OSError:
        pass

    # Delete vector embeddings from Weaviate
    try:
        delete_chunks_by_document(document_id)
    except Exception as e:
        print(f"Weaviate chunk deletion warning: {e}")

    await session.delete(doc)
    await session.commit()

    for c_id in linked_case_ids:
        delete_keys_by_pattern(f"rag:case:{c_id}:*")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
