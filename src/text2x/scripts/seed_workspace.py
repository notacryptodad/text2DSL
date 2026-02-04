#!/usr/bin/env python3
"""
Seed script to create default workspace with providers and connections.

This script creates:
- A default workspace named "Demo Workspace"
- PostgreSQL provider with connection to the test database
- MongoDB provider (placeholder)

Run this script after migrations to seed demo data.
"""

import asyncio
import sys
import logging
from pathlib import Path
from uuid import uuid4

# Add src to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from text2x.models.base import DatabaseConfig, init_db
from text2x.models.workspace import Workspace, Provider, Connection, ProviderType, ConnectionStatus
from text2x.repositories.workspace import WorkspaceRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_WORKSPACE = {
    "name": "Demo Workspace",
    "slug": "demo-workspace",
    "description": "Default workspace with sample PostgreSQL and MongoDB connections for testing",
}

POSTGRES_PROVIDER = {
    "name": "PostgreSQL",
    "type": ProviderType.POSTGRESQL,
    "description": "Main PostgreSQL test database",
}

POSTGRES_CONNECTION = {
    "name": "Test Database",
    "host": "localhost",
    "port": 5432,
    "database": "text2dsl_test",
    "schema_name": "public",
    "credentials": {"username": "postgres", "password": "postgres"},
}

MONGODB_PROVIDER = {
    "name": "MongoDB",
    "type": ProviderType.MONGODB,
    "description": "MongoDB test database",
}

MONGODB_CONNECTION = {
    "name": "Test Database",
    "host": "localhost",
    "port": 27017,
    "database": "text2x_test",
}


async def seed_workspace():
    """Create default workspace with providers and connections."""
    from text2x.models.base import get_db

    try:
        # Initialize database
        config = DatabaseConfig.from_env()
        db = init_db(config)

        # Check if workspace already exists
        repo = WorkspaceRepository()
        existing = await repo.get_by_slug(DEFAULT_WORKSPACE["slug"])

        if existing:
            logger.info(f"✅ Default workspace already exists: {DEFAULT_WORKSPACE['slug']}")
            return existing

        # Create workspace with providers and connections in a single transaction
        async with db.session() as session:
            workspace = Workspace(
                name=DEFAULT_WORKSPACE["name"],
                slug=DEFAULT_WORKSPACE["slug"],
                description=DEFAULT_WORKSPACE["description"],
                is_active=True,
            )
            session.add(workspace)
            await session.flush()

            postgres_provider = Provider(
                workspace_id=workspace.id,
                name=POSTGRES_PROVIDER["name"],
                type=POSTGRES_PROVIDER["type"],
                description=POSTGRES_PROVIDER["description"],
            )
            session.add(postgres_provider)
            await session.flush()

            postgres_connection = Connection(
                provider_id=postgres_provider.id,
                name=POSTGRES_CONNECTION["name"],
                host=POSTGRES_CONNECTION["host"],
                port=POSTGRES_CONNECTION["port"],
                database=POSTGRES_CONNECTION["database"],
                schema_name=POSTGRES_CONNECTION.get("schema_name"),
                credentials=POSTGRES_CONNECTION.get("credentials"),
                status=ConnectionStatus.CONNECTED,
                status_message="Successfully connected to test database",
            )
            session.add(postgres_connection)

            mongodb_provider = Provider(
                workspace_id=workspace.id,
                name=MONGODB_PROVIDER["name"],
                type=MONGODB_PROVIDER["type"],
                description=MONGODB_PROVIDER["description"],
            )
            session.add(mongodb_provider)
            await session.flush()

            mongodb_connection = Connection(
                provider_id=mongodb_provider.id,
                name=MONGODB_CONNECTION["name"],
                host=MONGODB_CONNECTION["host"],
                port=MONGODB_CONNECTION["port"],
                database=MONGODB_CONNECTION["database"],
                status=ConnectionStatus.PENDING,
            )
            session.add(mongodb_connection)

            await session.commit()
            await session.refresh(workspace)

        logger.info(f"✅ Default workspace created successfully!")
        logger.info(f"   Workspace: {workspace.name} ({workspace.slug})")
        logger.info(
            f"   PostgreSQL Provider: {postgres_provider.name} → {postgres_connection.database}"
        )
        logger.info(f"   MongoDB Provider: {mongodb_provider.name} → {mongodb_connection.database}")

        return workspace

    except Exception as e:
        logger.error(f"❌ Failed to seed workspace: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(seed_workspace())
