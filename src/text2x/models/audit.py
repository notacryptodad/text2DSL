"""
Audit log models for Text2DSL.

This module defines the database models for comprehensive audit logging
of all query generation requests, including processing details, agent
traces, costs, and performance metrics.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """
    Comprehensive audit log for query generation requests.
    
    This model captures detailed information about each query generation
    attempt, including:
    - Request details (user input, provider)
    - Processing details (schema context, RAG examples)
    - Agent traces (reasoning, decisions)
    - Results (final query, validation status)
    - Costs (tokens, pricing)
    - Performance (latency, iterations)
    
    This enables debugging, monitoring, cost analysis, and system improvement.
    """
    
    __tablename__ = "audit_logs"
    
    # Foreign keys
    conversation_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    turn_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("conversation_turns.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Request details
    user_input = Column(Text, nullable=False)
    provider_id = Column(String(255), nullable=False, index=True)
    
    # Processing details
    schema_context_used = Column(JSON, nullable=False)
    rag_examples_retrieved = Column(ARRAY(PGUUID(as_uuid=True)), nullable=True)
    iterations = Column(Integer, nullable=False, default=1)
    
    # Agent traces - detailed reasoning from each agent
    schema_agent_trace = Column(JSON, nullable=True)
    query_builder_trace = Column(JSON, nullable=True)
    validator_trace = Column(JSON, nullable=True)
    
    # Results
    final_query = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=False)
    validation_status = Column(String(50), nullable=False, index=True)
    execution_success = Column(Boolean, nullable=False, default=False, index=True)
    execution_error = Column(Text, nullable=True)
    
    # Cost tracking
    total_tokens_input = Column(Integer, nullable=False, default=0)
    total_tokens_output = Column(Integer, nullable=False, default=0)
    total_cost_usd = Column(Float, nullable=False, default=0.0)
    model_used = Column(String(100), nullable=False)
    
    # Performance metrics
    total_latency_ms = Column(Integer, nullable=False)
    schema_agent_latency_ms = Column(Integer, nullable=True)
    rag_retrieval_latency_ms = Column(Integer, nullable=True)
    query_builder_latency_ms = Column(Integer, nullable=True)
    validator_latency_ms = Column(Integer, nullable=True)
    
    # Additional metadata
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="audit_logs")
    turn = relationship("ConversationTurn", back_populates="audit_log")
    
    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, conversation_id={self.conversation_id}, "
            f"turn_id={self.turn_id}, status={self.validation_status})>"
        )
    
    def add_agent_trace(
        self,
        agent_name: str,
        trace_data: dict,
        latency_ms: Optional[int] = None,
    ) -> None:
        """
        Add agent trace data to the audit log.
        
        Args:
            agent_name: Name of the agent (schema, query_builder, validator)
            trace_data: Trace data from the agent
            latency_ms: Agent execution latency in milliseconds
        """
        if agent_name == "schema":
            self.schema_agent_trace = trace_data
            if latency_ms:
                self.schema_agent_latency_ms = latency_ms
        elif agent_name == "query_builder":
            self.query_builder_trace = trace_data
            if latency_ms:
                self.query_builder_latency_ms = latency_ms
        elif agent_name == "validator":
            self.validator_trace = trace_data
            if latency_ms:
                self.validator_latency_ms = latency_ms
    
    def add_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        """
        Add cost information to the audit log.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_usd: Cost in USD
        """
        self.total_tokens_input += input_tokens
        self.total_tokens_output += output_tokens
        self.total_cost_usd += cost_usd
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens (input + output)."""
        return self.total_tokens_input + self.total_tokens_output
    
    @property
    def cost_per_token(self) -> float:
        """Calculate cost per token."""
        if self.total_tokens == 0:
            return 0.0
        return self.total_cost_usd / self.total_tokens
    
    @property
    def success(self) -> bool:
        """Check if the query generation was successful."""
        return (
            self.validation_status == "valid" and
            self.execution_success
        )


class AgentTrace:
    """
    Structure for agent traces (stored as JSON).
    
    This is not a database model but a data structure that gets
    serialized to JSON in the agent trace columns.
    """
    
    def __init__(
        self,
        agent_name: str,
        input_data: dict,
        output_data: dict,
        reasoning_steps: list[dict],
        tool_calls: list[dict] | None = None,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ):
        """
        Initialize agent trace.
        
        Args:
            agent_name: Name of the agent
            input_data: Input data to the agent
            output_data: Output data from the agent
            reasoning_steps: List of reasoning steps
            tool_calls: List of tool calls made by the agent
            errors: List of errors encountered
            warnings: List of warnings
        """
        self.agent_name = agent_name
        self.input_data = input_data
        self.output_data = output_data
        self.reasoning_steps = reasoning_steps
        self.tool_calls = tool_calls or []
        self.errors = errors or []
        self.warnings = warnings or []
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_name": self.agent_name,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "reasoning_steps": self.reasoning_steps,
            "tool_calls": self.tool_calls,
            "errors": self.errors,
            "warnings": self.warnings,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentTrace":
        """Create from dictionary."""
        return cls(
            agent_name=data["agent_name"],
            input_data=data["input_data"],
            output_data=data["output_data"],
            reasoning_steps=data.get("reasoning_steps", []),
            tool_calls=data.get("tool_calls", []),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
        )
