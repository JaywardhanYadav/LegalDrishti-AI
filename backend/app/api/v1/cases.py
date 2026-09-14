from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security_guard import validate_and_sanitize_query
from app.core.redis_client import delete_keys_by_pattern

from app.api.dependencies import get_current_user, get_db_session
from app.models.case import Case
from app.models.case_document import CaseDocument
from app.models.document import Document
from app.models.user import User
from app.schemas.case import (
    CaseCreateRequest,
    CaseDocItem,
    CaseListResponse,
    CaseResponse,
    CaseUpdateRequest,
    CaseQARequest,
    CaseQAResponse,
    CaseSourceChunk,
)
from app.services.retrieval import generate_grounded_legal_answer
from app.services.vector_store import delete_chunks_by_case, delete_all_chunks_by_user



cases_router = APIRouter(prefix="/cases", tags=["Cases"])


@cases_router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new case workspace",
)
async def create_case(
    payload: CaseCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Case:
    new_case = Case(
        user_id=current_user.id,
        title=payload.title,
        case_number=payload.case_number,
        court_name=payload.court_name,
        case_type=payload.case_type,
        status=payload.status,
        client_name=payload.client_name,
        opponent_name=payload.opponent_name,
        description=payload.description,
        hearing_date=payload.hearing_date,
    )

    session.add(new_case)
    await session.commit()
    await session.refresh(new_case)

    return new_case


@cases_router.get(
    "",
    response_model=CaseListResponse,
    summary="List all cases for the current user",
)
async def list_cases(
    page: int = Query(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
    ),
    page_size: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Items per page",
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by case status",
    ),
    search: str | None = Query(
        default=None,
        description="Search by title, case number, or client name",
    ),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CaseListResponse:
    filters = [Case.user_id == current_user.id]

    if status_filter:
        filters.append(Case.status == status_filter)

    if search:
        search_term = f"%{search}%"
        filters.append(
            or_(
                Case.title.ilike(search_term),
                Case.case_number.ilike(search_term),
                Case.client_name.ilike(search_term),
            )
        )

    count_query = select(func.count()).select_from(Case).where(*filters)
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size

    items_query = (
        select(Case)
        .where(*filters)
        .order_by(Case.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    items_result = await session.execute(items_query)
    cases = list(items_result.scalars().all())

    case_ids = [c.id for c in cases]
    docs_by_case: dict[int, list[CaseDocItem]] = {c.id: [] for c in cases}
    if case_ids:
        docs_query = (
            select(CaseDocument.case_id, Document)
            .join(Document, CaseDocument.document_id == Document.id)
            .where(CaseDocument.case_id.in_(case_ids))
            .order_by(Document.created_at.desc())
        )
        docs_result = await session.execute(docs_query)
        for c_id, doc in docs_result.all():
            docs_by_case[c_id].append(
                CaseDocItem(
                    id=doc.id,
                    name=doc.file_name or doc.title or "Document",
                    type=doc.document_type or ("PDF Contract" if (doc.file_name or "").endswith(".pdf") else "Legal Document"),
                    submitted=True,
                    status="Submitted",
                    backendId=doc.id,
                    created_at=doc.created_at,
                )
            )

    response_items = []
    for c in cases:
        response_items.append(
            CaseResponse(
                id=c.id,
                user_id=c.user_id,
                title=c.title,
                case_number=c.case_number,
                court_name=c.court_name,
                case_type=c.case_type,
                status=c.status,
                client_name=c.client_name,
                opponent_name=c.opponent_name,
                description=c.description,
                hearing_date=c.hearing_date,
                created_at=c.created_at,
                updated_at=c.updated_at,
                docs=docs_by_case.get(c.id, []),
            )
        )

    return CaseListResponse(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@cases_router.get(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Get details of a single case",
)
async def get_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CaseResponse:
    query = select(Case).where(
        Case.id == case_id,
        Case.user_id == current_user.id,
    )

    result = await session.execute(query)
    case = result.scalar_one_or_none()

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    docs_query = (
        select(Document)
        .join(CaseDocument, CaseDocument.document_id == Document.id)
        .where(CaseDocument.case_id == case_id)
        .order_by(Document.created_at.desc())
    )
    docs_result = await session.execute(docs_query)
    docs = [
        CaseDocItem(
            id=doc.id,
            name=doc.file_name or doc.title or "Document",
            type=doc.document_type or ("PDF Contract" if (doc.file_name or "").endswith(".pdf") else "Legal Document"),
            submitted=True,
            status="Submitted",
            backendId=doc.id,
            created_at=doc.created_at,
        )
        for doc in docs_result.scalars().all()
    ]

    return CaseResponse(
        id=case.id,
        user_id=case.user_id,
        title=case.title,
        case_number=case.case_number,
        court_name=case.court_name,
        case_type=case.case_type,
        status=case.status,
        client_name=case.client_name,
        opponent_name=case.opponent_name,
        description=case.description,
        hearing_date=case.hearing_date,
        created_at=case.created_at,
        updated_at=case.updated_at,
        docs=docs,
    )


@cases_router.patch(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Update an existing case",
)
async def update_case(
    case_id: int,
    payload: CaseUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Case:
    query = select(Case).where(
        Case.id == case_id,
        Case.user_id == current_user.id,
    )

    result = await session.execute(query)
    case = result.scalar_one_or_none()

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        setattr(case, field_name, value)

    session.add(case)
    await session.commit()
    await session.refresh(case)

    return case


@cases_router.delete(
    "/purge-all",
    summary="Permanently purge all case matters and uploaded documents for the current user",
)
async def purge_all_user_data(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Safely and permanently deletes all cases, case-document associations, 
    and uploaded documents belonging to the authenticated user."""
    # 1. Fetch user's documents
    doc_query = select(Document).where(Document.user_id == current_user.id)
    doc_res = await session.execute(doc_query)
    user_docs = doc_res.scalars().all()

    for doc in user_docs:
        try:
            if doc.file_path:
                Path(doc.file_path).unlink(missing_ok=True)
        except OSError:
            pass
        await session.delete(doc)

    # 2. Fetch user's cases
    case_query = select(Case).where(Case.user_id == current_user.id)
    case_res = await session.execute(case_query)
    user_cases = case_res.scalars().all()

    for case in user_cases:
        try:
            delete_keys_by_pattern(f"rag:case:{case.id}:*")
        except Exception:
            pass
        await session.delete(case)

    # Purge all vector embeddings in Weaviate for this user
    try:
        delete_all_chunks_by_user(current_user.id)
    except Exception as e:
        print(f"Weaviate purge warning: {e}")

    await session.commit()
    return {"status": "success", "message": "All user case files and vault documents purged successfully."}


@cases_router.delete(
    "/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a case workspace",
)
async def delete_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    query = select(Case).where(
        Case.id == case_id,
        Case.user_id == current_user.id,
    )

    result = await session.execute(query)
    case = result.scalar_one_or_none()

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    # Purge Weaviate vectors for this vault
    try:
        delete_chunks_by_case(case_id)
    except Exception as e:
        print(f"Weaviate case chunk delete warning: {e}")

    await session.delete(case)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)



@cases_router.post(
    "/{case_id}/qa",
    response_model=CaseQAResponse,
    summary="Grounded Dual-Stream Legal Q&A against Case Brief & Indian Statutes",
)
async def ask_case_question(
    case_id: int,
    payload: CaseQARequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CaseQAResponse:

    payload.query = validate_and_sanitize_query(payload.query)

    stmt = select(Case).where(Case.id == case_id, Case.user_id == current_user.id)
    result = await session.execute(stmt)
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or unauthorized",
        )

    rag_result = await generate_grounded_legal_answer(
        query=payload.query,
        user_id=current_user.id,
        session=session,
        case_id=case_id,
        candidate_pool_size=payload.candidate_pool_size,
        top_k=payload.top_k,
        alpha=payload.alpha,
    )

    sources = [
        CaseSourceChunk(
            source_type=s.get("source_type"),
            document_title=s["document_title"],
            page_number=s["page_number"],
            score=s.get("score"),
        )
        for s in rag_result.get("sources", [])
    ]

    return CaseQAResponse(
        case_id=case_id,
        query=payload.query,
        answer=rag_result["answer"],
        sources=sources,
        grounded=rag_result["grounded"],
    )




