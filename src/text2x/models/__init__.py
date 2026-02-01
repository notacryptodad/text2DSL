"""
Text2DSL database models.

This package contains all SQLAlchemy models for the Text2DSL system:
- Base classes and session management
- Workspace, Provider, and Connection management
- Workspace admin and access control
- Conversation and query tracking
- RAG examples
- Audit logs
- Schema annotations
- User feedback
"""

from .admin import AdminRole, WorkspaceAdmin
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
from .feedback import FeedbackCategory, FeedbackRating, UserFeedback
from .rag import ComplexityLevel, ExampleStatus, QueryIntent, RAGExample
from .workspace import (
    Connection,
    ConnectionStatus,
    Provider,
    ProviderType,
    Workspace,
)

# Import domain models from parent models.py file
# These are used by agents and need to be accessible via text2x.models
import sys
from pathlib import Path

_parent = Path(__file__).parent.parent
_models_file = _parent / "models.py"

if _models_file.exists():
    # Load models.py as a module
    import importlib.util
    spec = importlib.util.spec_from_file_location("text2x_domain_models", _models_file)
    if spec and spec.loader:
        domain_models = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(domain_models)

        # Import domain model classes (using different names to avoid conflicts)
        ColumnInfo = domain_models.ColumnInfo
        TableInfo = domain_models.TableInfo
        Relationship = domain_models.Relationship
        JoinPath = domain_models.JoinPath
        SchemaContext = domain_models.SchemaContext
        QueryResult = domain_models.QueryResult
        QueryResponse = domain_models.QueryResponse
        AgentState = domain_models.AgentState
        ValidationStatus = domain_models.ValidationStatus

        # Note: Some classes have name conflicts with DB models (RAGExample, ValidationResult, etc.)
        # For those, agents should use the domain model versions

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
    # Admin models
    "WorkspaceAdmin",
    "AdminRole",
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
    # Feedback models
    "UserFeedback",
    "FeedbackRating",
    "FeedbackCategory",
    # Domain models (from models.py)
    "ColumnInfo",
    "TableInfo",
    "Relationship",
    "JoinPath",
    "SchemaContext",
    "QueryResult",
    "QueryResponse",
    "AgentState",
    "ValidationStatus",
]
