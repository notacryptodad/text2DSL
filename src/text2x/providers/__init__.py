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
from .splunk_provider import (
    SplunkProvider,
    SplunkConnectionConfig,
    SplunkSearchJob,
    SplunkFieldInfo,
    SplunkIndexInfo,
    SearchJobStatus,
    create_splunk_provider,
)
from .nosql_provider import (
    NoSQLProvider,
    MongoDBConnectionConfig,
    create_nosql_provider,
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
    # Splunk Provider
    "SplunkProvider",
    "SplunkConnectionConfig",
    "SplunkSearchJob",
    "SplunkFieldInfo",
    "SplunkIndexInfo",
    "SearchJobStatus",
    "create_splunk_provider",
    # NoSQL Provider
    "NoSQLProvider",
    "MongoDBConnectionConfig",
    "create_nosql_provider",
]
