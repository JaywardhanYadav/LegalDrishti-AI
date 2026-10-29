from fastapi import APIRouter
from app.api.v2.chat import chat_router_v2
from app.api.v2.documents import documents_router_v2

api_router_v2 = APIRouter(prefix="/api/v2")

api_router_v2.include_router(chat_router_v2)
api_router_v2.include_router(documents_router_v2)


@api_router_v2.get("/health", tags=["System V2"])
async def api_v2_health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "api_version": "v2",
        "embedding_engine": "Octen-0.6B Fine-Tuned (1024-D Local)",
        "generation_engine": "OpenAI GPT-4o",
        "chunking": "Common Contextual Legal Chunker",
    }
