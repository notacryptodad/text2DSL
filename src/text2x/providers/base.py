"""Base Provider Interface for Text2X"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class ProviderCapability(Enum):
    """Capabilities that a provider can support"""

    SCHEMA_INTROSPECTION = "schema_introspection"
    QUERY_VALIDATION = "query_validation"
    QUERY_EXECUTION = "query_execution"
    QUERY_EXPLANATION = "query_explanation"
    DRY_RUN = "dry_run"
    COST_ESTIMATION = "cost_estimation"


@dataclass
class ColumnInfo:
    """Information about a database column"""

    name: str
    type: str
    nullable: bool = True
    default: Optional[str] = None
    primary_key: bool = False
    unique: bool = False
    comment: Optional[str] = None
    autoincrement: bool = False
    nested: Optional[List["ColumnInfo"]] = None


@dataclass
class IndexInfo:
    """Information about a database index"""

    name: str
    columns: List[str]
    unique: bool = False
    type: Optional[str] = None  # btree, hash, etc.


@dataclass
class ForeignKeyInfo:
    """Information about a foreign key relationship"""

    name: Optional[str]
    constrained_columns: List[str]
    referred_schema: Optional[str]
    referred_table: str
    referred_columns: List[str]
    on_delete: Optional[str] = None  # CASCADE, SET NULL, etc.
    on_update: Optional[str] = None


@dataclass
class TableInfo:
    """Information about a database table"""

    name: str
    schema: Optional[str] = None
    columns: List[ColumnInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    foreign_keys: List[ForeignKeyInfo] = field(default_factory=list)
    primary_key: Optional[List[str]] = None
    comment: Optional[str] = None
    row_count: Optional[int] = None


@dataclass
class Relationship:
    """Represents a relationship between tables"""

    from_table: str
    to_table: str
    from_columns: List[str]
    to_columns: List[str]
    relationship_type: str  # "one-to-one", "one-to-many", "many-to-many"


@dataclass
class JoinPath:
    """Represents a suggested join path between tables"""

    tables: List[str]
    joins: List[Dict[str, Any]]  # List of join conditions


@dataclass
class SchemaDefinition:
    """Complete schema definition for a data source"""

    tables: List[TableInfo] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # For non-SQL systems
    sourcetypes: Optional[List[str]] = None  # For Splunk
    collections: Optional[List[str]] = None  # For MongoDB


@dataclass
class ValidationResult:
    """Result of query validation"""

    valid: bool
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    parsed_query: Optional[Any] = None
    validation_time_ms: Optional[float] = None


@dataclass
class ExecutionResult:
    """Result of query execution"""

    success: bool
    row_count: int = 0
    columns: Optional[List[str]] = None
    sample_rows: Optional[List[Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    query_plan: Optional[str] = None  # EXPLAIN output if available
    affected_rows: Optional[int] = None  # For UPDATE/DELETE/INSERT


@dataclass
class ProviderConfig:
    """Base configuration for a provider"""

    provider_type: str
    timeout_seconds: int = 30
    max_rows: int = 1000
    enable_query_plan: bool = False
    extra_params: Dict[str, Any] = field(default_factory=dict)


class QueryProvider(ABC):
    """Base interface for all query providers"""

    @abstractmethod
    def get_provider_id(self) -> str:
        """Unique identifier for this provider"""
        pass

    @abstractmethod
    def get_query_language(self) -> str:
        """e.g., 'SQL', 'SPL', 'MongoDB Query'"""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[ProviderCapability]:
        """List of capabilities this provider supports"""
        pass

    @abstractmethod
    async def get_schema(self) -> SchemaDefinition:
        """Retrieve the schema/structure of the target system"""
        pass

    @abstractmethod
    async def validate_syntax(self, query: str) -> ValidationResult:
        """Check if query is syntactically valid"""
        pass

    async def execute_query(self, query: str, limit: int = 100) -> Optional[ExecutionResult]:
        """Execute query and return results (optional)"""
        if ProviderCapability.QUERY_EXECUTION not in self.get_capabilities():
            return None
        raise NotImplementedError()

    async def explain_query(self, query: str) -> Optional[str]:
        """Get query execution plan (optional)"""
        if ProviderCapability.QUERY_EXPLANATION not in self.get_capabilities():
            return None
        raise NotImplementedError()

    async def dry_run(self, query: str) -> ValidationResult:
        """Validate query without executing (optional)"""
        if ProviderCapability.DRY_RUN not in self.get_capabilities():
            return await self.validate_syntax(query)
        raise NotImplementedError()

    async def estimate_cost(self, query: str) -> Optional[Dict[str, Any]]:
        """Estimate query cost (optional)"""
        if ProviderCapability.COST_ESTIMATION not in self.get_capabilities():
            return None
        raise NotImplementedError()

    async def close(self) -> None:
        """Close any open connections"""
        pass
