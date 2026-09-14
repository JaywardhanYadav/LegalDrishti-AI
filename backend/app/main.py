
from fastapi import FastAPI
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.api.router import api_router
from fastapi.middleware.cors import CORSMiddleware
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from app.core.database import engine
from pathlib import Path
from fastapi.staticfiles import StaticFiles



configure_logging()
logger = get_logger(__name__)


settings = get_settings()

allowed_origins = [
    origin.strip()
    for origin in settings.cors_origins.split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "application_startup",
        environment = settings.app_env,
        api_version = "v1"
    )

    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS session_id INTEGER REFERENCES chat_sessions(id) ON DELETE SET NULL;"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_session_id ON documents (session_id);"))
    except Exception as db_err:
        logger.warning(f"Database schema auto-check notice: {db_err}")

    yield

    logger.info("application_shutdown")

    await engine.dispose()



app = FastAPI(
    title="LegalDrishti AI",
    description="AI-POWERED LEGAL RESEARCH, ANALYSIS AND DRAFTING SUPPORT",
    version="0.1.0",
    debug=settings.app_env == "development",
    lifespan=lifespan, 
)

logger.info(
    "application_configured",
    environment = settings.app_env,
    api_version = "v1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials = True,
    allow_methods = ['GET',"POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)



app.include_router(api_router)

@app.get("/health",tags=["system"])
async def health_check() -> dict[str,str]:
    """Return the application health status"""
    return{
        "status" : "ok",
        "environment" : settings.app_env,
    }

frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")