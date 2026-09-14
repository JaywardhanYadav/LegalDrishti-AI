from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session

from app.core.jwt import(
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_token,
)

from app.core.security import hash_password, verify_password

from app.models.user import User

from app.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

auth_router = APIRouter(prefix="/auth",tags=["Authentication"])

@auth_router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account"
)
async def register_user(
    payload: UserRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
)-> User:

    exsiting_query = select(User).where(User.email == payload.email)
    result = await session.execute(exsiting_query)
    exsting_user = result.scalar_one_or_none()

    if exsting_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with email address alredy exists"
        )

    hashed_pwd = hash_password(payload.password)

    new_user = User(
        email = payload.email,
        hashed_password = hashed_pwd,
        full_name = payload.full_name,
        role = payload.role,
        is_active = True,
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return new_user

@auth_router.post(
    '/login',
    response_model=TokenResponse,
    summary="Autheenticate user and return JWT tokens"
)
async def login_user(
    payload: UserLoginRequest,
    session: AsyncSession = Depends(get_db_session),
)->TokenResponse:

    query = select(User).where(User.email == payload.email)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password,user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate":"bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    access_token = create_access_token(
        subject= user.id,
        extra_claims={"role": user.role, "email": user.email},
    )

    refresh_token = create_refresh_token(subject=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Obtain a new access token using a refresh token",
)
async def refresh_access_token(
    payload: TokenRefreshRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Validate refresh token and issue a fresh access token.
    """
    unauthorized_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = decode_token(payload.refresh_token)
        # Enforce that only refresh tokens can be used here
        if token_data.get("type") != "refresh":
            raise unauthorized_error
        user_id_str = token_data.get("sub")
        if not user_id_str:
            raise unauthorized_error
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise unauthorized_error

    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise unauthorized_error

    new_access_token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role, "email": user.email},
    )

    new_refresh_token = create_refresh_token(subject=user.id)
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

@auth_router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current logged-in user profile",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


@auth_router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    summary="Change user password with current password verification",
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChangePasswordResponse:
    """Securely update the user's password after verifying existing credentials."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password entered is incorrect.",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password.",
        )

    current_user.hashed_password = hash_password(payload.new_password)
    session.add(current_user)
    await session.commit()

    return ChangePasswordResponse(message="Password successfully updated.")