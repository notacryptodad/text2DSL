"""
Text2DSL database models.

This package contains all SQLAlchemy models for the Text2DSL system:
- Base classes and session management
- Workspace, Provider, and Connection management
- Conversation and query tracking
- RAG examples
- Audit logs
- Schema annotations
"""

from .annotation import SchemaAnnotation
from .audit import AgentTrace, AuditLog
from .base import (
    Base,
    DatabaseConfig,
    DatabaseSession,
    TimestampMixin,
    UUIDMixin,
    close_db,
    get_db,
    init_db,
)
from .conversation import (
    Conversation,
    ConversationStatus,
    ConversationTurn,
    ExecutionResult,
    ReasoningTrace,
    ValidationResult,
)
from .rag import ComplexityLevel, ExampleStatus, QueryIntent, RAGExample
from .workspace import (
    Connection,
    ConnectionStatus,
    Provider,
    ProviderType,
    Workspace,
)

__all__ = [
    # Base classes
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "DatabaseConfig",
    "DatabaseSession",
    "init_db",
    "get_db",
    "close_db",
    # Workspace models
    "Workspace",
    "Provider",
    "ProviderType",
    "Connection",
    "ConnectionStatus",
    # Conversation models
    "Conversation",
    "ConversationStatus",
    "ConversationTurn",
    "ValidationResult",
    "ExecutionResult",
    "ReasoningTrace",
    # RAG models
    "RAGExample",
    "ExampleStatus",
    "QueryIntent",
    "ComplexityLevel",
    # Audit models
    "AuditLog",
    "AgentTrace",
    # Annotation models
    "SchemaAnnotation",
]
