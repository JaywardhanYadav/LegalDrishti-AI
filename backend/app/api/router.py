from fastapi import APIRouter
from app.api.v1.auth import auth_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)

@api_router.get("/health",tags=["System"])
async def api_health_check() -> dict[str,str]:
    return {
        "status":"ok",
        "api_version":"v1",
    }