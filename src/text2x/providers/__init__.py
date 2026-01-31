"""Text2X Providers Package"""
from .base import (
    QueryProvider,
    ProviderCapability,
    ProviderConfig,
    SchemaDefinition,
    TableInfo,
    ColumnInfo,
    IndexInfo,
    ForeignKeyInfo,
    Relationship,
    JoinPath,
    ValidationResult,
    ExecutionResult,
)
from .sql_provider import (
    SQLProvider,
    SQLConnectionConfig,
    create_sql_provider,
)

__all__ = [
    # Base classes
    "QueryProvider",
    "ProviderCapability",
    "ProviderConfig",
    # Schema classes
    "SchemaDefinition",
    "TableInfo",
    "ColumnInfo",
    "IndexInfo",
    "ForeignKeyInfo",
    "Relationship",
    "JoinPath",
    # Result classes
    "ValidationResult",
    "ExecutionResult",
    # SQL Provider
    "SQLProvider",
    "SQLConnectionConfig",
    "create_sql_provider",
]
