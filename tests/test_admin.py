"""Tests for WorkspaceAdmin Repository.

Uses PostgreSQL test container for proper integration testing.
"""
import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4

from sqlalchemy import text

from text2x.models.base import Base, DatabaseConfig, init_db, close_db, get_db
from text2x.models.workspace import Workspace
from text2x.models.admin import WorkspaceAdmin, AdminRole

from text2x.repositories.admin import WorkspaceAdminRepository

from tests.config import TEST_POSTGRES_CONFIG


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def setup_db():
    """Set up the test database."""
    config = DatabaseConfig(
        host=TEST_POSTGRES_CONFIG['host'],
        port=TEST_POSTGRES_CONFIG['port'],
        database=TEST_POSTGRES_CONFIG['database'],
        user=TEST_POSTGRES_CONFIG['username'],
        password=TEST_POSTGRES_CONFIG['password'],
        echo=False,
    )

    db = init_db(config)
    engine = db.engine

    async with engine.begin() as conn:
        # Drop all tables
        await conn.execute(text("DROP TABLE IF EXISTS workspace_admins CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS workspaces CASCADE"))
        await conn.run_sync(Base.metadata.create_all)

    yield db

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS workspace_admins CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS workspaces CASCADE"))

    await close_db()


@pytest_asyncio.fixture
async def admin_repo(setup_db):
    return WorkspaceAdminRepository()


@pytest_asyncio.fixture
async def sample_workspace(setup_db):
    """Create a sample workspace for testing."""
    db = get_db()
    async with db.session() as session:
        workspace = Workspace(
            id=uuid4(),
            name="Test Workspace",
            slug="test-workspace",
            description="Test workspace for admin tests",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(workspace)
        await session.flush()
        await session.refresh(workspace)
        return workspace


# ============================================================================
# WorkspaceAdmin Repository Tests
# ============================================================================

class TestWorkspaceAdminRepository:
    """Test WorkspaceAdminRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_admin(self, admin_repo, sample_workspace):
        """Test creating a workspace admin."""
        admin = await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="user-123",
            invited_by="admin-456",
            role=AdminRole.ADMIN,
        )

        assert admin is not None
        assert admin.workspace_id == sample_workspace.id
        assert admin.user_id == "user-123"
        assert admin.role == AdminRole.ADMIN
        assert admin.invited_by == "admin-456"
        assert admin.invited_at is not None
        assert admin.accepted_at is None
        assert admin.is_pending is True

    @pytest.mark.asyncio
    async def test_create_owner(self, admin_repo, sample_workspace):
        """Test creating a workspace owner."""
        owner = await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="owner-123",
            invited_by="system",
            role=AdminRole.OWNER,
            accepted_at=datetime.utcnow(),
        )

        assert owner is not None
        assert owner.role == AdminRole.OWNER
        assert owner.is_pending is False
        assert owner.can_manage_admins() is True
        assert owner.can_manage_workspace() is True

    @pytest.mark.asyncio
    async def test_create_member(self, admin_repo, sample_workspace):
        """Test creating a workspace member with default role."""
        member = await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="member-123",
            invited_by="admin-456",
        )

        assert member is not None
        assert member.role == AdminRole.MEMBER
        assert member.can_manage_admins() is False
        assert member.can_manage_workspace() is False

    @pytest.mark.asyncio
    async def test_get_by_id(self, admin_repo, sample_workspace):
        """Test getting admin by ID."""
        created = await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="user-123",
            invited_by="admin-456",
            role=AdminRole.ADMIN,
        )

        fetched = await admin_repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.user_id == "user-123"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, admin_repo):
        """Test getting non-existent admin."""
        result = await admin_repo.get_by_id(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_workspace_and_user(self, admin_repo, sample_workspace):
        """Test getting admin by workspace and user."""
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="user-123",
            invited_by="admin-456",
            role=AdminRole.ADMIN,
        )

        fetched = await admin_repo.get_by_workspace_and_user(
            sample_workspace.id, "user-123"
        )
        assert fetched is not None
        assert fetched.user_id == "user-123"
        assert fetched.workspace_id == sample_workspace.id

    @pytest.mark.asyncio
    async def test_get_by_workspace_and_user_not_found(self, admin_repo, sample_workspace):
        """Test getting non-existent admin by workspace and user."""
        result = await admin_repo.get_by_workspace_and_user(
            sample_workspace.id, "nonexistent-user"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_workspace(self, admin_repo, sample_workspace):
        """Test listing admins by workspace."""
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="owner-1",
            invited_by="system",
            role=AdminRole.OWNER,
        )
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="admin-1",
            invited_by="owner-1",
            role=AdminRole.ADMIN,
        )
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="member-1",
            invited_by="admin-1",
            role=AdminRole.MEMBER,
        )

        results = await admin_repo.list_by_workspace(sample_workspace.id)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_list_by_workspace_with_role_filter(self, admin_repo, sample_workspace):
        """Test listing admins by workspace with role filter."""
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="owner-1",
            invited_by="system",
            role=AdminRole.OWNER,
        )
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="admin-1",
            invited_by="owner-1",
            role=AdminRole.ADMIN,
        )
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="admin-2",
            invited_by="owner-1",
            role=AdminRole.ADMIN,
        )

        admins = await admin_repo.list_by_workspace(
            sample_workspace.id, role=AdminRole.ADMIN
        )
        assert len(admins) == 2
        assert all(a.role == AdminRole.ADMIN for a in admins)

    @pytest.mark.asyncio
    async def test_list_by_workspace_pending_only(self, admin_repo, sample_workspace):
        """Test listing pending invitations for workspace."""
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="user-1",
            invited_by="admin",
            role=AdminRole.MEMBER,
        )
        accepted = await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="user-2",
            invited_by="admin",
            role=AdminRole.MEMBER,
        )
        await admin_repo.accept_invitation(accepted.id)

        pending = await admin_repo.list_by_workspace(
            sample_workspace.id, pending_only=True
        )
        assert len(pending) == 1
        assert pending[0].user_id == "user-1"

    @pytest.mark.asyncio
    async def test_list_by_user(self, admin_repo, sample_workspace):
        """Test listing workspaces for a user."""
        db = get_db()

        # Create second workspace in separate session
        async with db.session() as session:
            workspace2 = Workspace(
                id=uuid4(),
                name="Second Workspace",
                slug="second-workspace",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(workspace2)
            await session.flush()
            await session.refresh(workspace2)
            workspace2_id = workspace2.id

        # Now create admin records
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="user-123",
            invited_by="admin",
            role=AdminRole.ADMIN,
        )
        await admin_repo.create(
            workspace_id=workspace2_id,
            user_id="user-123",
            invited_by="admin",
            role=AdminRole.MEMBER,
        )

        results = await admin_repo.list_by_user("user-123")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_pending_for_user(self, admin_repo, sample_workspace):
        """Test listing pending invitations for a user."""
        # Create a pending invitation in first workspace
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="user-123",
            invited_by="admin",
            role=AdminRole.MEMBER,
        )

        # Create second workspace in separate session
        db = get_db()
        async with db.session() as session:
            workspace2 = Workspace(
                id=uuid4(),
                name="Second Workspace",
                slug="second-workspace",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(workspace2)
            await session.flush()
            await session.refresh(workspace2)
            workspace2_id = workspace2.id

        # Create another pending invitation in second workspace
        await admin_repo.create(
            workspace_id=workspace2_id,
            user_id="user-123",
            invited_by="admin",
            role=AdminRole.MEMBER,
        )

        pending = await admin_repo.list_pending_for_user("user-123")
        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_accept_invitation(self, admin_repo, sample_workspace):
        """Test accepting a workspace invitation."""
        admin = await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="user-123",
            invited_by="admin-456",
            role=AdminRole.MEMBER,
        )

        assert admin.is_pending is True

        updated = await admin_repo.accept_invitation(admin.id)
        assert updated is not None
        assert updated.is_pending is False
        assert updated.is_accepted is True
        assert updated.accepted_at is not None

    @pytest.mark.asyncio
    async def test_accept_invitation_not_found(self, admin_repo):
        """Test accepting non-existent invitation."""
        result = await admin_repo.accept_invitation(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_update_role(self, admin_repo, sample_workspace):
        """Test updating admin role."""
        admin = await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="user-123",
            invited_by="admin-456",
            role=AdminRole.MEMBER,
        )

        updated = await admin_repo.update_role(admin.id, AdminRole.ADMIN)
        assert updated is not None
        assert updated.role == AdminRole.ADMIN
        assert updated.can_manage_workspace() is True

    @pytest.mark.asyncio
    async def test_update_role_not_found(self, admin_repo):
        """Test updating role of non-existent admin."""
        result = await admin_repo.update_role(uuid4(), AdminRole.ADMIN)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, admin_repo, sample_workspace):
        """Test deleting an admin."""
        admin = await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="user-123",
            invited_by="admin-456",
            role=AdminRole.MEMBER,
        )

        result = await admin_repo.delete(admin.id)
        assert result is True

        fetched = await admin_repo.get_by_id(admin.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, admin_repo):
        """Test deleting non-existent admin."""
        result = await admin_repo.delete(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_by_workspace_and_user(self, admin_repo, sample_workspace):
        """Test deleting admin by workspace and user."""
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="user-123",
            invited_by="admin-456",
            role=AdminRole.MEMBER,
        )

        result = await admin_repo.delete_by_workspace_and_user(
            sample_workspace.id, "user-123"
        )
        assert result is True

        fetched = await admin_repo.get_by_workspace_and_user(
            sample_workspace.id, "user-123"
        )
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_by_workspace_and_user_not_found(self, admin_repo, sample_workspace):
        """Test deleting non-existent admin by workspace and user."""
        result = await admin_repo.delete_by_workspace_and_user(
            sample_workspace.id, "nonexistent-user"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_count_by_workspace(self, admin_repo, sample_workspace):
        """Test counting admins in workspace."""
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="owner-1",
            invited_by="system",
            role=AdminRole.OWNER,
        )
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="admin-1",
            invited_by="owner-1",
            role=AdminRole.ADMIN,
        )
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="member-1",
            invited_by="admin-1",
            role=AdminRole.MEMBER,
        )

        count = await admin_repo.count_by_workspace(sample_workspace.id)
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_by_workspace_with_role_filter(self, admin_repo, sample_workspace):
        """Test counting admins by role."""
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="owner-1",
            invited_by="system",
            role=AdminRole.OWNER,
        )
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="admin-1",
            invited_by="owner-1",
            role=AdminRole.ADMIN,
        )
        await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="admin-2",
            invited_by="owner-1",
            role=AdminRole.ADMIN,
        )

        owner_count = await admin_repo.count_by_workspace(
            sample_workspace.id, role=AdminRole.OWNER
        )
        assert owner_count == 1

        admin_count = await admin_repo.count_by_workspace(
            sample_workspace.id, role=AdminRole.ADMIN
        )
        assert admin_count == 2

    @pytest.mark.asyncio
    async def test_admin_to_dict(self, admin_repo, sample_workspace):
        """Test admin to_dict method."""
        admin = await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="user-123",
            invited_by="admin-456",
            role=AdminRole.ADMIN,
        )

        admin_dict = admin.to_dict()
        assert admin_dict["user_id"] == "user-123"
        assert admin_dict["role"] == "admin"
        assert admin_dict["invited_by"] == "admin-456"
        assert admin_dict["is_pending"] is True
        assert admin_dict["accepted_at"] is None

    @pytest.mark.asyncio
    async def test_cascade_delete_on_workspace_deletion(self, admin_repo, sample_workspace):
        """Test that admins are deleted when workspace is deleted."""
        admin = await admin_repo.create(
            workspace_id=sample_workspace.id,
            user_id="user-123",
            invited_by="admin-456",
            role=AdminRole.MEMBER,
        )

        # Delete the workspace
        db = get_db()
        async with db.session() as session:
            workspace = await session.get(Workspace, sample_workspace.id)
            await session.delete(workspace)

        # Verify admin was cascade deleted
        fetched = await admin_repo.get_by_id(admin.id)
        assert fetched is None
