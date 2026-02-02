"""Authentication and authorization utilities for the API."""
import logging
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING
from uuid import UUID

import bcrypt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from text2x.config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name=settings.api_key_header, auto_error=False)


class User(BaseModel):
    """User model for authentication."""

    id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    name: str = Field(default="", description="User's full name")
    role: str = Field(default="user", description="User role")
    roles: list[str] = Field(default_factory=list, description="User roles (deprecated)")
    is_active: bool = Field(default=True, description="Whether user is active")
    created_at: Optional[str] = Field(default=None, description="When user was created")
    updated_at: Optional[str] = Field(default=None, description="When user was last updated")


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # User ID
    email: str
    roles: list[str] = Field(default_factory=list)
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None
    type: str = "access"  # access or refresh


class TokenData(BaseModel):
    """Decoded token data."""

    user_id: str
    email: str
    roles: list[str] = Field(default_factory=list)


def create_access_token(
    user_id: str,
    email: str,
    roles: list[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a new JWT access token.

    Args:
        user_id: User identifier
        email: User email
        roles: User roles
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    if roles is None:
        roles = []

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)

    payload = TokenPayload(
        sub=user_id,
        email=email,
        roles=roles,
        exp=expire,
        iat=datetime.utcnow(),
        type="access",
    )

    encoded_jwt = jwt.encode(
        payload.model_dump(),
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def create_refresh_token(
    user_id: str,
    email: str,
    roles: list[str] = None,
) -> str:
    """
    Create a new JWT refresh token.

    Args:
        user_id: User identifier
        email: User email
        roles: User roles

    Returns:
        Encoded JWT refresh token string
    """
    if roles is None:
        roles = []

    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_expire_days)

    payload = TokenPayload(
        sub=user_id,
        email=email,
        roles=roles,
        exp=expire,
        iat=datetime.utcnow(),
        type="refresh",
    )

    encoded_jwt = jwt.encode(
        payload.model_dump(),
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token data

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        roles: list[str] = payload.get("roles", [])

        if user_id is None or email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenData(user_id=user_id, email=email, roles=roles)

    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches
    """
    # Convert strings to bytes for bcrypt
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')

    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """
    Hash a password.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    # Convert password to bytes and generate salt
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Return as string
    return hashed.decode('utf-8')


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Optional[User]:
    """
    Extract and validate user from JWT token.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        User object if token is valid, None if no token provided

    Raises:
        HTTPException: If token is invalid
    """
    if not credentials:
        return None

    token = credentials.credentials
    token_data = decode_token(token)

    # Try to fetch user from database to verify it exists and is active
    try:
        from uuid import UUID
        from text2x.repositories.user import UserRepository

        repository = UserRepository()
        db_user = await repository.get_by_id(UUID(token_data.user_id))

        if db_user:
            # Use database user information
            if not db_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive",
                )

            user = User(
                id=str(db_user.id),
                email=db_user.email,
                name=db_user.name,
                role=db_user.role.value if hasattr(db_user.role, 'value') else str(db_user.role),
                roles=[db_user.role.value if hasattr(db_user.role, 'value') else str(db_user.role)],
                is_active=db_user.is_active,
                created_at=db_user.created_at.isoformat() if hasattr(db_user.created_at, 'isoformat') else str(db_user.created_at),
                updated_at=db_user.updated_at.isoformat() if hasattr(db_user.updated_at, 'isoformat') else str(db_user.updated_at),
            )
            return user
    except Exception as e:
        # If database lookup fails, fall back to token data
        # This allows the system to work even if DB is temporarily unavailable
        logger.debug(f"Database user lookup failed, using token data: {e}")

    # Fall back to token data (backward compatibility)
    user = User(
        id=token_data.user_id,
        email=token_data.email,
        roles=token_data.roles,
    )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_current_user_from_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> Optional[User]:
    """
    Validate API key and return associated user.

    Args:
        api_key: API key from header

    Returns:
        User object if API key is valid, None if no key provided

    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key:
        return None

    # In a real application, you would look up the API key in the database
    # For now, we'll just validate against a simple check
    # This is just a placeholder - implement proper API key validation
    # by storing hashed API keys in the database

    # Example: Check if API key matches a test key (for development)
    if api_key == "test-api-key":
        return User(
            id="api-key-user",
            email="apikey@example.com",
            roles=["api_user"],
        )

    logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


async def get_current_user(
    user_from_token: Optional[User] = Depends(get_current_user_from_token),
    user_from_api_key: Optional[User] = Depends(get_current_user_from_api_key),
) -> Optional[User]:
    """
    Get current authenticated user from either JWT token or API key.

    This dependency tries multiple authentication methods:
    1. JWT Bearer token
    2. API key header

    If authentication is disabled in config, returns None.
    If authentication is enabled but no valid credentials provided, raises 401.

    Args:
        user_from_token: User from JWT token
        user_from_api_key: User from API key

    Returns:
        Authenticated user or None if auth is disabled

    Raises:
        HTTPException: If auth is enabled but credentials are invalid
    """
    # If authentication is disabled, return None (no user required)
    if not settings.enable_auth:
        return None

    # Try JWT token first
    if user_from_token:
        logger.debug(f"Authenticated user via JWT: {user_from_token.email}")
        return user_from_token

    # Try API key second
    if user_from_api_key:
        logger.debug(f"Authenticated user via API key: {user_from_api_key.email}")
        return user_from_api_key

    # If auth is enabled but no valid credentials provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a valid JWT token or API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (requires authentication).

    This dependency enforces authentication even when it's optional elsewhere.
    Use this for endpoints that always require authentication.

    Args:
        current_user: Current user from get_current_user

    Returns:
        Authenticated active user

    Raises:
        HTTPException: If user is not authenticated or not active
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return current_user


def require_role(required_role: str):
    """
    Create a dependency that requires a specific role.

    Args:
        required_role: Role that is required

    Returns:
        Dependency function that checks for the role
    """

    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if required_role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required role: {required_role}",
            )
        return current_user

    return role_checker


def require_expert():
    """
    Create a dependency that requires expert role (system or workspace level).
    
    Allows:
    - System-wide SUPER_ADMIN
    - System-wide EXPERT
    - Workspace EXPERT (checked per-request based on workspace_id)
    
    Returns:
        Dependency function that checks for expert permissions
    """

    async def expert_checker(current_user: User = Depends(get_current_active_user)) -> User:
        # System-wide experts can review anything
        if "super_admin" in current_user.roles or "expert" in current_user.roles:
            return current_user
        
        # For workspace-level experts, we need workspace_id in the request
        # This basic check allows any authenticated user through,
        # and workspace-level checks happen in the endpoint itself
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Expert role required to access review features",
        )

    return expert_checker


async def check_workspace_expert(
    user: User,
    workspace_id: UUID,
    session: "AsyncSession",
) -> bool:
    """
    Check if user has expert permissions for a specific workspace.
    
    Args:
        user: Current user
        workspace_id: Workspace to check
        session: Database session
        
    Returns:
        True if user is system expert or workspace expert
    """
    # System-wide experts
    if "super_admin" in user.roles or "expert" in user.roles:
        return True
    
    # Check workspace-level expert role
    from text2x.models.admin import WorkspaceAdmin, AdminRole
    from sqlalchemy import select
    
    result = await session.execute(
        select(WorkspaceAdmin).where(
            WorkspaceAdmin.workspace_id == workspace_id,
            WorkspaceAdmin.user_id == user.user_id,
            WorkspaceAdmin.role == AdminRole.EXPERT,
        )
    )
    return result.scalar_one_or_none() is not None
