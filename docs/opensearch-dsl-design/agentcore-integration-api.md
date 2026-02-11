# AgentCore Integration API Specification

## Overview

This document specifies the API contract between AgentCore QueryAgent and the RAG retrieval system for OpenSearch DSL sample integration.

---

## 1. RAG Service API

### search_examples()

Retrieve relevant DSL examples for query generation context.

**Signature**:
```python
async def search_examples(
    query: str,
    provider_id: str,
    limit: int = 5,
    query_intent: Optional[str] = None,
    min_similarity: float = 0.6,
    include_sample_queries: bool = True,
    provider_type: Optional[str] = None,
    involved_tables: Optional[List[str]] = None,
) -> List[RAGExample]
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | str | ✅ | - | Natural language query to search for |
| `provider_id` | str | ✅ | - | Provider UUID for filtering |
| `limit` | int | ❌ | 5 | Maximum number of examples to retrieve |
| `query_intent` | str | ❌ | None | Intent filter: `aggregation`, `filter`, `join`, `grouping`, `sorting`, `simple_select` |
| `min_similarity` | float | ❌ | 0.6 | Minimum cosine similarity threshold (0.0-1.0) |
| `include_sample_queries` | bool | ❌ | True | Include static sample queries from reference index |
| `provider_type` | str | ❌ | None | Provider type filter: `postgres`, `mongodb`, `splunk` |
| `involved_tables` | List[str] | ❌ | None | Filter by tables involved in examples |

**Returns**: `List[RAGExample]`

**RAGExample Structure**:
```python
@dataclass
class RAGExample:
    id: Optional[UUID]
    natural_language_query: str
    generated_query: str
    provider_id: str
    involved_tables: List[str]
    query_intent: str
    complexity_level: str  # simple, medium, complex
    is_good_example: bool
    similarity_score: float  # Set by search, 0.0-1.0
    metadata: Optional[Dict[str, Any]]

    def get_query_for_rag(self) -> str:
        """Return expert-corrected query if available, else generated query."""
        ...
```

**Example Usage**:
```python
# In query.py route handler
rag_service = RAGService(opensearch_service=opensearch_service)

try:
    examples = await rag_service.search_examples(
        query="Show all customers who made purchases last month",
        provider_id="550e8400-e29b-41d4-a716-446655440000",
        limit=5,
        query_intent="filter",
        min_similarity=0.6,
        include_sample_queries=True,
        provider_type="postgres",
        involved_tables=["customers", "orders"],
    )

    logger.info(f"Retrieved {len(examples)} RAG examples")

except Exception as e:
    logger.warning(f"RAG retrieval failed: {e}")
    examples = []  # Graceful degradation
```

**Error Handling**:
- `ValueError`: Invalid parameters (empty query, invalid provider_id)
- `TimeoutError`: OpenSearch query exceeded timeout (2s default)
- `OpenSearchConnectionError`: OpenSearch cluster unavailable
- All errors should be caught and logged, returning empty list for graceful degradation

---

## 2. QueryAgent Input Contract

### agent.process() Input

**Enhanced Input Data Structure**:
```python
input_data = {
    "user_message": str,              # Natural language query (existing)
    "provider_id": str,               # Provider UUID (existing)
    "schema_context": Dict[str, Any], # Schema metadata (existing)
    "rag_examples": List[Dict],       # NEW: RAG examples for prompt
    "enable_execution": bool,         # Query execution flag (existing)
    "reset_conversation": bool,       # Conversation reset flag (existing)
    "event_queue": Optional[Queue],   # SSE event queue (existing)
}
```

**New Field: `rag_examples`**

Format for each example dict:
```python
{
    "question": str,      # Natural language query
    "sql": str,           # Generated/corrected query
    "score": float,       # Similarity score (0.0-1.0)
    "intent": str,        # Query intent classification
    "tables": List[str],  # Involved tables
    "complexity": str,    # simple, medium, complex
}
```

**Example**:
```python
agent_result = await agent.process({
    "user_message": "Show all active customers",
    "provider_id": "550e8400-e29b-41d4-a716-446655440000",
    "schema_context": {
        "tables": [
            {
                "name": "customers",
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "status", "type": "varchar"},
                    {"name": "created_at", "type": "timestamp"},
                ]
            }
        ]
    },
    "rag_examples": [
        {
            "question": "Show all active users",
            "sql": "SELECT * FROM users WHERE status = 'active'",
            "score": 0.92,
            "intent": "filter",
            "tables": ["users"],
            "complexity": "simple",
        },
        {
            "question": "Get customers with active subscriptions",
            "sql": "SELECT c.* FROM customers c WHERE c.status = 'active'",
            "score": 0.87,
            "intent": "filter",
            "tables": ["customers"],
            "complexity": "simple",
        },
        {
            "question": "List all currently active accounts",
            "sql": "SELECT * FROM accounts WHERE active = true",
            "score": 0.84,
            "intent": "filter",
            "tables": ["accounts"],
            "complexity": "simple",
        },
    ],
    "enable_execution": True,
    "reset_conversation": False,
})
```

---

## 3. System Prompt Enhancement

### Prompt Injection Format

Examples are injected into the system prompt **before** the "Your responsibilities" section.

**Template**:
```
{base_system_prompt}

**📚 Relevant Example Queries:**

Use these similar queries as guidance, but adapt them to the user's specific question.

**Example 1** (relevance: 92%):
- Question: {question}
- Query: {sql}

**Example 2** (relevance: 87%):
- Question: {question}
- Query: {sql}

**Example 3** (relevance: 84%):
- Question: {question}
- Query: {sql}

**Your responsibilities:**
{rest_of_system_prompt}
```

**Implementation** (in `strands_agent.py`):
```python
def get_system_prompt(
    schema_context: Dict[str, Any],
    query_language: str,
    rag_examples: List[Dict] = None
) -> str:
    """Generate system prompt with optional RAG examples."""

    # Generate base prompt (existing logic)
    base_prompt = _generate_base_prompt(schema_context, query_language)

    # Inject examples if available
    if rag_examples and len(rag_examples) > 0:
        examples_section = "\n\n**📚 Relevant Example Queries:**\n\n"
        examples_section += "Use these similar queries as guidance, but adapt them to the user's specific question.\n\n"

        for i, ex in enumerate(rag_examples[:3], 1):  # Top 3 only
            relevance_pct = int(ex.get('score', 0) * 100)
            examples_section += f"**Example {i}** (relevance: {relevance_pct}%):\n"
            examples_section += f"- Question: {ex['question']}\n"
            examples_section += f"- Query: ```sql\n{ex['sql']}\n```\n\n"

        # Inject before responsibilities section
        base_prompt = base_prompt.replace(
            "**Your responsibilities:**",
            examples_section + "**Your responsibilities:**"
        )

    return base_prompt
```

**Constraints**:
- Maximum 3 examples shown (even if more retrieved)
- Truncate long queries to 500 characters
- Format with proper markdown for readability
- Show similarity score as percentage

---

## 4. Response Metadata

### Enhanced QueryResponse

Add RAG metadata to query response for observability:

```python
class QueryResponse(BaseModel):
    # ... existing fields ...

    # NEW: RAG metadata
    rag_examples_retrieved: int = 0
    rag_examples_shown: int = 0
    rag_cache_hit: bool = False
    rag_retrieval_time_ms: int = 0
```

**Example Response**:
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "turn_id": "660e8400-e29b-41d4-a716-446655440001",
  "generated_query": "SELECT * FROM customers WHERE status = 'active'",
  "confidence_score": 0.95,
  "validation_status": "valid",
  "rag_examples_retrieved": 5,
  "rag_examples_shown": 3,
  "rag_cache_hit": true,
  "rag_retrieval_time_ms": 45
}
```

---

## 5. Configuration

### Environment Variables

```bash
# RAG Integration
RAG_ENABLED=true                      # Master enable/disable
RAG_EXAMPLES_LIMIT=5                  # Max examples to retrieve from OpenSearch
RAG_EXAMPLES_IN_PROMPT=3              # Max examples to show in prompt
RAG_MIN_SIMILARITY=0.6                # Minimum cosine similarity threshold
RAG_CACHE_TTL=3600                    # Cache TTL in seconds (1 hour)
RAG_CACHE_SIZE=1000                   # Max cache entries (LRU eviction)
RAG_TIMEOUT=2.0                       # OpenSearch timeout in seconds
RAG_FALLBACK_TO_KEYWORD=true          # Use keyword search if vector fails
```

### Settings Class

```python
# In src/text2x/config.py
class Settings(BaseSettings):
    # ... existing settings ...

    # RAG integration
    rag_enabled: bool = Field(True, description="Enable RAG example retrieval")
    rag_examples_limit: int = Field(5, ge=1, le=10, description="Max examples to retrieve")
    rag_examples_in_prompt: int = Field(3, ge=1, le=5, description="Max examples in prompt")
    rag_min_similarity: float = Field(0.6, ge=0.0, le=1.0, description="Min similarity threshold")
    rag_cache_ttl: int = Field(3600, ge=0, description="Cache TTL in seconds")
    rag_cache_size: int = Field(1000, ge=100, description="Max cache entries")
    rag_timeout: float = Field(2.0, ge=0.1, description="OpenSearch timeout in seconds")
    rag_fallback_to_keyword: bool = Field(True, description="Fallback to keyword search")
```

---

## 6. Metrics & Observability

### Prometheus Metrics

```python
# In src/text2x/utils/observability.py

# RAG retrieval metrics
rag_examples_retrieved = Histogram(
    "rag_examples_retrieved",
    "Number of RAG examples retrieved per query",
    ["provider_type", "has_examples"],
    buckets=[0, 1, 2, 3, 5, 10],
)

rag_retrieval_latency = Histogram(
    "rag_retrieval_seconds",
    "RAG example retrieval latency",
    ["provider_type", "cache_hit"],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0],
)

rag_cache_operations = Counter(
    "rag_cache_operations_total",
    "RAG cache operations",
    ["operation"],  # hit, miss, eviction, invalidation
)

rag_search_errors = Counter(
    "rag_search_errors_total",
    "RAG search errors",
    ["error_type"],  # timeout, connection_error, opensearch_error
)

rag_similarity_scores = Histogram(
    "rag_similarity_scores",
    "Distribution of RAG example similarity scores",
    ["provider_type"],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0],
)
```

### Logging

**Structured Logging Format**:
```python
logger.info(
    "RAG examples retrieved",
    extra={
        "query_preview": query[:50],
        "provider_id": provider_id,
        "examples_retrieved": len(examples),
        "examples_shown": min(len(examples), 3),
        "cache_hit": cache_hit,
        "retrieval_time_ms": int(retrieval_time * 1000),
        "avg_similarity": sum(ex.similarity_score for ex in examples) / len(examples) if examples else 0,
    }
)
```

---

## 7. Error Scenarios & Handling

### Error Matrix

| Scenario | HTTP Code | Behavior | User Impact |
|----------|-----------|----------|-------------|
| RAG disabled via config | N/A | Skip retrieval, proceed with schema only | None (transparent) |
| OpenSearch unavailable | N/A | Log warning, proceed without examples | Slightly reduced accuracy |
| OpenSearch timeout | N/A | Log warning, return empty list | Slightly reduced accuracy |
| Invalid similarity threshold | 400 | Validation error in request | Request rejected |
| Embedding generation fails | N/A | Fallback to keyword search (if enabled) | Reduced example quality |
| Cache corruption | N/A | Clear cache, fetch fresh | Temporary latency increase |
| No examples found | N/A | Proceed with empty list | Same as before RAG |
| Example parsing error | N/A | Log error, skip malformed example | Fewer examples shown |

### Graceful Degradation Strategy

```python
# In query.py route handler
rag_examples = []
rag_metadata = {
    "retrieved": 0,
    "shown": 0,
    "cache_hit": False,
    "latency_ms": 0,
}

if settings.rag_enabled and app_state.opensearch_client:
    try:
        start = time.time()

        raw_examples = await asyncio.wait_for(
            rag_service.search_examples(
                query=request.query,
                provider_id=request.provider_id,
                limit=settings.rag_examples_limit,
                min_similarity=settings.rag_min_similarity,
            ),
            timeout=settings.rag_timeout,
        )

        rag_metadata["latency_ms"] = int((time.time() - start) * 1000)
        rag_metadata["retrieved"] = len(raw_examples)

        # Convert to prompt format
        rag_examples = [
            {
                "question": ex.natural_language_query,
                "sql": ex.get_query_for_rag(),
                "score": ex.similarity_score,
                "intent": ex.query_intent,
                "tables": ex.involved_tables,
                "complexity": ex.complexity_level,
            }
            for ex in raw_examples[:settings.rag_examples_in_prompt]
        ]

        rag_metadata["shown"] = len(rag_examples)

        logger.info(f"RAG retrieval successful: {rag_metadata}")

    except asyncio.TimeoutError:
        logger.warning(f"RAG retrieval timed out after {settings.rag_timeout}s")
        record_rag_error("timeout")

    except OpenSearchConnectionError as e:
        logger.warning(f"OpenSearch unavailable: {e}")
        record_rag_error("connection_error")

    except Exception as e:
        logger.error(f"RAG retrieval failed: {e}", exc_info=True)
        record_rag_error("unknown")

# ALWAYS proceed with agent call, even if rag_examples is empty
agent_result = await agent.process({
    "user_message": request.query,
    "schema_context": schema_context,
    "rag_examples": rag_examples,  # May be empty
    ...
})
```

---

## 8. Testing Contract

### Unit Test Interface

```python
# Test RAG service search
async def test_rag_search_returns_examples():
    service = RAGService(mock_opensearch)
    examples = await service.search_examples(
        query="Show active users",
        provider_id="test-provider",
        limit=5,
    )
    assert len(examples) <= 5
    assert all(ex.similarity_score >= 0.6 for ex in examples)

# Test prompt injection
def test_system_prompt_includes_examples():
    examples = [{"question": "...", "sql": "...", "score": 0.9}]
    prompt = get_system_prompt(schema_context, "SQL", examples)
    assert "Example 1" in prompt
    assert "relevance: 90%" in prompt

# Test graceful degradation
async def test_query_succeeds_without_rag():
    mock_rag_service.search_examples = Mock(side_effect=TimeoutError)
    response = await process_query(request)
    assert response.generated_query  # Query still generated
    assert response.rag_examples_retrieved == 0
```

---

## 9. Performance SLA

### Latency Targets

| Operation | Target (p50) | Target (p95) | Target (p99) | Timeout |
|-----------|--------------|--------------|--------------|---------|
| RAG retrieval (cache hit) | < 10ms | < 50ms | < 100ms | N/A |
| RAG retrieval (cache miss) | < 200ms | < 500ms | < 1000ms | 2000ms |
| Total query processing | < 2s | < 5s | < 8s | 30s |

### Throughput Targets

- Cache hit rate: > 30% after warmup
- OpenSearch queries/sec: > 100 (with caching)
- Memory overhead: < 50MB for 1000 cached entries

---

## 10. Migration & Rollout

### Feature Flag Strategy

```python
# Phase 1: Internal testing (RAG_ENABLED=false by default)
if settings.rag_enabled and request.headers.get("X-Enable-RAG") == "true":
    # Retrieve examples
    ...

# Phase 2: Canary (10% of requests)
if settings.rag_enabled and random.random() < 0.1:
    # Retrieve examples
    ...

# Phase 3: Full rollout (100%)
if settings.rag_enabled:
    # Retrieve examples
    ...
```

### Monitoring During Rollout

- Compare query accuracy: RAG-enabled vs RAG-disabled
- Monitor latency impact (target: < 20% increase)
- Track error rates
- Measure user satisfaction via feedback

### Rollback Criteria

- Error rate > 5%
- p95 latency increase > 50%
- Query accuracy decrease
- OpenSearch cluster health issues

---

## 11. API Change Summary

### New Parameters

**RAGService.search_examples()**:
- ✅ Already exists, no changes needed
- ⚠️ May need to add `provider_type` and `involved_tables` filters (pending schema updates)

**QueryAgent.process()**:
- ✅ Add `rag_examples: List[Dict]` to input_data
- ✅ Pass to `get_system_prompt()`

**QueryResponse**:
- ✅ Add `rag_examples_retrieved: int`
- ✅ Add `rag_examples_shown: int`
- ✅ Add `rag_cache_hit: bool`
- ✅ Add `rag_retrieval_time_ms: int`

### Backward Compatibility

All changes are backward compatible:
- New parameters have defaults
- Existing functionality unchanged when RAG disabled
- Response fields optional (can be omitted for legacy clients)

---

## Document Metadata

- **Author**: Integration Engineer
- **Created**: 2026-02-11
- **Status**: Implementation Ready
- **Dependencies**: Schema Architect (index fields), Query Patterns Analyst (search API), Embeddings Expert (latency SLA)
