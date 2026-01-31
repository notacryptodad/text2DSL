"""Data models for Text2X system"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4


class ConversationStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ValidationStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"


class ExampleStatus(Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class ColumnInfo:
    name: str
    type: str
    nullable: bool = True
    default: Optional[Any] = None
    description: Optional[str] = None


@dataclass
class TableInfo:
    name: str
    columns: List[ColumnInfo]
    description: Optional[str] = None
    primary_keys: List[str] = field(default_factory=list)


@dataclass
class Relationship:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    relationship_type: str = "foreign_key"  # foreign_key, one_to_many, many_to_many


@dataclass
class JoinPath:
    tables: List[str]
    relationships: List[Relationship]
    suggested_join_clause: str


@dataclass
class SchemaContext:
    """Context passed from Schema Expert to Query Builder"""
    relevant_tables: List[TableInfo]
    relationships: List[Relationship]
    annotations: Dict[str, str]  # field -> annotation
    suggested_joins: List[JoinPath]
    provider_id: str
    query_language: str


@dataclass
class RAGExample:
    """Example query for RAG retrieval"""
    id: UUID
    provider_id: str
    natural_language_query: str
    generated_query: str
    is_good_example: bool
    status: ExampleStatus
    involved_tables: List[str] = field(default_factory=list)
    query_intent: str = ""
    complexity_level: str = "medium"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    expert_corrected_query: Optional[str] = None
    similarity_score: float = 0.0  # Set during retrieval


@dataclass
class ValidationResult:
    valid: bool
    validation_status: ValidationStatus
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    success: bool
    row_count: int = 0
    columns: List[str] = field(default_factory=list)
    sample_rows: List[Any] = field(default_factory=list)
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class QueryResult:
    """Complete result from Query Builder + Validator"""
    generated_query: str
    confidence_score: float
    validation_result: ValidationResult
    execution_result: Optional[ExecutionResult] = None
    iteration_count: int = 1
    reasoning_steps: List[str] = field(default_factory=list)
    examples_used: List[UUID] = field(default_factory=list)


@dataclass
class QueryResponse:
    """Response to user"""
    generated_query: str
    confidence_score: float
    validation_status: ValidationStatus
    execution_result: Optional[ExecutionResult]
    iterations: int
    clarification_needed: bool
    clarification_question: Optional[str] = None
    reasoning_trace: List[str] = field(default_factory=list)


@dataclass
class ReasoningTrace:
    """Detailed reasoning trace for debugging"""
    agent_name: str
    step: str
    timestamp: datetime
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    duration_ms: float


@dataclass
class ConversationTurn:
    id: UUID
    conversation_id: UUID
    turn_number: int
    user_input: str
    system_response: QueryResponse
    reasoning_trace: List[ReasoningTrace]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Conversation:
    id: UUID
    user_id: str
    provider_id: str
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    turns: List[ConversationTurn] = field(default_factory=list)
    
    def add_turn(self, user_input: str, response: QueryResponse, trace: List[ReasoningTrace]) -> ConversationTurn:
        turn = ConversationTurn(
            id=uuid4(),
            conversation_id=self.id,
            turn_number=len(self.turns) + 1,
            user_input=user_input,
            system_response=response,
            reasoning_trace=trace
        )
        self.turns.append(turn)
        self.updated_at = datetime.utcnow()
        return turn


@dataclass
class AgentState:
    """State maintained by an agent across iterations"""
    iteration: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_history(self, action: str, data: Any) -> None:
        self.history.append({
            "iteration": self.iteration,
            "action": action,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })
