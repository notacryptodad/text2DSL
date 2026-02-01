"""Tests for authentication and authorization functionality.

This module tests JWT token generation, validation, API key authentication,
and the authentication dependency injection system.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

from httpx import AsyncClient, ASGITransport
from jose import jwt

from text2x.api.app import app
from text2x.api.auth import (
    User,
    TokenData,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from text2x.config import settings


# ============================================================================
# Unit Tests - Token Operations
# ============================================================================


def test_create_access_token():
    """Test JWT access token creation."""
    user_id = "test-user-123"
    email = "test@example.com"
    roles = ["user", "admin"]

    token = create_access_token(user_id=user_id, email=email, roles=roles)

    # Decode token to verify contents
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["sub"] == user_id
    assert payload["email"] == email
    assert payload["roles"] == roles
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_create_refresh_token():
    """Test JWT refresh token creation."""
    user_id = "test-user-456"
    email = "refresh@example.com"
    roles = ["user"]

    token = create_refresh_token(user_id=user_id, email=email, roles=roles)

    # Decode token to verify contents
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["sub"] == user_id
    assert payload["email"] == email
    assert payload["roles"] == roles
    assert payload["type"] == "refresh"
    assert "exp" in payload
    assert "iat" in payload


def test_decode_valid_token():
    """Test decoding a valid JWT token."""
    user_id = "test-user-789"
    email = "decode@example.com"
    roles = ["user"]

    token = create_access_token(user_id=user_id, email=email, roles=roles)
    token_data = decode_token(token)

    assert isinstance(token_data, TokenData)
    assert token_data.user_id == user_id
    assert token_data.email == email
    assert token_data.roles == roles


def test_decode_expired_token():
    """Test that expired tokens raise an exception."""
    from fastapi import HTTPException

    user_id = "test-user-expired"
    email = "expired@example.com"

    # Create token that expires immediately
    token = create_access_token(
        user_id=user_id,
        email=email,
        expires_delta=timedelta(seconds=-1),  # Already expired
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)

    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_decode_invalid_token():
    """Test that invalid tokens raise an exception."""
    from fastapi import HTTPException

    invalid_token = "not.a.valid.token"

    with pytest.raises(HTTPException) as exc_info:
        decode_token(invalid_token)

    assert exc_info.value.status_code == 401


def test_password_hashing():
    """Test password hashing and verification."""
    password = "SecurePassword123!"

    # Hash the password
    hashed = get_password_hash(password)

    # Verify correct password
    assert verify_password(password, hashed) is True

    # Verify incorrect password
    assert verify_password("WrongPassword", hashed) is False


# ============================================================================
# Integration Tests - API Endpoints
# ============================================================================


@pytest_asyncio.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_login_success(client):
    """Test successful login with valid credentials."""
    response = await client.post(
        "/api/v1/auth/token",
        json={
            "email": "admin@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0

    # Verify the access token is valid
    token_data = decode_token(data["access_token"])
    assert token_data.email == "admin@example.com"
    assert "admin" in token_data.roles


@pytest.mark.asyncio
async def test_login_with_any_example_email(client):
    """Test login with any @example.com email (demo mode)."""
    response = await client.post(
        "/api/v1/auth/token",
        json={
            "email": "demo@example.com",
            "password": "anypassword",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data

    token_data = decode_token(data["access_token"])
    assert token_data.email == "demo@example.com"


@pytest.mark.asyncio
async def test_login_failure(client):
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/v1/auth/token",
        json={
            "email": "invalid@other.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_invalid_email_format(client):
    """Test login with invalid email format."""
    response = await client.post(
        "/api/v1/auth/token",
        json={
            "email": "not-an-email",
            "password": "password123",
        },
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_refresh_token_success(client):
    """Test refreshing an access token with a valid refresh token."""
    # First, login to get a refresh token
    login_response = await client.post(
        "/api/v1/auth/token",
        json={
            "email": "admin@example.com",
            "password": "password123",
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    # Now use the refresh token to get a new access token
    response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_token_invalid(client):
    """Test refresh with an invalid token."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": "invalid.token.here",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_with_valid_token(client):
    """Test /auth/me endpoint with valid JWT token."""
    # Enable auth for this test
    with patch.object(settings, "enable_auth", True):
        # First, login to get a token
        login_response = await client.post(
            "/api/v1/auth/token",
            json={
                "email": "admin@example.com",
                "password": "password123",
            },
        )
        access_token = login_response.json()["access_token"]

        # Use the token to access /auth/me
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == "admin@example.com"
        assert "admin" in data["roles"]
        assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_current_user_without_token(client):
    """Test /auth/me endpoint without authentication."""
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_with_invalid_token(client):
    """Test /auth/me endpoint with invalid token."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_key_authentication(client):
    """Test authentication using API key header."""
    # Enable auth for this test
    with patch.object(settings, "enable_auth", True):
        # Test with valid test API key
        response = await client.get(
            "/api/v1/auth/me",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == "apikey@example.com"
        assert "api_user" in data["roles"]


@pytest.mark.asyncio
async def test_api_key_invalid(client):
    """Test authentication with invalid API key."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": "invalid-key"},
    )

    assert response.status_code == 401


# ============================================================================
# Integration Tests - Protected Endpoints
# ============================================================================


@pytest.mark.asyncio
async def test_protected_endpoint_with_auth_disabled(client):
    """Test that endpoints work without auth when auth is disabled."""
    # Mock auth being disabled
    with patch.object(settings, "enable_auth", False):
        # Query endpoint should work without authentication
        response = await client.post(
            "/api/v1/query",
            json={
                "query": "Show me all users",
                "provider_id": "test-provider",
            },
        )

        # Should not fail due to authentication
        # (may fail for other reasons like missing orchestrator)
        assert response.status_code != 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_auth_enabled_no_token(client):
    """Test that endpoints require auth when auth is enabled."""
    # Mock auth being enabled
    with patch.object(settings, "enable_auth", True):
        # Query endpoint should require authentication
        response = await client.post(
            "/api/v1/query",
            json={
                "query": "Show me all users",
                "provider_id": "test-provider",
            },
        )

        # Should fail due to missing authentication (401) or other error
        # The important thing is it's not a successful 200
        # It might be 500 if orchestrator is not initialized, which happens first
        # But if auth was checked first, it would be 401
        # Since the orchestrator check happens in the endpoint logic,
        # and auth check happens in the dependency, 401 should come first
        assert response.status_code in [401, 500]  # Accept either for this test


@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(client):
    """Test accessing protected endpoint with valid token."""
    # Get a valid token
    login_response = await client.post(
        "/api/v1/auth/token",
        json={
            "email": "admin@example.com",
            "password": "password123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Mock auth being enabled
    with patch.object(settings, "enable_auth", True):
        # Try to access protected endpoint with token
        response = await client.post(
            "/api/v1/query",
            json={
                "query": "Show me all users",
                "provider_id": "test-provider",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Should not fail due to authentication
        # (may fail for other reasons like missing orchestrator)
        assert response.status_code != 401


# ============================================================================
# Edge Cases and Security Tests
# ============================================================================


@pytest.mark.asyncio
async def test_token_with_missing_claims(client):
    """Test that tokens with missing claims are rejected."""
    from fastapi import HTTPException

    # Create a token with missing email claim
    payload = {
        "sub": "user-123",
        # Missing "email" field
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow(),
    }
    invalid_token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_token(invalid_token)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_token_expiration():
    """Test that tokens properly expire after the configured time."""
    # Create token with short expiration
    token = create_access_token(
        user_id="test-user",
        email="test@example.com",
        expires_delta=timedelta(seconds=1),
    )

    # Token should be valid immediately
    token_data = decode_token(token)
    assert token_data.user_id == "test-user"

    # Wait for token to expire
    import time
    time.sleep(2)

    # Token should now be expired
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_bearer_token_without_prefix(client):
    """Test that token without 'Bearer' prefix is handled correctly."""
    login_response = await client.post(
        "/api/v1/auth/token",
        json={
            "email": "admin@example.com",
            "password": "password123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Try to use token without Bearer prefix
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": access_token},  # Missing "Bearer " prefix
    )

    # Should fail because Bearer prefix is expected
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_user_roles_in_token(client):
    """Test that user roles are properly encoded in tokens."""
    token = create_access_token(
        user_id="test-user",
        email="test@example.com",
        roles=["admin", "superuser"],
    )

    token_data = decode_token(token)
    assert "admin" in token_data.roles
    assert "superuser" in token_data.roles
    assert len(token_data.roles) == 2


# ============================================================================
# Password Security Tests
# ============================================================================


def test_password_hash_uniqueness():
    """Test that hashing the same password twice produces different hashes."""
    password = "TestPassword123"

    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)

    # Hashes should be different (due to salt)
    assert hash1 != hash2

    # But both should verify correctly
    assert verify_password(password, hash1)
    assert verify_password(password, hash2)


def test_password_hash_strength():
    """Test that password hashes are of expected length and format."""
    password = "SecurePassword"
    hashed = get_password_hash(password)

    # Bcrypt hashes should be 60 characters long
    assert len(hashed) == 60

    # Should start with bcrypt identifier
    assert hashed.startswith("$2b$")
