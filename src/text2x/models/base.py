"""
Base models and database session management for Text2DSL.

This module provides the foundational components for the database layer:
- SQLAlchemy declarative base
- Async database session management
- Database configuration
- Common mixins and utilities
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Base class for all database models."""
    
    pass


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps to models."""
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )


class UUIDMixin:
    """Mixin to add UUID primary key to models."""
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)


class DatabaseConfig:
    """Database configuration and connection management."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "text2x",
        user: str = "text2x",
        password: str = "text2x",
        pool_size: int = 5,
        max_overflow: int = 10,
        echo: bool = False,
    ):
        """
        Initialize database configuration.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
            echo: Whether to echo SQL statements (for debugging)
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.echo = echo
        
    @property
    def url(self) -> str:
        """Get the database connection URL."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """
        Create database configuration from environment variables.
        
        Environment variables:
            DB_HOST: Database host (default: localhost)
            DB_PORT: Database port (default: 5432)
            DB_NAME: Database name (default: text2x)
            DB_USER: Database user (default: text2x)
            DB_PASSWORD: Database password (default: text2x)
            DB_POOL_SIZE: Connection pool size (default: 5)
            DB_MAX_OVERFLOW: Maximum overflow connections (default: 10)
            DB_ECHO: Echo SQL statements (default: False)
        
        Returns:
            DatabaseConfig instance
        """
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "text2x"),
            user=os.getenv("DB_USER", "text2x"),
            password=os.getenv("DB_PASSWORD", "text2x"),
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
        )


class DatabaseSession:
    """
    Manages database engine and session creation.
    
    This class provides async context managers for database sessions
    and handles connection pooling.
    """
    
    def __init__(self, config: DatabaseConfig):
        """
        Initialize database session manager.
        
        Args:
            config: Database configuration
        """
        self.config = config
        self.engine = create_async_engine(
            config.url,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            echo=config.echo,
            pool_pre_ping=True,  # Enable connection health checks
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Create an async database session context manager.
        
        Usage:
            async with db.session() as session:
                result = await session.execute(query)
                await session.commit()
        
        Yields:
            AsyncSession instance
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self) -> None:
        """Close the database engine and all connections."""
        await self.engine.dispose()


# Global database session instance
_db_session: DatabaseSession | None = None


def init_db(config: DatabaseConfig | None = None) -> DatabaseSession:
    """
    Initialize the global database session.
    
    Args:
        config: Database configuration. If None, loads from environment.
    
    Returns:
        DatabaseSession instance
    """
    global _db_session
    
    if config is None:
        config = DatabaseConfig.from_env()
    
    _db_session = DatabaseSession(config)
    return _db_session


def get_db() -> DatabaseSession:
    """
    Get the global database session.
    
    Returns:
        DatabaseSession instance
    
    Raises:
        RuntimeError: If database has not been initialized
    """
    if _db_session is None:
        raise RuntimeError(
            "Database not initialized. Call init_db() first."
        )
    return _db_session


async def close_db() -> None:
    """Close the global database session."""
    global _db_session
    
    if _db_session is not None:
        await _db_session.close()
        _db_session = None
