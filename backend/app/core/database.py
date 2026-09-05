from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import(
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo = False,
    pool_pre_ping = True,
)


async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    """
    Base declarative class.
    All database tables (Users, Cases, Documents, etc.) will inherit from this class.
    """

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            # Roll back any uncommitted changes on error to maintain data integrity
            await session.rollback()
            raise