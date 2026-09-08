from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.models.case import Case
from app.models.user import User
from app.schemas.case import (
    CaseCreateRequest,
    CaseListResponse,
    CaseResponse,
    CaseUpdateRequest,
    CaseQARequest,
    CaseQAResponse,
    CaseSourceChunk,
)
from app.services.retrieval import generate_grounded_legal_answer


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
    items = list(items_result.scalars().all())

    return CaseListResponse(
        items=items,
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

    return case


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




