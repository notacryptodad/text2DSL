"""Tests for Workspace, Provider, and Connection Repositories.

Uses PostgreSQL test container for proper integration testing since
the models use PostgreSQL-specific types (UUID, JSONB).
"""
import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from text2x.models.workspace import (
    Workspace,
    Provider,
    Connection,
    ProviderType,
    ConnectionStatus,
)
from text2x.models.base import Base, DatabaseConfig, init_db, close_db, get_db
from text2x.repositories.workspace import WorkspaceRepository
from text2x.repositories.provider import ProviderRepository
from text2x.repositories.connection import ConnectionRepository
from tests.config import TEST_POSTGRES_CONFIG


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def setup_db():
    """Set up the test database and initialize the global db connection."""
    # Create config from test settings
    config = DatabaseConfig(
        host=TEST_POSTGRES_CONFIG['host'],
        port=TEST_POSTGRES_CONFIG['port'],
        database=TEST_POSTGRES_CONFIG['database'],
        user=TEST_POSTGRES_CONFIG['username'],
        password=TEST_POSTGRES_CONFIG['password'],
        echo=False,
    )
    
    # Initialize global db
    db = init_db(config)
    
    # Create tables (drop first for clean slate)
    engine = db.engine
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS connections CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS providers CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS workspaces CASCADE"))
        await conn.run_sync(Base.metadata.create_all)
    
    yield db
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS connections CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS providers CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS workspaces CASCADE"))
    
    await close_db()


@pytest_asyncio.fixture
async def workspace_repo(setup_db):
    """Create WorkspaceRepository."""
    return WorkspaceRepository()


@pytest_asyncio.fixture
async def provider_repo(setup_db):
    """Create ProviderRepository."""
    return ProviderRepository()


@pytest_asyncio.fixture
async def connection_repo(setup_db):
    """Create ConnectionRepository."""
    return ConnectionRepository()


@pytest_asyncio.fixture
async def sample_workspace(setup_db):
    """Create a sample workspace for testing."""
    db = get_db()
    async with db.session() as session:
        workspace = Workspace(
            id=uuid4(),
            name="Test Workspace",
            slug="test-workspace",
            description="A test workspace",
            settings={"theme": "dark"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(workspace)
        await session.flush()
        await session.refresh(workspace)
        # Return a copy of data, not the ORM object which will be detached
        return workspace


@pytest_asyncio.fixture
async def sample_provider(setup_db, sample_workspace):
    """Create a sample provider for testing."""
    db = get_db()
    async with db.session() as session:
        provider = Provider(
            id=uuid4(),
            workspace_id=sample_workspace.id,
            name="Test PostgreSQL",
            type=ProviderType.POSTGRESQL,
            description="A test PostgreSQL provider",
            settings={"timeout": 30},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(provider)
        await session.flush()
        await session.refresh(provider)
        return provider


@pytest_asyncio.fixture
async def sample_connection(setup_db, sample_provider):
    """Create a sample connection for testing."""
    db = get_db()
    async with db.session() as session:
        connection = Connection(
            id=uuid4(),
            provider_id=sample_provider.id,
            name="Production DB",
            host="localhost",
            port=5432,
            database="testdb",
            schema_name="public",
            credentials={"username": "test", "password": "secret"},
            connection_options={"ssl": True},
            status=ConnectionStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(connection)
        await session.flush()
        await session.refresh(connection)
        return connection


# ============================================================================
# Workspace Repository Tests
# ============================================================================

class TestWorkspaceRepository:
    """Test WorkspaceRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_workspace(self, workspace_repo):
        """Test creating a new workspace."""
        workspace = await workspace_repo.create(
            name="New Workspace",
            slug="new-workspace",
            description="A new workspace",
            settings={"feature": "enabled"},
        )
        
        assert workspace is not None
        assert workspace.id is not None
        assert workspace.name == "New Workspace"
        assert workspace.slug == "new-workspace"
        assert workspace.description == "A new workspace"
        assert workspace.settings == {"feature": "enabled"}
        assert workspace.created_at is not None
        assert workspace.updated_at is not None

    @pytest.mark.asyncio
    async def test_create_workspace_duplicate_slug(self, workspace_repo, sample_workspace):
        """Test that creating workspace with duplicate slug raises error."""
        with pytest.raises(Exception):  # IntegrityError from DB
            await workspace_repo.create(
                name="Another Workspace",
                slug=sample_workspace.slug,  # Duplicate slug
                description="Should fail",
            )

    @pytest.mark.asyncio
    async def test_get_by_id(self, workspace_repo, sample_workspace):
        """Test getting workspace by ID."""
        workspace = await workspace_repo.get_by_id(sample_workspace.id)
        
        assert workspace is not None
        assert workspace.id == sample_workspace.id
        assert workspace.name == sample_workspace.name

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, workspace_repo):
        """Test getting non-existent workspace returns None."""
        workspace = await workspace_repo.get_by_id(uuid4())
        assert workspace is None

    @pytest.mark.asyncio
    async def test_get_by_slug(self, workspace_repo, sample_workspace):
        """Test getting workspace by slug."""
        workspace = await workspace_repo.get_by_slug(sample_workspace.slug)
        
        assert workspace is not None
        assert workspace.slug == sample_workspace.slug

    @pytest.mark.asyncio
    async def test_get_by_slug_not_found(self, workspace_repo):
        """Test getting workspace by non-existent slug returns None."""
        workspace = await workspace_repo.get_by_slug("non-existent-slug")
        assert workspace is None

    @pytest.mark.asyncio
    async def test_list_all(self, workspace_repo, sample_workspace):
        """Test listing all workspaces."""
        # Create another workspace
        await workspace_repo.create(
            name="Second Workspace",
            slug="second-workspace",
        )
        
        workspaces = await workspace_repo.list_all()
        
        assert len(workspaces) >= 2
        slugs = [w.slug for w in workspaces]
        assert "test-workspace" in slugs
        assert "second-workspace" in slugs

    @pytest.mark.asyncio
    async def test_update_workspace(self, workspace_repo, sample_workspace):
        """Test updating a workspace."""
        updated = await workspace_repo.update(
            sample_workspace.id,
            name="Updated Name",
            description="Updated description",
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"
        assert updated.slug == sample_workspace.slug  # Unchanged

    @pytest.mark.asyncio
    async def test_update_workspace_not_found(self, workspace_repo):
        """Test updating non-existent workspace returns None."""
        updated = await workspace_repo.update(uuid4(), name="New Name")
        assert updated is None

    @pytest.mark.asyncio
    async def test_delete_workspace(self, workspace_repo, sample_workspace):
        """Test deleting a workspace."""
        result = await workspace_repo.delete(sample_workspace.id)
        assert result is True
        
        # Verify deleted
        workspace = await workspace_repo.get_by_id(sample_workspace.id)
        assert workspace is None

    @pytest.mark.asyncio
    async def test_delete_workspace_not_found(self, workspace_repo):
        """Test deleting non-existent workspace returns False."""
        result = await workspace_repo.delete(uuid4())
        assert result is False


# ============================================================================
# Provider Repository Tests
# ============================================================================

class TestProviderRepository:
    """Test ProviderRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_provider(self, provider_repo, sample_workspace):
        """Test creating a new provider."""
        provider = await provider_repo.create(
            workspace_id=sample_workspace.id,
            name="New Provider",
            type=ProviderType.MYSQL,
            description="A MySQL provider",
            settings={"charset": "utf8"},
        )
        
        assert provider is not None
        assert provider.id is not None
        assert provider.workspace_id == sample_workspace.id
        assert provider.name == "New Provider"
        assert provider.type == ProviderType.MYSQL
        assert provider.description == "A MySQL provider"

    @pytest.mark.asyncio
    async def test_create_provider_invalid_workspace(self, provider_repo):
        """Test creating provider with invalid workspace_id returns None."""
        result = await provider_repo.create(
            workspace_id=uuid4(),  # Non-existent
            name="Bad Provider",
            type=ProviderType.POSTGRESQL,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id(self, provider_repo, sample_provider):
        """Test getting provider by ID."""
        provider = await provider_repo.get_by_id(sample_provider.id)
        
        assert provider is not None
        assert provider.id == sample_provider.id
        assert provider.name == sample_provider.name

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, provider_repo):
        """Test getting non-existent provider returns None."""
        provider = await provider_repo.get_by_id(uuid4())
        assert provider is None

    @pytest.mark.asyncio
    async def test_list_by_workspace(self, provider_repo, sample_workspace, sample_provider):
        """Test listing providers by workspace."""
        # Create another provider in same workspace
        await provider_repo.create(
            workspace_id=sample_workspace.id,
            name="Second Provider",
            type=ProviderType.MONGODB,
        )
        
        providers = await provider_repo.list_by_workspace(sample_workspace.id)
        
        assert len(providers) == 2
        names = [p.name for p in providers]
        assert "Test PostgreSQL" in names
        assert "Second Provider" in names

    @pytest.mark.asyncio
    async def test_list_by_workspace_empty(self, provider_repo, workspace_repo):
        """Test listing providers for workspace with no providers."""
        # Create workspace without providers
        workspace = await workspace_repo.create(
            name="Empty Workspace",
            slug="empty-workspace",
        )
        
        providers = await provider_repo.list_by_workspace(workspace.id)
        assert len(providers) == 0

    @pytest.mark.asyncio
    async def test_update_provider(self, provider_repo, sample_provider):
        """Test updating a provider."""
        updated = await provider_repo.update(
            sample_provider.id,
            name="Updated Provider",
            description="New description",
        )
        
        assert updated is not None
        assert updated.name == "Updated Provider"
        assert updated.description == "New description"
        assert updated.type == sample_provider.type  # Unchanged

    @pytest.mark.asyncio
    async def test_update_provider_not_found(self, provider_repo):
        """Test updating non-existent provider returns None."""
        updated = await provider_repo.update(uuid4(), name="New Name")
        assert updated is None

    @pytest.mark.asyncio
    async def test_delete_provider(self, provider_repo, sample_provider):
        """Test deleting a provider."""
        result = await provider_repo.delete(sample_provider.id)
        assert result is True
        
        # Verify deleted
        provider = await provider_repo.get_by_id(sample_provider.id)
        assert provider is None

    @pytest.mark.asyncio
    async def test_delete_provider_not_found(self, provider_repo):
        """Test deleting non-existent provider returns False."""
        result = await provider_repo.delete(uuid4())
        assert result is False


# ============================================================================
# Connection Repository Tests
# ============================================================================

class TestConnectionRepository:
    """Test ConnectionRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_connection(self, connection_repo, sample_provider):
        """Test creating a new connection."""
        connection = await connection_repo.create(
            provider_id=sample_provider.id,
            name="Staging DB",
            host="staging.example.com",
            port=5432,
            database="staging_db",
            schema_name="public",
            credentials={"user": "admin", "pass": "secret"},
            connection_options={"ssl": False},
        )
        
        assert connection is not None
        assert connection.id is not None
        assert connection.provider_id == sample_provider.id
        assert connection.name == "Staging DB"
        assert connection.host == "staging.example.com"
        assert connection.status == ConnectionStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_connection_invalid_provider(self, connection_repo):
        """Test creating connection with invalid provider_id returns None."""
        result = await connection_repo.create(
            provider_id=uuid4(),  # Non-existent
            name="Bad Connection",
            host="localhost",
            database="test",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id(self, connection_repo, sample_connection):
        """Test getting connection by ID."""
        connection = await connection_repo.get_by_id(sample_connection.id)
        
        assert connection is not None
        assert connection.id == sample_connection.id
        assert connection.name == sample_connection.name

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, connection_repo):
        """Test getting non-existent connection returns None."""
        connection = await connection_repo.get_by_id(uuid4())
        assert connection is None

    @pytest.mark.asyncio
    async def test_list_by_provider(self, connection_repo, sample_provider, sample_connection):
        """Test listing connections by provider."""
        # Create another connection
        await connection_repo.create(
            provider_id=sample_provider.id,
            name="Development DB",
            host="dev.example.com",
            database="dev_db",
        )
        
        connections = await connection_repo.list_by_provider(sample_provider.id)
        
        assert len(connections) == 2
        names = [c.name for c in connections]
        assert "Production DB" in names
        assert "Development DB" in names

    @pytest.mark.asyncio
    async def test_update_connection(self, connection_repo, sample_connection):
        """Test updating a connection."""
        updated = await connection_repo.update(
            sample_connection.id,
            name="Updated Connection",
            host="new-host.example.com",
            port=5433,
        )
        
        assert updated is not None
        assert updated.name == "Updated Connection"
        assert updated.host == "new-host.example.com"
        assert updated.port == 5433

    @pytest.mark.asyncio
    async def test_update_connection_not_found(self, connection_repo):
        """Test updating non-existent connection returns None."""
        updated = await connection_repo.update(uuid4(), name="New Name")
        assert updated is None

    @pytest.mark.asyncio
    async def test_update_status(self, connection_repo, sample_connection):
        """Test updating connection status."""
        updated = await connection_repo.update_status(
            sample_connection.id,
            status=ConnectionStatus.CONNECTED,
            status_message="Connection successful",
        )
        
        assert updated is not None
        assert updated.status == ConnectionStatus.CONNECTED
        assert updated.status_message == "Connection successful"
        assert updated.last_health_check is not None

    @pytest.mark.asyncio
    async def test_update_status_error(self, connection_repo, sample_connection):
        """Test updating connection status to error."""
        updated = await connection_repo.update_status(
            sample_connection.id,
            status=ConnectionStatus.ERROR,
            status_message="Connection refused",
        )
        
        assert updated is not None
        assert updated.status == ConnectionStatus.ERROR
        assert updated.status_message == "Connection refused"

    @pytest.mark.asyncio
    async def test_update_schema_refresh_time(self, connection_repo, sample_connection):
        """Test updating schema refresh timestamp."""
        cache_key = f"schema:{sample_connection.id}"
        
        updated = await connection_repo.update_schema_refresh_time(
            sample_connection.id,
            schema_cache_key=cache_key,
        )
        
        assert updated is not None
        assert updated.schema_cache_key == cache_key
        assert updated.schema_last_refreshed is not None

    @pytest.mark.asyncio
    async def test_delete_connection(self, connection_repo, sample_connection):
        """Test deleting a connection."""
        result = await connection_repo.delete(sample_connection.id)
        assert result is True
        
        # Verify deleted
        connection = await connection_repo.get_by_id(sample_connection.id)
        assert connection is None

    @pytest.mark.asyncio
    async def test_delete_connection_not_found(self, connection_repo):
        """Test deleting non-existent connection returns False."""
        result = await connection_repo.delete(uuid4())
        assert result is False


# ============================================================================
# Integration Tests - Cascade Behavior
# ============================================================================

class TestCascadeDelete:
    """Test cascade delete behavior."""

    @pytest.mark.asyncio
    async def test_delete_workspace_cascades_to_providers(
        self, workspace_repo, provider_repo, sample_workspace, sample_provider
    ):
        """Test that deleting workspace cascades to providers."""
        # Verify provider exists
        provider = await provider_repo.get_by_id(sample_provider.id)
        assert provider is not None
        
        # Delete workspace
        await workspace_repo.delete(sample_workspace.id)
        
        # Verify provider is also deleted
        provider = await provider_repo.get_by_id(sample_provider.id)
        assert provider is None

    @pytest.mark.asyncio
    async def test_delete_provider_cascades_to_connections(
        self, provider_repo, connection_repo, sample_provider, sample_connection
    ):
        """Test that deleting provider cascades to connections."""
        # Verify connection exists
        connection = await connection_repo.get_by_id(sample_connection.id)
        assert connection is not None
        
        # Delete provider
        await provider_repo.delete(sample_provider.id)
        
        # Verify connection is also deleted
        connection = await connection_repo.get_by_id(sample_connection.id)
        assert connection is None

    @pytest.mark.asyncio
    async def test_full_cascade_workspace_to_connections(
        self, workspace_repo, provider_repo, connection_repo,
        sample_workspace, sample_provider, sample_connection
    ):
        """Test full cascade from workspace through provider to connection."""
        # Verify all exist
        assert await workspace_repo.get_by_id(sample_workspace.id) is not None
        assert await provider_repo.get_by_id(sample_provider.id) is not None
        assert await connection_repo.get_by_id(sample_connection.id) is not None
        
        # Delete workspace
        await workspace_repo.delete(sample_workspace.id)
        
        # Verify all are deleted
        assert await workspace_repo.get_by_id(sample_workspace.id) is None
        assert await provider_repo.get_by_id(sample_provider.id) is None
        assert await connection_repo.get_by_id(sample_connection.id) is None
