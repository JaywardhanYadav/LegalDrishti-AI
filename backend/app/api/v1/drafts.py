
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.models.case import Case
from app.models.draft import Draft
from app.models.user import User
from app.schemas.draft import (
    DraftGenerateRequest,
    DraftListResponse,
    DraftResponse,
    DraftUpdateRequest,
)
from app.services.drafting import generate_legal_draft, run_statutory_validation

drafts_router = APIRouter(prefix="/drafts", tags=["Drafts"])


@drafts_router.post(
    "/generate",
    response_model=DraftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a structured court-ready legal draft",
)
async def create_legal_draft(
    payload: DraftGenerateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Draft:
    # If case_id provided, verify ownership
    if payload.case_id:
        stmt = select(Case).where(Case.id == payload.case_id, Case.user_id == current_user.id)
        res = await session.execute(stmt)
        if not res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target case not found or does not belong to you",
            )

    draft = await generate_legal_draft(
        user_id=current_user.id,
        payload=payload,
        session=session,
    )
    return draft


@drafts_router.get(
    "",
    response_model=DraftListResponse,
    summary="List all generated legal drafts for the current user",
)
async def list_drafts(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    case_id: int | None = Query(default=None, description="Filter by case ID"),
    draft_type: str | None = Query(default=None, description="Filter by draft type"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DraftListResponse:
    filters = [Draft.user_id == current_user.id]

    if case_id is not None:
        filters.append(Draft.case_id == case_id)
    if draft_type is not None:
        filters.append(Draft.draft_type == draft_type)

    count_query = select(func.count()).select_from(Draft).where(*filters)
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    items_query = (
        select(Draft)
        .where(*filters)
        .order_by(Draft.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    items_result = await session.execute(items_query)
    items = list(items_result.scalars().all())

    return DraftListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@drafts_router.get(
    "/{draft_id}",
    response_model=DraftResponse,
    summary="Get details of a single legal draft",
)
async def get_draft(
    draft_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Draft:
    stmt = select(Draft).where(Draft.id == draft_id, Draft.user_id == current_user.id)
    res = await session.execute(stmt)
    draft = res.scalar_one_or_none()

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )

    return draft


@drafts_router.patch(
    "/{draft_id}",
    response_model=DraftResponse,
    summary="Update an existing legal draft (saves in-browser edits and re-validates)",
)
async def update_draft(
    draft_id: int,
    payload: DraftUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Draft:
    stmt = select(Draft).where(Draft.id == draft_id, Draft.user_id == current_user.id)
    res = await session.execute(stmt)
    draft = res.scalar_one_or_none()

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "content" in update_data and update_data["content"]:
        # Re-run statutory compliance on advocate's edits
        new_status, new_report = run_statutory_validation(
            draft_type=draft.draft_type,
            content=update_data["content"],
        )
        draft.validation_status = new_status
        draft.validation_report = new_report
        draft.version += 1

    for field, value in update_data.items():
        setattr(draft, field, value)

    session.add(draft)
    await session.commit()
    await session.refresh(draft)

    return draft


@drafts_router.delete(
    "/{draft_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a legal draft permanently",
)
async def delete_draft(
    draft_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    stmt = select(Draft).where(Draft.id == draft_id, Draft.user_id == current_user.id)
    res = await session.execute(stmt)
    draft = res.scalar_one_or_none()

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )

    await session.delete(draft)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
