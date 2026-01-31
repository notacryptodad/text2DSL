"""Text2X Python SDK - Client library for Text2DSL API."""

from .client import Text2XClient
from .models import (
    ComplexityLevel,
    ConversationResponse,
    ConversationStatus,
    ConversationTurnResponse,
    ErrorResponse,
    ExampleRequest,
    ExampleStatus,
    ExecutionResult,
    FeedbackRequest,
    ProviderInfo,
    ProviderSchema,
    QueryIntent,
    QueryOptions,
    QueryRequest,
    QueryResponse,
    RAGExampleResponse,
    ReviewQueueItem,
    ReviewUpdateRequest,
    TableInfo,
    TraceLevel,
    ValidationResult,
    ValidationStatus,
)
from .websocket import WebSocketClient

__version__ = "0.1.0"

__all__ = [
    # Main client
    "Text2XClient",
    "WebSocketClient",
    # Request models
    "QueryRequest",
    "QueryOptions",
    "FeedbackRequest",
    "ExampleRequest",
    "ReviewUpdateRequest",
    # Response models
    "QueryResponse",
    "ConversationResponse",
    "ConversationTurnResponse",
    "ProviderInfo",
    "ProviderSchema",
    "TableInfo",
    "ValidationResult",
    "ExecutionResult",
    "RAGExampleResponse",
    "ReviewQueueItem",
    "ErrorResponse",
    # Enums
    "TraceLevel",
    "ConversationStatus",
    "ValidationStatus",
    "ExampleStatus",
    "QueryIntent",
    "ComplexityLevel",
]
