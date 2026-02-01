"""
Workspace and Connection models for Text2DSL.

This module provides the multi-tenancy layer:
- Workspace: Logical grouping of providers for a team/project
- Connection: A specific database connection with credentials, maps to a schema
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .conversation import Conversation


class ConnectionStatus(str, Enum):
    """Connection health status."""
    
    PENDING = "pending"  # Not yet tested
    CONNECTED = "connected"  # Successfully connected
    DISCONNECTED = "disconnected"  # Failed to connect
    ERROR = "error"  # Connection error


class ProviderType(str, Enum):
    """Supported database provider types."""
    
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ATHENA = "athena"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    REDSHIFT = "redshift"
    MONGODB = "mongodb"
    OPENSEARCH = "opensearch"
    ELASTICSEARCH = "elasticsearch"
    SPLUNK = "splunk"


class Workspace(Base, UUIDMixin, TimestampMixin):
    """
    A workspace is a logical grouping of database providers/connections.
    
    Workspaces provide multi-tenancy support, allowing different teams
    or projects to have isolated sets of database connections.
    
    Attributes:
        id: Unique workspace identifier (UUID)
        name: Human-readable workspace name
        slug: URL-friendly unique identifier
        description: Optional description of the workspace purpose
        settings: JSON blob for workspace-specific settings
        providers: List of providers linked to this workspace
        created_at: When the workspace was created
        updated_at: When the workspace was last modified
    """
    
    __tablename__ = "workspaces"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Relationships
    providers: Mapped[List["Provider"]] = relationship(
        "Provider",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Workspace(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Provider(Base, UUIDMixin, TimestampMixin):
    """
    A provider represents a database type/platform within a workspace.
    
    Each provider can have multiple connections (e.g., dev, staging, prod
    environments of the same database type).
    
    Attributes:
        id: Unique provider identifier (UUID)
        workspace_id: Parent workspace UUID
        name: Human-readable provider name
        type: Database type (postgresql, mysql, athena, etc.)
        description: Optional description
        settings: Provider-specific settings (timeouts, defaults, etc.)
        connections: List of connections for this provider
        created_at: When the provider was created
        updated_at: When the provider was last modified
    """
    
    __tablename__ = "providers"
    
    workspace_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[ProviderType] = mapped_column(
        SQLEnum(ProviderType, native_enum=False),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="providers")
    connections: Mapped[List["Connection"]] = relationship(
        "Connection",
        back_populates="provider",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_provider_workspace_name"),
        Index("ix_providers_workspace_type", "workspace_id", "type"),
    )
    
    def __repr__(self) -> str:
        return f"<Provider(id={self.id}, name='{self.name}', type={self.type.value})>"


class Connection(Base, UUIDMixin, TimestampMixin):
    """
    A connection represents a specific database instance with credentials.
    
    Each connection maps to a schema (set of tables/collections). Multiple
    connections can exist for the same provider (e.g., different environments
    or different databases on the same server).
    
    Attributes:
        id: Unique connection identifier (UUID)
        provider_id: Parent provider UUID
        name: Human-readable connection name (e.g., "Production", "Analytics")
        host: Database host/endpoint
        port: Database port (optional, uses provider default)
        database: Database/catalog name
        schema_name: Schema/namespace within the database (optional)
        credentials: Encrypted credentials blob (username, password, etc.)
        connection_options: Additional connection parameters (SSL, etc.)
        status: Current connection health status
        last_health_check: When connection was last tested
        schema_cache_key: Redis key for cached schema
        schema_last_refreshed: When schema was last introspected
        conversations: Conversations using this connection
        created_at: When the connection was created
        updated_at: When the connection was last modified
    """
    
    __tablename__ = "connections"
    
    provider_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Connection details
    host: Mapped[str] = mapped_column(String(512), nullable=False)
    port: Mapped[Optional[int]] = mapped_column(nullable=True)
    database: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Credentials (should be encrypted at rest)
    credentials: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Additional connection options
    connection_options: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Connection status
    status: Mapped[ConnectionStatus] = mapped_column(
        SQLEnum(ConnectionStatus, native_enum=False),
        nullable=False,
        default=ConnectionStatus.PENDING,
    )
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Schema caching
    schema_cache_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    schema_last_refreshed: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    provider: Mapped["Provider"] = relationship("Provider", back_populates="connections")
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="connection",
        lazy="selectin",
    )
    
    __table_args__ = (
        UniqueConstraint("provider_id", "name", name="uq_connection_provider_name"),
        Index("ix_connections_status", "status"),
        Index("ix_connections_provider_database", "provider_id", "database"),
    )
    
    def __repr__(self) -> str:
        return f"<Connection(id={self.id}, name='{self.name}', database='{self.database}', status={self.status.value})>"
    
    @property
    def display_name(self) -> str:
        """Full display name including provider context."""
        schema_part = f".{self.schema_name}" if self.schema_name else ""
        return f"{self.database}{schema_part}"
    
    def get_connection_string(self, include_credentials: bool = False) -> str:
        """
        Build a connection string for this connection.
        
        Args:
            include_credentials: Whether to include username/password
            
        Returns:
            Connection string (format depends on provider type)
        """
        # This would be implemented per-provider type
        # For now, return a generic format
        port_str = f":{self.port}" if self.port else ""
        schema_str = f"/{self.schema_name}" if self.schema_name else ""
        
        if include_credentials and self.credentials:
            user = self.credentials.get("username", "")
            passwd = self.credentials.get("password", "")
            if user:
                auth = f"{user}:{passwd}@" if passwd else f"{user}@"
                return f"{auth}{self.host}{port_str}/{self.database}{schema_str}"
        
        return f"{self.host}{port_str}/{self.database}{schema_str}"
