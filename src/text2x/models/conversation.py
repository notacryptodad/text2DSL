"""
Conversation and query response models for Text2DSL.

This module defines the database models for tracking user conversations,
individual turns within conversations, and the query responses generated
by the system.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin


class ConversationStatus(str, PyEnum):
    """Status of a conversation."""
    
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Conversation(Base, UUIDMixin, TimestampMixin):
    """
    Represents a conversation session between a user and the system.
    
    A conversation contains multiple turns where the user asks questions
    and the system generates query responses.
    """
    
    __tablename__ = "conversations"
    
    user_id = Column(String(255), nullable=False, index=True)
    provider_id = Column(String(255), nullable=False, index=True)
    status = Column(
        Enum(ConversationStatus),
        nullable=False,
        default=ConversationStatus.ACTIVE,
        index=True,
    )
    
    # Relationships
    turns = relationship(
        "ConversationTurn",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationTurn.turn_number",
    )
    audit_logs = relationship(
        "AuditLog",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return (
            f"<Conversation(id={self.id}, user_id={self.user_id}, "
            f"status={self.status}, turns={len(self.turns)})>"
        )


class ConversationTurn(Base, UUIDMixin, TimestampMixin):
    """
    Represents a single turn in a conversation.
    
    Each turn captures:
    - User's natural language input
    - System's query response
    - Reasoning traces showing how the query was generated
    - Turn number for ordering
    """
    
    __tablename__ = "conversation_turns"
    
    conversation_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    turn_number = Column(Integer, nullable=False)
    user_input = Column(Text, nullable=False)
    
    # Query response fields (denormalized for quick access)
    generated_query = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=False)
    iterations = Column(Integer, nullable=False, default=1)
    clarification_needed = Column(Boolean, nullable=False, default=False)
    clarification_question = Column(Text, nullable=True)
    
    # Validation and execution results stored as JSON
    validation_result = Column(JSON, nullable=True)
    execution_result = Column(JSON, nullable=True)
    
    # Reasoning trace showing the decision-making process
    reasoning_trace = Column(JSON, nullable=False)
    
    # Schema context used for this turn
    schema_context = Column(JSON, nullable=True)
    
    # RAG examples used for this turn
    rag_examples_used = Column(JSON, nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="turns")
    audit_log = relationship(
        "AuditLog",
        back_populates="turn",
        uselist=False,
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return (
            f"<ConversationTurn(id={self.id}, "
            f"conversation_id={self.conversation_id}, "
            f"turn_number={self.turn_number})>"
        )


class ValidationResult:
    """
    Structure for validation results (stored as JSON).
    
    This is not a database model but a data structure that gets
    serialized to JSON in the validation_result column.
    """
    
    def __init__(
        self,
        is_valid: bool,
        syntax_errors: list[str] | None = None,
        semantic_errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ):
        """
        Initialize validation result.
        
        Args:
            is_valid: Whether the query is valid
            syntax_errors: List of syntax errors found
            semantic_errors: List of semantic errors found
            warnings: List of warnings
        """
        self.is_valid = is_valid
        self.syntax_errors = syntax_errors or []
        self.semantic_errors = semantic_errors or []
        self.warnings = warnings or []
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_valid": self.is_valid,
            "syntax_errors": self.syntax_errors,
            "semantic_errors": self.semantic_errors,
            "warnings": self.warnings,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ValidationResult":
        """Create from dictionary."""
        return cls(
            is_valid=data["is_valid"],
            syntax_errors=data.get("syntax_errors", []),
            semantic_errors=data.get("semantic_errors", []),
            warnings=data.get("warnings", []),
        )


class ExecutionResult:
    """
    Structure for execution results (stored as JSON).
    
    This is not a database model but a data structure that gets
    serialized to JSON in the execution_result column.
    """
    
    def __init__(
        self,
        success: bool,
        row_count: int | None = None,
        execution_time_ms: int | None = None,
        error_message: str | None = None,
        result_preview: list[dict] | None = None,
    ):
        """
        Initialize execution result.
        
        Args:
            success: Whether the query executed successfully
            row_count: Number of rows returned or affected
            execution_time_ms: Query execution time in milliseconds
            error_message: Error message if execution failed
            result_preview: Preview of results (first few rows)
        """
        self.success = success
        self.row_count = row_count
        self.execution_time_ms = execution_time_ms
        self.error_message = error_message
        self.result_preview = result_preview or []
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "row_count": self.row_count,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "result_preview": self.result_preview,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionResult":
        """Create from dictionary."""
        return cls(
            success=data["success"],
            row_count=data.get("row_count"),
            execution_time_ms=data.get("execution_time_ms"),
            error_message=data.get("error_message"),
            result_preview=data.get("result_preview", []),
        )


class ReasoningTrace:
    """
    Structure for reasoning traces (stored as JSON).
    
    This captures the step-by-step reasoning process used to generate
    the query, including agent decisions and iterations.
    """
    
    def __init__(
        self,
        steps: list[dict],
        schema_analysis: dict | None = None,
        rag_retrieval: dict | None = None,
        query_construction: dict | None = None,
        validation_attempts: list[dict] | None = None,
    ):
        """
        Initialize reasoning trace.
        
        Args:
            steps: List of reasoning steps
            schema_analysis: Schema analysis results
            rag_retrieval: RAG retrieval results
            query_construction: Query construction process
            validation_attempts: List of validation attempts
        """
        self.steps = steps
        self.schema_analysis = schema_analysis
        self.rag_retrieval = rag_retrieval
        self.query_construction = query_construction
        self.validation_attempts = validation_attempts or []
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "steps": self.steps,
            "schema_analysis": self.schema_analysis,
            "rag_retrieval": self.rag_retrieval,
            "query_construction": self.query_construction,
            "validation_attempts": self.validation_attempts,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ReasoningTrace":
        """Create from dictionary."""
        return cls(
            steps=data.get("steps", []),
            schema_analysis=data.get("schema_analysis"),
            rag_retrieval=data.get("rag_retrieval"),
            query_construction=data.get("query_construction"),
            validation_attempts=data.get("validation_attempts", []),
        )
