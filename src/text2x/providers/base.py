"""Base Provider Interface for Text2X"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

class ProviderCapability(Enum):
    SCHEMA_INTROSPECTION = "schema_introspection"
    QUERY_VALIDATION = "query_validation"
    QUERY_EXECUTION = "query_execution"
    QUERY_EXPLANATION = "query_explanation"
    DRY_RUN = "dry_run"
    COST_ESTIMATION = "cost_estimation"

@dataclass
class ValidationResult:
    valid: bool
    error: Optional[str] = None
    parsed_query: Optional[Any] = None

@dataclass
class ExecutionResult:
    success: bool
    row_count: int = 0
    columns: List[str] = None
    sample_rows: List[Any] = None
    error: Optional[str] = None

@dataclass
class SchemaDefinition:
    tables: List[Any] = None
    indexes: List[Any] = None
    sourcetypes: List[Any] = None

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
