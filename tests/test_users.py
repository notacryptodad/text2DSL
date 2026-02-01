"""Tests for user management functionality.

This module tests user CRUD operations, authentication with database users,
and all user management API endpoints.
"""
import pytest
import pytest_asyncio
from uuid import uuid4

from httpx import AsyncClient, ASGITransport

from text2x.api.app import app
from text2x.api.auth import create_access_token, get_password_hash, verify_password
from text2x.config import settings
from text2x.models.base import init_db, get_db, Base
from text2x.models.user import User, UserRole
from text2x.repositories.user import UserRepository


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_env():
    """Setup test environment."""
    # Enable auth for user management tests
    original_enable_auth = settings.enable_auth
    settings.enable_auth = True

    yield

    # Restore original setting
    settings.enable_auth = original_enable_auth


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a test database session."""
    # Initialize database
    db = init_db()

    # Create all tables
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield db

    # Drop all tables
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await db.close()


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user in the database."""
    repository = UserRepository()
    user = await repository.create_user(
        email="testuser@example.com",
        password="testpassword123",
        name="Test User",
        role=UserRole.USER,
        is_active=True,
    )
    return user


@pytest_asyncio.fixture
async def test_admin(db_session):
    """Create a test admin user in the database."""
    repository = UserRepository()
    admin = await repository.create_user(
        email="admin@example.com",
        password="adminpassword123",
        name="Admin User",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    return admin


@pytest_asyncio.fixture
async def test_inactive_user(db_session):
    """Create an inactive test user in the database."""
    repository = UserRepository()
    user = await repository.create_user(
        email="inactive@example.com",
        password="password123",
        name="Inactive User",
        role=UserRole.USER,
        is_active=False,
    )
    return user


@pytest_asyncio.fixture
async def user_token(test_user):
    """Create an access token for the test user."""
    user_role = test_user.role.value if hasattr(test_user.role, 'value') else test_user.role
    return create_access_token(
        user_id=str(test_user.id),
        email=test_user.email,
        roles=[user_role],
    )


@pytest_asyncio.fixture
async def admin_token(test_admin):
    """Create an access token for the test admin."""
    admin_role = test_admin.role.value if hasattr(test_admin.role, 'value') else test_admin.role
    return create_access_token(
        user_id=str(test_admin.id),
        email=test_admin.email,
        roles=[admin_role],
    )


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ============================================================================
# Unit Tests - UserRepository
# ============================================================================


@pytest.mark.asyncio
async def test_create_user(db_session):
    """Test creating a user in the database."""
    repository = UserRepository()

    user = await repository.create_user(
        email="newuser@example.com",
        password="securepassword123",
        name="New User",
        role=UserRole.USER,
    )

    assert user.id is not None
    assert user.email == "newuser@example.com"
    assert user.name == "New User"
    assert user.role == UserRole.USER
    assert user.is_active is True
    assert user.hashed_password != "securepassword123"
    assert verify_password("securepassword123", user.hashed_password)
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_create_user_duplicate_email(db_session, test_user):
    """Test that creating a user with duplicate email fails."""
    repository = UserRepository()

    with pytest.raises(Exception):  # IntegrityError
        await repository.create_user(
            email=test_user.email,
            password="password123",
            name="Duplicate User",
        )


@pytest.mark.asyncio
async def test_get_user_by_id(db_session, test_user):
    """Test retrieving a user by ID."""
    repository = UserRepository()

    user = await repository.get_by_id(test_user.id)

    assert user is not None
    assert user.id == test_user.id
    assert user.email == test_user.email
    assert user.name == test_user.name


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(db_session):
    """Test retrieving a non-existent user returns None."""
    repository = UserRepository()

    user = await repository.get_by_id(uuid4())

    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_email(db_session, test_user):
    """Test retrieving a user by email."""
    repository = UserRepository()

    user = await repository.get_by_email(test_user.email)

    assert user is not None
    assert user.id == test_user.id
    assert user.email == test_user.email


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(db_session):
    """Test retrieving a non-existent user by email returns None."""
    repository = UserRepository()

    user = await repository.get_by_email("nonexistent@example.com")

    assert user is None


@pytest.mark.asyncio
async def test_list_users(db_session, test_user, test_admin):
    """Test listing all users."""
    repository = UserRepository()

    users = await repository.list_users()

    assert len(users) >= 2
    emails = [user.email for user in users]
    assert test_user.email in emails
    assert test_admin.email in emails


@pytest.mark.asyncio
async def test_list_users_filter_by_role(db_session, test_user, test_admin):
    """Test listing users filtered by role."""
    repository = UserRepository()

    # Filter by USER role
    users = await repository.list_users(role=UserRole.USER)
    assert all(user.role == UserRole.USER for user in users)
    assert any(user.id == test_user.id for user in users)

    # Filter by SUPER_ADMIN role
    admins = await repository.list_users(role=UserRole.SUPER_ADMIN)
    assert all(user.role == UserRole.SUPER_ADMIN for user in admins)
    assert any(user.id == test_admin.id for user in admins)


@pytest.mark.asyncio
async def test_list_users_filter_by_active(db_session, test_user, test_inactive_user):
    """Test listing users filtered by active status."""
    repository = UserRepository()

    # Filter active users
    active_users = await repository.list_users(is_active=True)
    assert all(user.is_active for user in active_users)
    assert any(user.id == test_user.id for user in active_users)

    # Filter inactive users
    inactive_users = await repository.list_users(is_active=False)
    assert all(not user.is_active for user in inactive_users)
    assert any(user.id == test_inactive_user.id for user in inactive_users)


@pytest.mark.asyncio
async def test_update_user(db_session, test_user):
    """Test updating a user."""
    repository = UserRepository()

    updated_user = await repository.update_user(
        user_id=test_user.id,
        name="Updated Name",
        role=UserRole.SUPER_ADMIN,
    )

    assert updated_user is not None
    assert updated_user.id == test_user.id
    assert updated_user.name == "Updated Name"
    assert updated_user.role == UserRole.SUPER_ADMIN
    assert updated_user.email == test_user.email  # Unchanged


@pytest.mark.asyncio
async def test_update_user_not_found(db_session):
    """Test updating a non-existent user returns None."""
    repository = UserRepository()

    updated_user = await repository.update_user(
        user_id=uuid4(),
        name="New Name",
    )

    assert updated_user is None


@pytest.mark.asyncio
async def test_update_password(db_session, test_user):
    """Test updating a user's password."""
    repository = UserRepository()
    new_password = "newsecurepassword123"

    updated_user = await repository.update_password(
        user_id=test_user.id,
        new_password=new_password,
    )

    assert updated_user is not None
    assert verify_password(new_password, updated_user.hashed_password)
    # Old password should not work
    assert not verify_password("testpassword123", updated_user.hashed_password)


@pytest.mark.asyncio
async def test_deactivate_user(db_session, test_user):
    """Test deactivating a user."""
    repository = UserRepository()

    deactivated_user = await repository.deactivate_user(test_user.id)

    assert deactivated_user is not None
    assert deactivated_user.id == test_user.id
    assert not deactivated_user.is_active


@pytest.mark.asyncio
async def test_delete_user(db_session, test_user):
    """Test deleting a user."""
    repository = UserRepository()

    # Delete user
    result = await repository.delete_user(test_user.id)
    assert result is True

    # Verify user is deleted
    user = await repository.get_by_id(test_user.id)
    assert user is None


@pytest.mark.asyncio
async def test_delete_user_not_found(db_session):
    """Test deleting a non-existent user returns False."""
    repository = UserRepository()

    result = await repository.delete_user(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_authenticate_success(db_session, test_user):
    """Test successful authentication."""
    repository = UserRepository()

    user = await repository.authenticate(
        email=test_user.email,
        password="testpassword123",
    )

    assert user is not None
    assert user.id == test_user.id
    assert user.email == test_user.email


@pytest.mark.asyncio
async def test_authenticate_wrong_password(db_session, test_user):
    """Test authentication with wrong password."""
    repository = UserRepository()

    user = await repository.authenticate(
        email=test_user.email,
        password="wrongpassword",
    )

    assert user is None


@pytest.mark.asyncio
async def test_authenticate_nonexistent_user(db_session):
    """Test authentication with non-existent user."""
    repository = UserRepository()

    user = await repository.authenticate(
        email="nonexistent@example.com",
        password="password123",
    )

    assert user is None


@pytest.mark.asyncio
async def test_authenticate_inactive_user(db_session, test_inactive_user):
    """Test authentication with inactive user."""
    repository = UserRepository()

    user = await repository.authenticate(
        email=test_inactive_user.email,
        password="password123",
    )

    assert user is None


# ============================================================================
# Integration Tests - Authentication with Database
# ============================================================================


@pytest.mark.asyncio
async def test_login_with_database_user(client, db_session, test_user):
    """Test login endpoint with database user."""
    response = await client.post(
        f"{settings.api_prefix}/auth/token",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_with_wrong_password(client, db_session, test_user):
    """Test login with wrong password."""
    response = await client.post(
        f"{settings.api_prefix}/auth/token",
        json={
            "email": test_user.email,
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_with_nonexistent_user(client, db_session):
    """Test login with non-existent user."""
    response = await client.post(
        f"{settings.api_prefix}/auth/token",
        json={
            "email": "nonexistent@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_with_inactive_user(client, db_session, test_inactive_user):
    """Test login with inactive user."""
    response = await client.post(
        f"{settings.api_prefix}/auth/token",
        json={
            "email": test_inactive_user.email,
            "password": "password123",
        },
    )

    assert response.status_code == 401


# ============================================================================
# Integration Tests - Admin User Management Endpoints
# ============================================================================


@pytest.mark.asyncio
async def test_create_user_endpoint(client, db_session, admin_token):
    """Test creating a user via API."""
    response = await client.post(
        f"{settings.api_prefix}/admin/users",
        json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "name": "New User",
            "role": "user",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["name"] == "New User"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_create_user_endpoint_unauthorized(client, db_session, user_token):
    """Test creating a user without super admin permission."""
    response = await client.post(
        f"{settings.api_prefix}/admin/users",
        json={
            "email": "newuser@example.com",
            "password": "password123",
            "name": "New User",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_user_endpoint_duplicate_email(client, db_session, admin_token, test_user):
    """Test creating a user with duplicate email."""
    response = await client.post(
        f"{settings.api_prefix}/admin/users",
        json={
            "email": test_user.email,
            "password": "password123",
            "name": "Duplicate User",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_users_endpoint(client, db_session, admin_token, test_user):
    """Test listing users via API."""
    response = await client.get(
        f"{settings.api_prefix}/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    emails = [user["email"] for user in data]
    assert test_user.email in emails


@pytest.mark.asyncio
async def test_list_users_endpoint_unauthorized(client, db_session, user_token):
    """Test listing users without super admin permission."""
    response = await client.get(
        f"{settings.api_prefix}/admin/users",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_user_endpoint(client, db_session, admin_token, test_user):
    """Test getting a user by ID via API."""
    response = await client.get(
        f"{settings.api_prefix}/admin/users/{test_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email
    assert data["name"] == test_user.name


@pytest.mark.asyncio
async def test_get_user_endpoint_not_found(client, db_session, admin_token):
    """Test getting a non-existent user."""
    response = await client.get(
        f"{settings.api_prefix}/admin/users/{uuid4()}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_user_endpoint(client, db_session, admin_token, test_user):
    """Test updating a user via API."""
    response = await client.put(
        f"{settings.api_prefix}/admin/users/{test_user.id}",
        json={
            "name": "Updated Name",
            "role": "super_admin",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["name"] == "Updated Name"
    assert data["role"] == "super_admin"


@pytest.mark.asyncio
async def test_update_user_endpoint_not_found(client, db_session, admin_token):
    """Test updating a non-existent user."""
    response = await client.put(
        f"{settings.api_prefix}/admin/users/{uuid4()}",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deactivate_user_endpoint(client, db_session, admin_token, test_user):
    """Test deactivating a user via API."""
    response = await client.delete(
        f"{settings.api_prefix}/admin/users/{test_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 204

    # Verify user is deactivated
    repository = UserRepository()
    user = await repository.get_by_id(test_user.id)
    assert user is not None
    assert not user.is_active


# ============================================================================
# Integration Tests - User Self-Service Endpoints
# ============================================================================


@pytest.mark.asyncio
async def test_register_endpoint_disabled(client, db_session):
    """Test self-registration when disabled."""
    # Ensure registration is disabled
    original_value = settings.allow_self_registration
    settings.allow_self_registration = False

    try:
        response = await client.post(
            f"{settings.api_prefix}/users/register",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "name": "New User",
            },
        )

        assert response.status_code == 403
    finally:
        settings.allow_self_registration = original_value


@pytest.mark.asyncio
async def test_register_endpoint_enabled(client, db_session):
    """Test self-registration when enabled."""
    # Enable registration
    original_value = settings.allow_self_registration
    settings.allow_self_registration = True

    try:
        response = await client.post(
            f"{settings.api_prefix}/users/register",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert data["role"] == "user"  # Self-registered users are always regular users
    finally:
        settings.allow_self_registration = original_value


@pytest.mark.asyncio
async def test_update_own_profile(client, db_session, user_token, test_user):
    """Test updating own profile."""
    response = await client.put(
        f"{settings.api_prefix}/users/me",
        json={"name": "Updated Name"},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_change_own_password(client, db_session, user_token, test_user):
    """Test changing own password."""
    response = await client.put(
        f"{settings.api_prefix}/users/me/password",
        json={
            "current_password": "testpassword123",
            "new_password": "newpassword123",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 204

    # Verify new password works
    login_response = await client.post(
        f"{settings.api_prefix}/auth/token",
        json={
            "email": test_user.email,
            "password": "newpassword123",
        },
    )
    assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_change_own_password_wrong_current(client, db_session, user_token):
    """Test changing password with wrong current password."""
    response = await client.put(
        f"{settings.api_prefix}/users/me/password",
        json={
            "current_password": "wrongpassword",
            "new_password": "newpassword123",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 401
