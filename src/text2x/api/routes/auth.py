"""Authentication endpoints."""
import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from text2x.api.auth import (
    User,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_active_user,
    get_current_user,
    verify_password,
)
from text2x.api.models import ErrorResponse
from text2x.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request model."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password", min_length=8)


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str = Field(..., description="Refresh token to exchange for new access token")


class UserResponse(BaseModel):
    """User information response."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    roles: list[str] = Field(default_factory=list, description="User roles")
    is_active: bool = Field(..., description="User active status")


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login and get JWT token",
    description="Authenticate with email and password to receive JWT access and refresh tokens",
)
async def login(credentials: LoginRequest) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.

    This endpoint validates user credentials and returns both access and refresh tokens.
    The access token is short-lived and used for API authentication.
    The refresh token is long-lived and used to obtain new access tokens.

    In a production system, this would:
    1. Look up user by email in database
    2. Verify password hash
    3. Check if user account is active
    4. Generate and return tokens

    For now, this is a placeholder implementation that accepts any credentials.
    You should implement proper user authentication with database lookup.

    Args:
        credentials: User login credentials

    Returns:
        JWT access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid (401)
    """
    try:
        logger.info(f"Login attempt for user: {credentials.email}")

        # Authenticate user with database
        from text2x.repositories.user import UserRepository

        repository = UserRepository()
        user = await repository.authenticate(credentials.email, credentials.password)

        if user is None:
            logger.warning(f"Invalid login attempt for: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Get user ID and roles
        user_id = str(user.id)
        user_email = user.email
        # Handle role - it might be an enum or a string
        user_role = user.role.value if hasattr(user.role, 'value') else user.role
        user_roles = [user_role]

        # Generate tokens
        access_token = create_access_token(
            user_id=user_id,
            email=user_email,
            roles=user_roles,
        )

        refresh_token = create_refresh_token(
            user_id=user_id,
            email=user_email,
            roles=user_roles,
        )

        logger.info(f"User logged in successfully: {user_email}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_expire_minutes * 60,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="login_error",
                message="Failed to process login",
            ).model_dump(),
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token",
)
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    """
    Refresh access token using a refresh token.

    This endpoint validates the refresh token and issues a new access token.
    Refresh tokens are long-lived and should be stored securely by the client.

    Args:
        request: Refresh token request

    Returns:
        New JWT access token and refresh token

    Raises:
        HTTPException: If refresh token is invalid or expired (401)
    """
    try:
        logger.info("Token refresh requested")

        # Decode and validate the refresh token
        token_data = decode_token(request.refresh_token)

        # In production, you should:
        # 1. Verify the token hasn't been revoked
        # 2. Check if user still exists and is active
        # 3. Potentially verify token type is "refresh"

        # Generate new tokens
        access_token = create_access_token(
            user_id=token_data.user_id,
            email=token_data.email,
            roles=token_data.roles,
        )

        refresh_token = create_refresh_token(
            user_id=token_data.user_id,
            email=token_data.email,
            roles=token_data.roles,
        )

        logger.info(f"Token refreshed for user: {token_data.email}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_expire_minutes * 60,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="refresh_error",
                message="Failed to refresh token",
            ).model_dump(),
        )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get information about the currently authenticated user",
)
async def get_me(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """
    Get current user information.

    This endpoint returns information about the currently authenticated user
    based on the JWT token or API key provided in the request.

    This endpoint always requires authentication, even if auth is optional elsewhere.

    Args:
        current_user: Current authenticated user (from JWT or API key)

    Returns:
        User information

    Raises:
        HTTPException: If not authenticated (401)
    """
    try:
        logger.info(f"User info requested for: {current_user.email}")

        return UserResponse(
            id=current_user.id,
            email=current_user.email,
            roles=current_user.roles,
            is_active=current_user.is_active,
        )

    except Exception as e:
        logger.error(f"Error fetching user info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch user information",
            ).model_dump(),
        )
