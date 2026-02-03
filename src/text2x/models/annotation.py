"""
Schema annotation models for Text2DSL.

This module defines the database models for user-provided schema annotations.
Annotations help the LLM understand the schema by providing descriptions,
business terms, examples, and special handling hints.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from .base import Base, TimestampMixin, UUIDMixin


class SchemaAnnotation(Base, UUIDMixin, TimestampMixin):
    """
    User-provided hints to help LLM understand schema.
    
    Annotations can be attached to:
    - Tables: Provide table-level descriptions and business context
    - Columns: Provide column-level descriptions, enums, formats
    
    These annotations are used by the Schema Agent to enrich the schema
    context passed to the Query Builder Agent, improving query accuracy.
    """
    
    __tablename__ = "schema_annotations"
    
    provider_id = Column(String(255), nullable=False, index=True)
    
    # Target (either table_name or column_name is set, not both)
    table_name = Column(String(255), nullable=True, index=True)
    column_name = Column(String(255), nullable=True, index=True)
    
    # Annotation content
    description = Column(Text, nullable=False)
    business_terms = Column(ARRAY(String), nullable=True)  # Natural language mappings
    examples = Column(ARRAY(String), nullable=True)
    relationships = Column(ARRAY(String), nullable=True)
    
    # Special handling hints
    date_format = Column(String(100), nullable=True)
    enum_values = Column(ARRAY(String), nullable=True)
    sensitive = Column(Boolean, nullable=False, default=False)
    
    # ===== NEW: Query generation hints =====
    
    # Table-level hints
    primary_lookup_column = Column(String(255), nullable=True)  # Main column for entity lookup (e.g., "name" for products)
    represents = Column(String(255), nullable=True)  # Business concept this table represents (e.g., "sales_event")
    
    # Column-level hints
    is_searchable = Column(Boolean, nullable=True)  # Column used in WHERE clauses
    search_type = Column(String(50), nullable=True)  # "exact", "like", "full_text", "range"
    aggregation = Column(String(50), nullable=True)  # Default aggregation: "SUM", "COUNT", "AVG", "MIN", "MAX"
    data_format = Column(String(100), nullable=True)  # "currency_usd", "percentage", "phone", etc.
    
    # Join path hints (stored as JSONB for flexibility)
    join_hints = Column(JSONB, nullable=True)  # {"target_table": "orders", "join_column": "product_id", "cardinality": "1:N"}
    
    # Creation metadata
    created_by = Column(String(255), nullable=False)
    
    def __repr__(self) -> str:
        target = self.table_name or self.column_name
        target_type = "table" if self.table_name else "column"
        return (
            f"<SchemaAnnotation(id={self.id}, provider_id={self.provider_id}, "
            f"{target_type}={target})>"
        )
    
    @property
    def is_table_annotation(self) -> bool:
        """Check if this is a table-level annotation."""
        return self.table_name is not None and self.column_name is None
    
    @property
    def is_column_annotation(self) -> bool:
        """Check if this is a column-level annotation."""
        return self.column_name is not None
    
    @property
    def target(self) -> str:
        """Get the annotation target (table or column name)."""
        return self.table_name or self.column_name or ""
    
    @property
    def target_type(self) -> str:
        """Get the annotation target type (table or column)."""
        if self.is_table_annotation:
            return "table"
        elif self.is_column_annotation:
            return "column"
        return "unknown"
    
    def to_dict(self) -> dict:
        """
        Convert annotation to dictionary for schema context.
        
        Returns:
            Dictionary representation suitable for schema context
        """
        return {
            "id": str(self.id),
            "provider_id": self.provider_id,
            "target_type": self.target_type,
            "target": self.target,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "description": self.description,
            "business_terms": self.business_terms or [],
            "examples": self.examples or [],
            "relationships": self.relationships or [],
            "date_format": self.date_format,
            "enum_values": self.enum_values or [],
            "sensitive": self.sensitive,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def create_table_annotation(
        cls,
        provider_id: str,
        table_name: str,
        description: str,
        created_by: str,
        business_terms: Optional[list[str]] = None,
        examples: Optional[list[str]] = None,
        relationships: Optional[list[str]] = None,
    ) -> "SchemaAnnotation":
        """
        Create a table-level annotation.
        
        Args:
            provider_id: Provider ID
            table_name: Name of the table
            description: Description of the table
            created_by: User who created the annotation
            business_terms: Alternative names users might use
            examples: Example use cases
            relationships: Related tables or concepts
        
        Returns:
            SchemaAnnotation instance
        """
        return cls(
            provider_id=provider_id,
            table_name=table_name,
            description=description,
            created_by=created_by,
            business_terms=business_terms,
            examples=examples,
            relationships=relationships,
        )
    
    @classmethod
    def create_column_annotation(
        cls,
        provider_id: str,
        column_name: str,
        description: str,
        created_by: str,
        business_terms: Optional[list[str]] = None,
        examples: Optional[list[str]] = None,
        date_format: Optional[str] = None,
        enum_values: Optional[list[str]] = None,
        sensitive: bool = False,
    ) -> "SchemaAnnotation":
        """
        Create a column-level annotation.
        
        Args:
            provider_id: Provider ID
            column_name: Name of the column (format: "table.column")
            description: Description of the column
            created_by: User who created the annotation
            business_terms: Alternative names users might use
            examples: Example values
            date_format: Date/time format if applicable
            enum_values: Enumeration values if applicable
            sensitive: Whether the column contains sensitive data
        
        Returns:
            SchemaAnnotation instance
        """
        return cls(
            provider_id=provider_id,
            column_name=column_name,
            description=description,
            created_by=created_by,
            business_terms=business_terms,
            examples=examples,
            date_format=date_format,
            enum_values=enum_values,
            sensitive=sensitive,
        )
