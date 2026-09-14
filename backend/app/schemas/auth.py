from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


class UserRegisterRequest(BaseModel):
    email: str = Field(
        ...,
        pattern=EMAIL_REGEX,
        description="Valid email address for login and notifications",
        examples=["advocate.sharma@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password must be at least 8 characters long",
    )
    full_name: str | None = Field(
        default=None,
        max_length=255,
        description="User's full name",
        examples=["Adv. Ramesh Sharma"],
    )
    role: str = Field(
        default="user",
        pattern="^(user|researcher|admin)$",
        description="User access role ('user', 'researcher', 'admin')",
    )


class UserLoginRequest(BaseModel):
    email: str = Field(
        ...,
        pattern=EMAIL_REGEX,
        description="Registered user email",
    )
    password: str = Field(
        ...,
        min_length=1,
        description="User account password",
    )


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    role: str
    is_active: bool
    deep_search_credits: int = 3
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str = Field(
        ...,
        description="JWT access token used for Authorization header",
    )
    refresh_token: str = Field(
        ...,
        description="Secure token used to generate a new access token",
    )
    token_type: str = Field(
        default="bearer",
        description="OAuth2 token type (bearer)",
    )
    expires_in: int = Field(
        ...,
        description="Access token lifespan in seconds",
    )


class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(
        ...,
        min_length=1,
        description="Valid refresh token string",
    )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(
        ...,
        min_length=1,
        description="Current account password",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (minimum 8 characters)",
    )


class ChangePasswordResponse(BaseModel):
    message: str = "Password updated successfully"