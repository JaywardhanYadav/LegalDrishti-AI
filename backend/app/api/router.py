
from fastapi import APIRouter
from app.api.v1.auth import auth_router
from app.api.v1.cases import cases_router
from app.api.v1.documents import documents_router
from app.api.v1.research import research_router
from app.api.v1.drafts import drafts_router
from app.api.v1.chat import chat_router


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(cases_router)
api_router.include_router(cases_router, prefix="/vaults", tags=["Vaults"])
api_router.include_router(documents_router)
api_router.include_router(research_router)
api_router.include_router(drafts_router)


@api_router.get("/health", tags=["System"])
async def api_health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "api_version": "v1",
    }
