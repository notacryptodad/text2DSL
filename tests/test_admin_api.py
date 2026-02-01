"""Integration tests for admin API endpoints.

Tests the admin API routes for workspace management, admin invitations,
and access control.
"""
import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from text2x.api.app import app
from text2x.models.base import Base, DatabaseConfig, init_db, close_db, get_db
from text2x.models.workspace import Workspace
from text2x.models.admin import WorkspaceAdmin, AdminRole

from tests.config import TEST_POSTGRES_CONFIG


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def setup_db():
    """Set up the test database."""
    config = DatabaseConfig(
        host=TEST_POSTGRES_CONFIG["host"],
        port=TEST_POSTGRES_CONFIG["port"],
        database=TEST_POSTGRES_CONFIG["database"],
        user=TEST_POSTGRES_CONFIG["username"],
        password=TEST_POSTGRES_CONFIG["password"],
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
async def client(setup_db):
    """Create test client."""
    return TestClient(app)


# ============================================================================
# Admin Workspace Management Tests
# ============================================================================


class TestAdminWorkspaceEndpoints:
    """Test admin workspace management endpoints."""

    @pytest.mark.asyncio
    async def test_create_workspace_with_owner(self, client):
        """Test creating a workspace with an owner (super admin endpoint)."""
        workspace_data = {
            "name": "Test Workspace",
            "slug": "test-workspace",
            "description": "A test workspace",
            "settings": {"feature_flags": {"advanced_mode": True}},
            "owner_user_id": "user-123",
        }

        response = client.post("/api/v1/admin/workspaces", json=workspace_data)

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Test Workspace"
        assert data["slug"] == "test-workspace"
        assert data["description"] == "A test workspace"
        assert data["admin_count"] == 1
        assert data["provider_count"] == 0
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_workspace_duplicate_slug(self, client):
        """Test creating a workspace with duplicate slug fails."""
        workspace_data = {
            "name": "Test Workspace",
            "slug": "test-workspace",
            "owner_user_id": "user-123",
        }

        # Create first workspace
        response1 = client.post("/admin/workspaces", json=workspace_data)
        assert response1.status_code == 201

        # Try to create duplicate
        workspace_data["name"] = "Different Name"
        response2 = client.post("/admin/workspaces", json=workspace_data)

        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]["message"]

    @pytest.mark.asyncio
    async def test_list_all_workspaces(self, client):
        """Test listing all workspaces (super admin endpoint)."""
        # Create multiple workspaces
        for i in range(3):
            workspace_data = {
                "name": f"Workspace {i}",
                "slug": f"workspace-{i}",
                "owner_user_id": f"user-{i}",
            }
            response = client.post("/api/v1/admin/workspaces", json=workspace_data)
            assert response.status_code == 201

        # List all workspaces
        response = client.get("/api/v1/admin/workspaces")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 3
        assert all("id" in ws for ws in data)
        assert all("name" in ws for ws in data)
        assert all("admin_count" in ws for ws in data)

    @pytest.mark.asyncio
    async def test_list_workspaces_empty(self, client):
        """Test listing workspaces when none exist."""
        response = client.get("/api/v1/admin/workspaces")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 0


# ============================================================================
# Admin Invitation Tests
# ============================================================================


class TestAdminInvitationEndpoints:
    """Test admin invitation endpoints."""

    @pytest.mark.asyncio
    async def test_invite_admin_to_workspace(self, client):
        """Test inviting a user as admin to a workspace."""
        # Create workspace first
        workspace_data = {
            "name": "Test Workspace",
            "slug": "test-workspace",
            "owner_user_id": "owner-123",
        }
        ws_response = client.post("/api/v1/admin/workspaces", json=workspace_data)
        assert ws_response.status_code == 201
        workspace_id = ws_response.json()["id"]

        # Invite admin
        invite_data = {
            "user_id": "admin-456",
            "role": "admin",
            "invited_by": "owner-123",
        }
        response = client.post(
            f"/api/v1/admin/workspaces/{workspace_id}/admins", json=invite_data
        )

        assert response.status_code == 201
        data = response.json()

        assert data["user_id"] == "admin-456"
        assert data["role"] == "admin"
        assert data["invited_by"] == "owner-123"
        assert data["is_pending"] is True
        assert data["accepted_at"] is None
        assert "id" in data
        assert "workspace_id" in data

    @pytest.mark.asyncio
    async def test_invite_member_to_workspace(self, client):
        """Test inviting a user as member to a workspace."""
        # Create workspace first
        workspace_data = {
            "name": "Test Workspace",
            "slug": "test-workspace",
            "owner_user_id": "owner-123",
        }
        ws_response = client.post("/api/v1/admin/workspaces", json=workspace_data)
        assert ws_response.status_code == 201
        workspace_id = ws_response.json()["id"]

        # Invite member
        invite_data = {
            "user_id": "member-789",
            "role": "member",
            "invited_by": "owner-123",
        }
        response = client.post(
            f"/api/v1/admin/workspaces/{workspace_id}/admins", json=invite_data
        )

        assert response.status_code == 201
        data = response.json()

        assert data["user_id"] == "member-789"
        assert data["role"] == "member"
        assert data["is_pending"] is True

    @pytest.mark.asyncio
    async def test_invite_owner_fails(self, client):
        """Test that inviting as owner through invite endpoint fails."""
        # Create workspace first
        workspace_data = {
            "name": "Test Workspace",
            "slug": "test-workspace",
            "owner_user_id": "owner-123",
        }
        ws_response = client.post("/api/v1/admin/workspaces", json=workspace_data)
        assert ws_response.status_code == 201
        workspace_id = ws_response.json()["id"]

        # Try to invite as owner
        invite_data = {
            "user_id": "wannabe-owner",
            "role": "owner",
            "invited_by": "owner-123",
        }
        response = client.post(
            f"/api/v1/admin/workspaces/{workspace_id}/admins", json=invite_data
        )

        assert response.status_code == 400
        assert "Cannot invite users as OWNER" in response.json()["detail"]["message"]

    @pytest.mark.asyncio
    async def test_invite_duplicate_user_fails(self, client):
        """Test that inviting the same user twice fails."""
        # Create workspace
        workspace_data = {
            "name": "Test Workspace",
            "slug": "test-workspace",
            "owner_user_id": "owner-123",
        }
        ws_response = client.post("/api/v1/admin/workspaces", json=workspace_data)
        assert ws_response.status_code == 201
        workspace_id = ws_response.json()["id"]

        # First invitation
        invite_data = {
            "user_id": "admin-456",
            "role": "admin",
            "invited_by": "owner-123",
        }
        response1 = client.post(
            f"/admin/workspaces/{workspace_id}/admins", json=invite_data
        )
        assert response1.status_code == 201

        # Try to invite again
        response2 = client.post(
            f"/admin/workspaces/{workspace_id}/admins", json=invite_data
        )

        assert response2.status_code == 400
        assert "already has access" in response2.json()["detail"]["message"]

    @pytest.mark.asyncio
    async def test_invite_to_nonexistent_workspace(self, client):
        """Test inviting to a non-existent workspace fails."""
        fake_workspace_id = str(uuid4())

        invite_data = {
            "user_id": "admin-456",
            "role": "admin",
            "invited_by": "owner-123",
        }
        response = client.post(
            f"/api/v1/admin/workspaces/{fake_workspace_id}/admins", json=invite_data
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]["message"]


# ============================================================================
# Accept Invitation Tests
# ============================================================================


class TestAcceptInvitationEndpoints:
    """Test invitation acceptance endpoints."""

    @pytest.mark.asyncio
    async def test_accept_invitation(self, client):
        """Test accepting a pending invitation."""
        # Create workspace
        workspace_data = {
            "name": "Test Workspace",
            "slug": "test-workspace",
            "owner_user_id": "owner-123",
        }
        ws_response = client.post("/api/v1/admin/workspaces", json=workspace_data)
        assert ws_response.status_code == 201
        workspace_id = ws_response.json()["id"]

        # Create invitation
        invite_data = {
            "user_id": "admin-456",
            "role": "admin",
            "invited_by": "owner-123",
        }
        invite_response = client.post(
            f"/api/v1/admin/workspaces/{workspace_id}/admins", json=invite_data
        )
        assert invite_response.status_code == 201
        invitation_id = invite_response.json()["id"]

        # Accept invitation
        response = client.post(f"/api/v1/admin/invitations/{invitation_id}/accept")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "accepted successfully" in data["message"]
        assert data["admin"]["is_pending"] is False
        assert data["admin"]["accepted_at"] is not None

    @pytest.mark.asyncio
    async def test_accept_already_accepted_invitation(self, client):
        """Test accepting an already accepted invitation."""
        # Create workspace and invitation
        workspace_data = {
            "name": "Test Workspace",
            "slug": "test-workspace",
            "owner_user_id": "owner-123",
        }
        ws_response = client.post("/api/v1/admin/workspaces", json=workspace_data)
        assert ws_response.status_code == 201
        workspace_id = ws_response.json()["id"]

        invite_data = {
            "user_id": "admin-456",
            "role": "admin",
            "invited_by": "owner-123",
        }
        invite_response = client.post(
            f"/api/v1/admin/workspaces/{workspace_id}/admins", json=invite_data
        )
        invitation_id = invite_response.json()["id"]

        # Accept first time
        response1 = client.post(f"/admin/invitations/{invitation_id}/accept")
        assert response1.status_code == 200

        # Accept again
        response2 = client.post(f"/admin/invitations/{invitation_id}/accept")

        assert response2.status_code == 200
        data = response2.json()
        assert data["success"] is True
        assert "already accepted" in data["message"]

    @pytest.mark.asyncio
    async def test_accept_nonexistent_invitation(self, client):
        """Test accepting a non-existent invitation fails."""
        fake_invitation_id = str(uuid4())

        response = client.post(f"/api/v1/admin/invitations/{fake_invitation_id}/accept")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]["message"]


# ============================================================================
# Remove Admin Tests
# ============================================================================


class TestRemoveAdminEndpoints:
    """Test admin removal endpoints."""

    @pytest.mark.asyncio
    async def test_remove_admin_from_workspace(self, client):
        """Test removing an admin from a workspace."""
        # Create workspace
        workspace_data = {
            "name": "Test Workspace",
            "slug": "test-workspace",
            "owner_user_id": "owner-123",
        }
        ws_response = client.post("/api/v1/admin/workspaces", json=workspace_data)
        assert ws_response.status_code == 201
        workspace_id = ws_response.json()["id"]

        # Invite admin
        invite_data = {
            "user_id": "admin-456",
            "role": "admin",
            "invited_by": "owner-123",
        }
        invite_response = client.post(
            f"/api/v1/admin/workspaces/{workspace_id}/admins", json=invite_data
        )
        assert invite_response.status_code == 201

        # Remove admin
        response = client.delete(
            f"/api/v1/admin/workspaces/{workspace_id}/admins/admin-456"
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_remove_nonexistent_admin(self, client):
        """Test removing a non-existent admin fails."""
        # Create workspace
        workspace_data = {
            "name": "Test Workspace",
            "slug": "test-workspace",
            "owner_user_id": "owner-123",
        }
        ws_response = client.post("/api/v1/admin/workspaces", json=workspace_data)
        assert ws_response.status_code == 201
        workspace_id = ws_response.json()["id"]

        # Try to remove non-existent admin
        response = client.delete(
            f"/api/v1/admin/workspaces/{workspace_id}/admins/nonexistent-user"
        )

        assert response.status_code == 404
        assert "not a member" in response.json()["detail"]["message"]

    @pytest.mark.asyncio
    async def test_remove_last_owner_fails(self, client):
        """Test that removing the last owner from a workspace fails."""
        # Create workspace
        workspace_data = {
            "name": "Test Workspace",
            "slug": "test-workspace",
            "owner_user_id": "owner-123",
        }
        ws_response = client.post("/api/v1/admin/workspaces", json=workspace_data)
        assert ws_response.status_code == 201
        workspace_id = ws_response.json()["id"]

        # Try to remove the owner (which is the only owner)
        response = client.delete(
            f"/api/v1/admin/workspaces/{workspace_id}/admins/owner-123"
        )

        assert response.status_code == 400
        assert "Cannot remove the last owner" in response.json()["detail"]["message"]

    @pytest.mark.asyncio
    async def test_remove_from_nonexistent_workspace(self, client):
        """Test removing admin from non-existent workspace fails."""
        fake_workspace_id = str(uuid4())

        response = client.delete(
            f"/api/v1/admin/workspaces/{fake_workspace_id}/admins/admin-456"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]["message"]


# ============================================================================
# Integration Tests
# ============================================================================


class TestAdminWorkflowIntegration:
    """Test complete admin workflow scenarios."""

    @pytest.mark.asyncio
    async def test_complete_workspace_setup_workflow(self, client):
        """Test complete workflow: create workspace, invite admins, accept invitations."""
        # 1. Super admin creates workspace
        workspace_data = {
            "name": "Engineering Team",
            "slug": "engineering",
            "description": "Engineering team workspace",
            "owner_user_id": "alice",
        }
        ws_response = client.post("/api/v1/admin/workspaces", json=workspace_data)
        assert ws_response.status_code == 201
        workspace_id = ws_response.json()["id"]

        # 2. Owner invites admins
        bob_invite = {
            "user_id": "bob",
            "role": "admin",
            "invited_by": "alice",
        }
        bob_response = client.post(
            f"/api/v1/admin/workspaces/{workspace_id}/admins", json=bob_invite
        )
        assert bob_response.status_code == 201
        bob_invitation_id = bob_response.json()["id"]

        # 3. Owner invites members
        charlie_invite = {
            "user_id": "charlie",
            "role": "member",
            "invited_by": "alice",
        }
        charlie_response = client.post(
            f"/api/v1/admin/workspaces/{workspace_id}/admins", json=charlie_invite
        )
        assert charlie_response.status_code == 201
        charlie_invitation_id = charlie_response.json()["id"]

        # 4. Bob accepts invitation
        bob_accept = client.post(f"/api/v1/admin/invitations/{bob_invitation_id}/accept")
        assert bob_accept.status_code == 200
        assert bob_accept.json()["admin"]["is_pending"] is False

        # 5. Charlie accepts invitation
        charlie_accept = client.post(
            f"/api/v1/admin/invitations/{charlie_invitation_id}/accept"
        )
        assert charlie_accept.status_code == 200
        assert charlie_accept.json()["admin"]["is_pending"] is False

        # 6. List workspaces - should have 1 workspace with 3 admins
        list_response = client.get("/api/v1/admin/workspaces")
        assert list_response.status_code == 200
        workspaces = list_response.json()
        assert len(workspaces) == 1
        assert workspaces[0]["admin_count"] == 3

    @pytest.mark.asyncio
    async def test_multi_workspace_multi_admin_scenario(self, client):
        """Test scenario with multiple workspaces and shared admins."""
        # Create two workspaces
        ws1_data = {
            "name": "Workspace 1",
            "slug": "workspace-1",
            "owner_user_id": "alice",
        }
        ws1_response = client.post("/api/v1/admin/workspaces", json=ws1_data)
        assert ws1_response.status_code == 201
        ws1_id = ws1_response.json()["id"]

        ws2_data = {
            "name": "Workspace 2",
            "slug": "workspace-2",
            "owner_user_id": "bob",
        }
        ws2_response = client.post("/api/v1/admin/workspaces", json=ws2_data)
        assert ws2_response.status_code == 201
        ws2_id = ws2_response.json()["id"]

        # Add Charlie to both workspaces
        charlie_ws1 = {
            "user_id": "charlie",
            "role": "admin",
            "invited_by": "alice",
        }
        client.post(f"/api/v1/admin/workspaces/{ws1_id}/admins", json=charlie_ws1)

        charlie_ws2 = {
            "user_id": "charlie",
            "role": "member",
            "invited_by": "bob",
        }
        client.post(f"/api/v1/admin/workspaces/{ws2_id}/admins", json=charlie_ws2)

        # List all workspaces
        list_response = client.get("/api/v1/admin/workspaces")
        assert list_response.status_code == 200
        workspaces = list_response.json()
        assert len(workspaces) == 2
