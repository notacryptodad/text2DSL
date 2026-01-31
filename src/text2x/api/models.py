"""Pydantic models for API request/response validation."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# Enums
class TraceLevel(str, Enum):
    """Tracing detail level."""

    NONE = "none"
    SUMMARY = "summary"
    FULL = "full"


class ConversationStatus(str, Enum):
    """Conversation lifecycle status."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ValidationStatus(str, Enum):
    """Query validation status."""

    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    UNKNOWN = "unknown"


class ExampleStatus(str, Enum):
    """RAG example review status."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class QueryIntent(str, Enum):
    """Type of query intent."""

    AGGREGATION = "aggregation"
    FILTER = "filter"
    JOIN = "join"
    SEARCH = "search"
    MIXED = "mixed"


class ComplexityLevel(str, Enum):
    """Query complexity level."""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


# Request Models
class QueryOptions(BaseModel):
    """Optional parameters for query processing."""

    model_config = ConfigDict(extra="forbid")

    max_iterations: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Maximum number of refinement iterations",
    )
    confidence_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to accept query",
    )
    trace_level: TraceLevel = Field(
        default=TraceLevel.NONE,
        description="Level of reasoning trace detail to return",
    )
    enable_execution: Optional[bool] = Field(
        default=None,
        description="Whether to execute the generated query",
    )
    rag_top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of RAG examples to retrieve",
    )


class QueryRequest(BaseModel):
    """Request model for query generation endpoint."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="ID of the database provider/connection",
    )
    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Natural language query",
    )
    conversation_id: Optional[UUID] = Field(
        default=None,
        description="Conversation ID for multi-turn dialogue",
    )
    options: QueryOptions = Field(
        default_factory=QueryOptions,
        description="Optional query processing parameters",
    )


class FeedbackRequest(BaseModel):
    """Request model for user feedback."""

    model_config = ConfigDict(extra="forbid")

    rating: int = Field(..., ge=1, le=5, description="User satisfaction rating (1-5)")
    is_query_correct: bool = Field(..., description="Whether the generated query is correct")
    corrected_query: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="User-provided correct query if original was wrong",
    )
    comments: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Additional feedback comments",
    )


class ExampleRequest(BaseModel):
    """Request model for adding RAG examples."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str = Field(..., min_length=1, max_length=100)
    natural_language_query: str = Field(..., min_length=1, max_length=5000)
    generated_query: str = Field(..., min_length=1, max_length=10000)
    is_good_example: bool = Field(..., description="True for positive, False for negative example")
    involved_tables: list[str] = Field(default_factory=list)
    query_intent: Optional[QueryIntent] = None
    complexity_level: Optional[ComplexityLevel] = None


class ReviewUpdateRequest(BaseModel):
    """Request model for expert review updates."""

    model_config = ConfigDict(extra="forbid")

    approved: bool = Field(..., description="Whether the query is approved")
    corrected_query: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Expert-corrected query if needed",
    )
    feedback: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Expert feedback/notes",
    )


# Response Models
class ValidationResult(BaseModel):
    """Query validation result."""

    model_config = ConfigDict(extra="allow")

    status: ValidationStatus
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    """Query execution result."""

    model_config = ConfigDict(extra="allow")

    success: bool
    row_count: Optional[int] = None
    data: Optional[list[dict[str, Any]]] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None


class AgentTrace(BaseModel):
    """Trace information for a single agent."""

    model_config = ConfigDict(extra="allow")

    agent_name: str
    latency_ms: int
    tokens_input: int
    tokens_output: int
    iterations: int = 1
    details: dict[str, Any] = Field(default_factory=dict)


class ReasoningTrace(BaseModel):
    """Complete reasoning trace for query processing."""

    model_config = ConfigDict(extra="allow")

    schema_agent: Optional[AgentTrace] = None
    rag_agent: Optional[AgentTrace] = None
    query_builder_agent: Optional[AgentTrace] = None
    validator_agent: Optional[AgentTrace] = None
    orchestrator_latency_ms: int
    total_tokens_input: int
    total_tokens_output: int
    total_cost_usd: float


class QueryResponse(BaseModel):
    """Response model for query generation endpoint."""

    model_config = ConfigDict(extra="allow")

    conversation_id: UUID = Field(..., description="Conversation identifier")
    turn_id: UUID = Field(..., description="Turn identifier within conversation")
    generated_query: str = Field(..., description="Generated database query")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the generated query",
    )
    validation_status: ValidationStatus = Field(..., description="Query validation status")
    validation_result: ValidationResult = Field(..., description="Detailed validation results")
    execution_result: Optional[ExecutionResult] = Field(
        default=None,
        description="Query execution result if execution was enabled",
    )
    reasoning_trace: Optional[ReasoningTrace] = Field(
        default=None,
        description="Reasoning trace if tracing was enabled",
    )
    needs_clarification: bool = Field(
        ...,
        description="Whether user clarification is needed",
    )
    clarification_questions: list[str] = Field(
        default_factory=list,
        description="Questions for user clarification",
    )
    iterations: int = Field(..., ge=1, description="Number of refinement iterations performed")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Provider Models
class TableInfo(BaseModel):
    """Database table information."""

    model_config = ConfigDict(extra="allow")

    name: str
    schema: Optional[str] = None
    columns: list[dict[str, Any]] = Field(default_factory=list)
    primary_keys: list[str] = Field(default_factory=list)
    foreign_keys: list[dict[str, Any]] = Field(default_factory=list)
    row_count: Optional[int] = None
    description: Optional[str] = None


class ProviderSchema(BaseModel):
    """Complete schema information for a provider."""

    model_config = ConfigDict(extra="allow")

    provider_id: str
    provider_type: str  # postgresql, athena, opensearch
    tables: list[TableInfo]
    metadata: dict[str, Any] = Field(default_factory=dict)
    last_refreshed: datetime


class ProviderInfo(BaseModel):
    """Provider connection information."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Provider identifier")
    name: str = Field(..., description="Human-readable provider name")
    type: str = Field(..., description="Provider type (postgresql, athena, opensearch)")
    description: Optional[str] = Field(default=None, description="Provider description")
    connection_status: str = Field(..., description="Connection status (connected, disconnected)")
    table_count: int = Field(..., ge=0, description="Number of tables/indexes")
    last_schema_refresh: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last schema refresh",
    )
    created_at: datetime
    updated_at: datetime


# Conversation Models
class ConversationTurnResponse(BaseModel):
    """Response model for a conversation turn."""

    model_config = ConfigDict(extra="allow")

    id: UUID
    turn_number: int
    user_input: str
    generated_query: str
    confidence_score: float
    validation_status: ValidationStatus
    created_at: datetime


class ConversationResponse(BaseModel):
    """Response model for conversation details."""

    model_config = ConfigDict(extra="allow")

    id: UUID
    provider_id: str
    status: ConversationStatus
    turn_count: int
    created_at: datetime
    updated_at: datetime
    turns: list[ConversationTurnResponse] = Field(default_factory=list)


# RAG Example Models
class RAGExampleResponse(BaseModel):
    """Response model for RAG examples."""

    model_config = ConfigDict(extra="allow")

    id: UUID
    provider_id: str
    natural_language_query: str
    generated_query: str
    is_good_example: bool
    status: ExampleStatus
    involved_tables: list[str]
    query_intent: Optional[str] = None
    complexity_level: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    expert_corrected_query: Optional[str] = None
    created_at: datetime


# Review Queue Models
class ReviewQueueItem(BaseModel):
    """Response model for review queue items."""

    model_config = ConfigDict(extra="allow")

    id: UUID
    conversation_id: UUID
    turn_id: UUID
    provider_id: str
    user_input: str
    generated_query: str
    confidence_score: float
    validation_status: ValidationStatus
    reason_for_review: str  # low_confidence, validation_failed, user_reported
    created_at: datetime
    priority: int = Field(default=0, description="Review priority (higher = more urgent)")


# Health Check
class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""

    model_config = ConfigDict(extra="allow")

    status: str = Field(..., description="Overall health status")
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Status of dependent services",
    )


# Error Response
class ErrorResponse(BaseModel):
    """Standard error response model."""

    model_config = ConfigDict(extra="allow")

    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional error details",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
