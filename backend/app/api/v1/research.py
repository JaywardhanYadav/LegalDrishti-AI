from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.schemas.research import LegalResearchRequest, LegalResearchResponse
from app.services.research import perform_legal_research
from app.core.security_guard import validate_and_sanitize_query


research_router = APIRouter(prefix="/research", tags=["Legal Research"])


@research_router.post(
    "/precedents",
    response_model=LegalResearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Deep Search: Retrieve Indian judicial precedents and ratio decidendi (Quota: 3 free credits)",
)
async def research_court_precedents(
    payload: LegalResearchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> LegalResearchResponse:

    payload.query = validate_and_sanitize_query(payload.query)
    if current_user.deep_search_credits <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You have exhausted your 3 free Deep Search credits. "
                "Please upgrade to a Pro plan for unlimited judicial precedent research."
            ),
        )

    
    try:
        research_result = perform_legal_research(payload)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deep Search engine encountered an error: {str(exc)}",
        )

    
    current_user.deep_search_credits -= 1
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    research_result.remaining_credits = current_user.deep_search_credits
    return research_result
