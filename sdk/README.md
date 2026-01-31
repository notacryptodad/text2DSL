# Text2X Python SDK

The official Python client library for Text2DSL - an AI-powered system that converts natural language queries into executable database queries (SQL, NoSQL, Splunk SPL, etc.).

## Features

- **Async/Await Support**: Built on `httpx` and `websockets` for high-performance async operations
- **Type Safety**: Full type hints and Pydantic models for request/response validation
- **Streaming Support**: Real-time query processing via WebSocket streaming
- **Comprehensive API Coverage**: Support for all Text2X endpoints
- **Error Handling**: Detailed exception hierarchy for different error scenarios
- **Connection Pooling**: Built-in WebSocket connection pooling for concurrent operations

## Installation

```bash
pip install text2x-client
```

### Development Installation

```bash
git clone https://github.com/text2dsl/text2dsl.git
cd text2dsl/sdk
pip install -e ".[dev]"
```

## Quick Start

### Basic Usage

```python
import asyncio
from text2x_client import Text2XClient

async def main():
    async with Text2XClient("http://localhost:8000") as client:
        # Generate a query from natural language
        response = await client.query(
            provider_id="postgres_main",
            query="Show me all orders from last month with total greater than $1000"
        )

        print(f"Generated Query: {response.generated_query}")
        print(f"Confidence: {response.confidence_score:.2%}")

        if response.execution_result:
            print(f"Rows returned: {response.execution_result.row_count}")

asyncio.run(main())
```

### WebSocket Streaming

```python
import asyncio
from text2x_client import WebSocketClient

async def main():
    async with WebSocketClient("ws://localhost:8000") as ws_client:
        async for event in ws_client.query_stream(
            provider_id="postgres_main",
            query="Show me all orders from last month",
            trace_level="summary"
        ):
            if event.is_progress:
                print(f"Progress: {event.data}")
            elif event.is_clarification:
                print(f"Need clarification: {event.data['questions']}")
            elif event.is_result:
                print(f"Final query: {event.data['generated_query']}")
            elif event.is_error:
                print(f"Error: {event.data['message']}")
                break

asyncio.run(main())
```

## API Reference

### Text2XClient

The main HTTP client for interacting with the Text2X API.

#### Constructor

```python
client = Text2XClient(
    base_url: str,              # API base URL (e.g., "http://localhost:8000")
    api_key: Optional[str] = None,  # Optional API key for authentication
    timeout: float = 30.0,      # Request timeout in seconds
    max_retries: int = 3        # Maximum retry attempts
)
```

#### Methods

##### `query()`

Generate a database query from natural language.

```python
response = await client.query(
    provider_id: str,                    # Database provider ID
    query: str,                          # Natural language query
    conversation_id: Optional[UUID] = None,  # For multi-turn dialogue
    **options                            # Additional options
)

# Available options:
# - max_iterations: int (1-10)
# - confidence_threshold: float (0.0-1.0)
# - trace_level: "none" | "summary" | "full"
# - enable_execution: bool
# - rag_top_k: int (1-20)
```

**Returns:** `QueryResponse`

**Example:**

```python
response = await client.query(
    provider_id="postgres_main",
    query="Show me top 10 customers by total revenue",
    max_iterations=5,
    confidence_threshold=0.85,
    trace_level="summary",
    enable_execution=True
)

print(response.generated_query)
print(f"Confidence: {response.confidence_score}")
print(f"Iterations: {response.iterations}")

if response.reasoning_trace:
    print(f"Total tokens: {response.reasoning_trace.total_tokens_input}")
    print(f"Cost: ${response.reasoning_trace.total_cost_usd:.4f}")
```

##### `get_conversation()`

Retrieve conversation details and history.

```python
conversation = await client.get_conversation(conversation_id: UUID)
```

**Returns:** `ConversationResponse`

**Example:**

```python
conversation = await client.get_conversation(response.conversation_id)
print(f"Status: {conversation.status}")
print(f"Turns: {conversation.turn_count}")

for turn in conversation.turns:
    print(f"Turn {turn.turn_number}: {turn.user_input}")
    print(f"  Query: {turn.generated_query}")
    print(f"  Confidence: {turn.confidence_score}")
```

##### `submit_feedback()`

Submit user feedback for a conversation.

```python
await client.submit_feedback(
    conversation_id: UUID,
    rating: int,                        # 1-5
    is_query_correct: bool,
    corrected_query: Optional[str] = None,
    comments: Optional[str] = None
)
```

**Example:**

```python
await client.submit_feedback(
    conversation_id=response.conversation_id,
    rating=5,
    is_query_correct=True,
    comments="Perfect query, exactly what I needed!"
)
```

##### `list_providers()`

List all available database providers.

```python
providers = await client.list_providers()
```

**Returns:** `list[ProviderInfo]`

**Example:**

```python
providers = await client.list_providers()
for provider in providers:
    print(f"{provider.name} ({provider.type})")
    print(f"  Status: {provider.connection_status}")
    print(f"  Tables: {provider.table_count}")
```

##### `get_schema()`

Get schema information for a provider.

```python
schema = await client.get_schema(provider_id: str)
```

**Returns:** `ProviderSchema`

**Example:**

```python
schema = await client.get_schema("postgres_main")
print(f"Provider: {schema.provider_id} ({schema.provider_type})")
print(f"Tables: {len(schema.tables)}")

for table in schema.tables:
    print(f"\nTable: {table.name}")
    print(f"  Columns: {len(table.columns)}")
    print(f"  Primary Keys: {table.primary_keys}")

    for column in table.columns[:3]:  # First 3 columns
        print(f"    - {column['name']}: {column['type']}")
```

##### `refresh_schema()`

Trigger a schema refresh for a provider.

```python
result = await client.refresh_schema(provider_id: str)
```

**Example:**

```python
result = await client.refresh_schema("postgres_main")
print(result["message"])  # "Schema refresh initiated"
```

##### `get_review_queue()`

Get pending items from the expert review queue.

```python
queue = await client.get_review_queue(limit: int = 50)
```

**Returns:** `list[ReviewQueueItem]`

**Example:**

```python
queue = await client.get_review_queue(limit=10)
for item in queue:
    print(f"Priority: {item.priority}")
    print(f"Reason: {item.reason_for_review}")
    print(f"Query: {item.generated_query}")
    print(f"Confidence: {item.confidence_score}")
```

##### `submit_review()`

Submit an expert review for a queued item.

```python
await client.submit_review(
    review_id: UUID,
    approved: bool,
    corrected_query: Optional[str] = None,
    feedback: Optional[str] = None
)
```

**Example:**

```python
await client.submit_review(
    review_id=item.id,
    approved=True,
    feedback="Query is correct but could be optimized with an index"
)
```

##### `list_examples()`

List RAG examples from the knowledge base.

```python
examples = await client.list_examples(
    provider_id: Optional[str] = None,
    status: Optional[str] = None,  # "pending_review" | "approved" | "rejected"
    limit: int = 50
)
```

**Returns:** `list[RAGExampleResponse]`

**Example:**

```python
examples = await client.list_examples(
    provider_id="postgres_main",
    status="approved",
    limit=20
)

for example in examples:
    print(f"Question: {example.natural_language_query}")
    print(f"Query: {example.generated_query}")
    print(f"Tables: {example.involved_tables}")
```

##### `add_example()`

Add a new RAG example to the knowledge base.

```python
example = await client.add_example(
    provider_id: str,
    natural_language_query: str,
    generated_query: str,
    is_good_example: bool,
    involved_tables: Optional[list[str]] = None,
    query_intent: Optional[str] = None,
    complexity_level: Optional[str] = None
)
```

**Returns:** `RAGExampleResponse`

**Example:**

```python
example = await client.add_example(
    provider_id="postgres_main",
    natural_language_query="Show me recent orders",
    generated_query="SELECT * FROM orders ORDER BY created_at DESC LIMIT 10",
    is_good_example=True,
    involved_tables=["orders"],
    query_intent="filter",
    complexity_level="simple"
)

print(f"Example created with ID: {example.id}")
```

##### `health_check()`

Check API health status.

```python
health = await client.health_check()
```

**Example:**

```python
health = await client.health_check()
print(f"Status: {health['status']}")
print(f"Version: {health['version']}")

for service, info in health['services'].items():
    print(f"{service}: {info['status']}")
```

### WebSocketClient

Client for streaming query processing via WebSocket.

#### Constructor

```python
ws_client = WebSocketClient(
    base_url: str,              # WebSocket URL (e.g., "ws://localhost:8000")
    api_key: Optional[str] = None   # Optional API key
)
```

#### Methods

##### `query_stream()`

Stream query processing events in real-time.

```python
async for event in ws_client.query_stream(
    provider_id: str,
    query: str,
    conversation_id: Optional[UUID] = None,
    **options
):
    # Handle events
    pass
```

**Yields:** `StreamEvent` objects

**Event Types:**
- `progress`: Processing progress updates
- `clarification`: System needs user clarification
- `result`: Final query result
- `error`: Error occurred

**Example:**

```python
async with WebSocketClient("ws://localhost:8000") as ws_client:
    async for event in ws_client.query_stream(
        provider_id="postgres_main",
        query="Show me orders",
        trace_level="full"
    ):
        if event.is_progress:
            step = event.data.get("step")
            print(f"Step: {step}")

        elif event.is_clarification:
            questions = event.data.get("questions", [])
            print(f"Clarification needed: {questions}")
            # Handle clarification...

        elif event.is_result:
            print(f"Query: {event.data['generated_query']}")
            print(f"Confidence: {event.data['confidence_score']}")

            if event.trace:
                print(f"Trace: {event.trace}")

        elif event.is_error:
            print(f"Error: {event.data['message']}")
```

##### `query_stream_with_clarification()`

Stream query processing with automatic clarification handling.

```python
async def clarification_handler(questions: list[str]) -> str:
    # Handle clarification request
    print(f"Questions: {questions}")
    return "My answer"

result = await ws_client.query_stream_with_clarification(
    provider_id="postgres_main",
    query="Show me orders",
    clarification_callback=clarification_handler
)

if result.is_result:
    print(f"Final query: {result.data['generated_query']}")
```

### WebSocketManager

Connection pool manager for multiple concurrent WebSocket connections.

```python
manager = WebSocketManager(
    base_url: str,
    api_key: Optional[str] = None,
    pool_size: int = 5
)

async with manager.get_client() as client:
    async for event in client.query_stream(...):
        # Handle events
        pass

# Clean up
await manager.close_all()
```

## Models

### Enums

```python
from text2x_client import (
    TraceLevel,           # NONE, SUMMARY, FULL
    ConversationStatus,   # ACTIVE, COMPLETED, ABANDONED
    ValidationStatus,     # VALID, INVALID, WARNING, UNKNOWN
    ExampleStatus,        # PENDING_REVIEW, APPROVED, REJECTED
    QueryIntent,          # AGGREGATION, FILTER, JOIN, SEARCH, MIXED
    ComplexityLevel       # SIMPLE, MEDIUM, COMPLEX
)
```

### Response Models

All response models are Pydantic models with full type hints:

- `QueryResponse`: Main query generation response
- `ConversationResponse`: Conversation details with turns
- `ProviderInfo`: Provider connection information
- `ProviderSchema`: Complete schema information
- `ValidationResult`: Query validation details
- `ExecutionResult`: Query execution results
- `RAGExampleResponse`: RAG example details
- `ReviewQueueItem`: Review queue item

## Error Handling

The SDK provides a comprehensive exception hierarchy:

```python
from text2x_client.client import (
    Text2XError,              # Base exception
    Text2XAPIError,           # API returned an error
    Text2XConnectionError,    # Connection failed
    Text2XValidationError     # Request/response validation failed
)

from text2x_client.websocket import (
    WebSocketError,           # Base WebSocket exception
    WebSocketConnectionError, # WebSocket connection failed
    WebSocketMessageError     # Message parsing failed
)
```

**Example:**

```python
from text2x_client.client import Text2XAPIError, Text2XConnectionError

try:
    response = await client.query(
        provider_id="postgres_main",
        query="Show me orders"
    )
except Text2XAPIError as e:
    print(f"API Error: {e.error_response.error}")
    print(f"Message: {e.error_response.message}")
    if e.error_response.details:
        print(f"Details: {e.error_response.details}")
except Text2XConnectionError as e:
    print(f"Connection failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Advanced Examples

### Multi-turn Conversation

```python
async def multi_turn_conversation():
    async with Text2XClient("http://localhost:8000") as client:
        # First query
        response1 = await client.query(
            provider_id="postgres_main",
            query="Show me all customers"
        )

        conversation_id = response1.conversation_id

        # Follow-up query in same conversation
        response2 = await client.query(
            provider_id="postgres_main",
            query="Now filter to only active customers",
            conversation_id=conversation_id
        )

        # Another follow-up
        response3 = await client.query(
            provider_id="postgres_main",
            query="Sort by registration date",
            conversation_id=conversation_id
        )

        print(f"Final query: {response3.generated_query}")
```

### Concurrent Queries

```python
import asyncio

async def process_queries():
    async with Text2XClient("http://localhost:8000") as client:
        queries = [
            "Show me all orders",
            "Count active customers",
            "Get top 10 products by revenue"
        ]

        tasks = [
            client.query(provider_id="postgres_main", query=q)
            for q in queries
        ]

        results = await asyncio.gather(*tasks)

        for i, result in enumerate(results):
            print(f"\nQuery {i+1}: {queries[i]}")
            print(f"Generated: {result.generated_query}")
            print(f"Confidence: {result.confidence_score:.2%}")
```

### WebSocket with Connection Pool

```python
from text2x_client.websocket import WebSocketManager

async def concurrent_streaming():
    manager = WebSocketManager("ws://localhost:8000", pool_size=5)

    async def process_query(query: str):
        async with manager.get_client() as client:
            async for event in client.query_stream(
                provider_id="postgres_main",
                query=query
            ):
                if event.is_result:
                    return event.data["generated_query"]

    queries = [
        "Show me all orders",
        "Count customers",
        "Top products"
    ]

    tasks = [process_query(q) for q in queries]
    results = await asyncio.gather(*tasks)

    for query, result in zip(queries, results):
        print(f"{query} -> {result}")

    await manager.close_all()
```

### Custom Timeout and Retries

```python
async def with_custom_config():
    client = Text2XClient(
        base_url="http://localhost:8000",
        timeout=60.0,      # 60 second timeout
        max_retries=5      # Retry up to 5 times
    )

    async with client:
        response = await client.query(
            provider_id="postgres_main",
            query="Complex query that might take time",
            max_iterations=10
        )
```

## Configuration

### Environment Variables

You can configure the client using environment variables:

```bash
export TEXT2X_BASE_URL=http://localhost:8000
export TEXT2X_API_KEY=your-api-key-here
```

```python
import os
from text2x_client import Text2XClient

client = Text2XClient(
    base_url=os.getenv("TEXT2X_BASE_URL"),
    api_key=os.getenv("TEXT2X_API_KEY")
)
```

## Development

### Running Tests

```bash
pytest tests/
pytest tests/ -v --cov=text2x_client
```

### Type Checking

```bash
mypy text2x_client/
```

### Linting

```bash
ruff check text2x_client/
black text2x_client/
```

## Requirements

- Python 3.9+
- httpx >= 0.26.0
- websockets >= 12.0
- pydantic >= 2.5.0

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: https://text2dsl.readthedocs.io
- Issues: https://github.com/text2dsl/text2dsl/issues
- Email: support@text2dsl.com

## Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.
