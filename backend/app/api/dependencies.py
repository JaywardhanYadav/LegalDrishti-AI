from collections.abc import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.database import get_db_session
from app.core.jwt import decode_token
from app.models.user import User

http_bearer_guard = HTTPBearer(
    auto_error=True,
    description="JWT Bearer token header authorization",
)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer_guard),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)

        if payload.get("type") != "access":
            raise credentials_exception

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise credentials_exception

        user_id = int(user_id_str)

    except (JWTError, ValueError):
        raise credentials_exception


    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail = "User account is deactivated",
        )

    return user

def require_role(allowed_roles: list[str]) -> Callable:
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {allowed_roles}",
            )
        return current_user
    return role_checker
