"""User management endpoints."""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from text2x.api.auth import (
    User as AuthUser,
    get_current_active_user,
    require_role,
)
from text2x.api.models import ErrorResponse
from text2x.config import settings
from text2x.models.user import UserRole
from text2x.repositories.user import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateUserRequest(BaseModel):
    """Request to create a new user."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password", min_length=8)
    name: str = Field(..., description="User's full name")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    is_active: bool = Field(default=True, description="Whether user is active")


class UpdateUserRequest(BaseModel):
    """Request to update user details."""

    email: Optional[EmailStr] = Field(None, description="New email address")
    name: Optional[str] = Field(None, description="New name")
    role: Optional[UserRole] = Field(None, description="New role")
    is_active: Optional[bool] = Field(None, description="New active status")


class UpdatePasswordRequest(BaseModel):
    """Request to update password."""

    current_password: str = Field(..., description="Current password", min_length=8)
    new_password: str = Field(..., description="New password", min_length=8)


class UpdateOwnPasswordRequest(BaseModel):
    """Request to update own password."""

    current_password: str = Field(..., description="Current password", min_length=8)
    new_password: str = Field(..., description="New password", min_length=8)


class UpdateOwnProfileRequest(BaseModel):
    """Request to update own profile."""

    name: Optional[str] = Field(None, description="New name")
    email: Optional[EmailStr] = Field(None, description="New email address")


class RegisterRequest(BaseModel):
    """Self-registration request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password", min_length=8)
    name: str = Field(..., description="User's full name")


class UserResponse(BaseModel):
    """User information response."""

    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User's full name")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(..., description="User active status")
    created_at: str = Field(..., description="When user was created")
    updated_at: str = Field(..., description="When user was last updated")

    class Config:
        from_attributes = True


# ============================================================================
# Admin Endpoints (Super Admin Only)
# ============================================================================


@router.post(
    "/admin/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user (super admin only)",
    dependencies=[Depends(require_role("super_admin"))],
)
async def create_user(
    request: CreateUserRequest,
    current_user: AuthUser = Depends(get_current_active_user),
) -> UserResponse:
    """
    Create a new user.

    Only super admins can create users. This endpoint allows creating users
    with any role, including other super admins.

    Args:
        request: User creation request
        current_user: Current authenticated super admin

    Returns:
        Created user information

    Raises:
        HTTPException: If user creation fails (e.g., email already exists)
    """
    try:
        logger.info(
            f"Creating user {request.email} with role {request.role} by {current_user.email}"
        )

        repository = UserRepository()
        user = await repository.create_user(
            email=request.email,
            password=request.password,
            name=request.name,
            role=request.role,
            is_active=request.is_active,
        )

        logger.info(f"User created successfully: {user.id}")

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to create user: {e}", exc_info=True)
        if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )


@router.get(
    "/admin/users",
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List users",
    description="List all users (super admin only)",
    dependencies=[Depends(require_role("super_admin"))],
)
async def list_users(
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    current_user: AuthUser = Depends(get_current_active_user),
) -> List[UserResponse]:
    """
    List all users with optional filters.

    Only super admins can list users.

    Args:
        role: Filter by role (optional)
        is_active: Filter by active status (optional)
        current_user: Current authenticated super admin

    Returns:
        List of users
    """
    try:
        logger.info(f"Listing users by {current_user.email}")

        repository = UserRepository()
        users = await repository.list_users(role=role, is_active=is_active)

        return [
            UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at.isoformat(),
                updated_at=user.updated_at.isoformat(),
            )
            for user in users
        ]

    except Exception as e:
        logger.error(f"Failed to list users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users",
        )


@router.get(
    "/admin/users/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user details",
    description="Get user details by ID (super admin only)",
    dependencies=[Depends(require_role("super_admin"))],
)
async def get_user(
    user_id: UUID,
    current_user: AuthUser = Depends(get_current_active_user),
) -> UserResponse:
    """
    Get user details by ID.

    Only super admins can view user details.

    Args:
        user_id: User UUID
        current_user: Current authenticated super admin

    Returns:
        User information

    Raises:
        HTTPException: If user not found
    """
    try:
        logger.info(f"Getting user {user_id} by {current_user.email}")

        repository = UserRepository()
        user = await repository.get_by_id(user_id)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user",
        )


@router.put(
    "/admin/users/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user",
    description="Update user details (super admin only)",
    dependencies=[Depends(require_role("super_admin"))],
)
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    current_user: AuthUser = Depends(get_current_active_user),
) -> UserResponse:
    """
    Update user details.

    Only super admins can update users. This does not update passwords;
    use the password change endpoints instead.

    Args:
        user_id: User UUID
        request: Update request
        current_user: Current authenticated super admin

    Returns:
        Updated user information

    Raises:
        HTTPException: If user not found or update fails
    """
    try:
        logger.info(f"Updating user {user_id} by {current_user.email}")

        repository = UserRepository()
        user = await repository.update_user(
            user_id=user_id,
            email=request.email,
            name=request.name,
            role=request.role,
            is_active=request.is_active,
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        logger.info(f"User updated successfully: {user.id}")

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user: {e}", exc_info=True)
        if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )


@router.delete(
    "/admin/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate user",
    description="Deactivate a user (soft delete, super admin only)",
    dependencies=[Depends(require_role("super_admin"))],
)
async def deactivate_user(
    user_id: UUID,
    current_user: AuthUser = Depends(get_current_active_user),
) -> None:
    """
    Deactivate a user (soft delete).

    Only super admins can deactivate users. This sets is_active to False
    rather than deleting the user record.

    Args:
        user_id: User UUID
        current_user: Current authenticated super admin

    Raises:
        HTTPException: If user not found
    """
    try:
        logger.info(f"Deactivating user {user_id} by {current_user.email}")

        repository = UserRepository()
        user = await repository.deactivate_user(user_id)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        logger.info(f"User deactivated successfully: {user.id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deactivate user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user",
        )


# ============================================================================
# User Self-Service Endpoints
# ============================================================================


@router.post(
    "/users/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Self-registration",
    description="Register a new user account (if enabled in config)",
)
async def register(request: RegisterRequest) -> UserResponse:
    """
    Self-registration for new users.

    This endpoint is only available if allow_self_registration is enabled
    in the configuration. Self-registered users always get the 'user' role.

    Args:
        request: Registration request

    Returns:
        Created user information

    Raises:
        HTTPException: If registration is disabled or fails
    """
    if not settings.allow_self_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration is disabled",
        )

    try:
        logger.info(f"Self-registration attempt for {request.email}")

        repository = UserRepository()
        user = await repository.create_user(
            email=request.email,
            password=request.password,
            name=request.name,
            role=UserRole.USER,  # Self-registered users are always regular users
            is_active=True,
        )

        logger.info(f"User registered successfully: {user.id}")

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to register user: {e}", exc_info=True)
        if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user",
        )


@router.put(
    "/users/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update own profile",
    description="Update your own profile information",
)
async def update_own_profile(
    request: UpdateOwnProfileRequest,
    current_user: AuthUser = Depends(get_current_active_user),
) -> UserResponse:
    """
    Update your own profile information.

    Users can update their own name and email. Role and is_active
    can only be changed by super admins.

    Args:
        request: Update request
        current_user: Current authenticated user

    Returns:
        Updated user information

    Raises:
        HTTPException: If update fails
    """
    try:
        logger.info(f"User {current_user.email} updating own profile")

        repository = UserRepository()
        user = await repository.update_user(
            user_id=UUID(current_user.id),
            email=request.email,
            name=request.name,
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        logger.info(f"Profile updated successfully: {user.id}")

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update profile: {e}", exc_info=True)
        if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )


@router.put(
    "/users/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change own password",
    description="Change your own password",
)
async def change_own_password(
    request: UpdateOwnPasswordRequest,
    current_user: AuthUser = Depends(get_current_active_user),
) -> None:
    """
    Change your own password.

    Users must provide their current password for verification.

    Args:
        request: Password change request
        current_user: Current authenticated user

    Raises:
        HTTPException: If current password is incorrect or update fails
    """
    try:
        logger.info(f"User {current_user.email} changing password")

        repository = UserRepository()

        # Verify current password
        user = await repository.authenticate(current_user.email, request.current_password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

        # Update password
        updated_user = await repository.update_password(
            user_id=UUID(current_user.id),
            new_password=request.new_password,
        )

        if updated_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        logger.info(f"Password changed successfully: {updated_user.id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change password: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )
