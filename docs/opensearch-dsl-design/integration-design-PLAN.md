# OpenSearch DSL Sample Retrieval - AgentCore Integration Plan

## Document Status: PLAN MODE - AWAITING APPROVAL

This document outlines the architecture and implementation plan for integrating OpenSearch DSL sample retrieval into the text2DSL AgentCore system.

---

## 1. Executive Summary

**Objective**: Enable AgentCore agents to seamlessly retrieve relevant DSL examples from OpenSearch during query processing to improve query generation accuracy through RAG (Retrieval-Augmented Generation).

**Key Integration Points**:
- QueryAgent during query generation phase
- RAGService as the abstraction layer
- OpenSearchService for vector similarity search
- Schema context enrichment with relevant examples

**Expected Benefits**:
- Improved query accuracy through example-based learning
- Reduced hallucination by grounding LLM in real examples
- Better handling of complex query patterns
- Learning from expert-corrected queries

---

## 2. Current System Analysis

### 2.1 AgentCore Architecture

**Key Files**:
- `/home/ubuntu/text2DSL-opensearch-design/src/text2x/agentcore/runtime.py` - AgentCore runtime
- `/home/ubuntu/text2DSL-opensearch-design/src/text2x/agentcore/agents/query/strands_agent.py` - QueryAgent implementation
- `/home/ubuntu/text2DSL-opensearch-design/src/text2x/agentcore/client.py` - Client wrapper

**QueryAgent Flow** (from strands_agent.py):
```
1. User sends natural language query via API
2. API route (query.py) creates/retrieves QueryAgent instance
3. QueryAgent.process() is called with:
   - user_message: NL query
   - provider_id: Database connection
   - schema_context: Tables and columns
   - enable_execution: Whether to run query
4. Agent uses Strands SDK with tools:
   - generate_sql_query / generate_mongo_query
   - execute_sql_query / execute_mongo_query
   - validate_sql_query / validate_mongo_query
   - explain_sql_query / explain_mongo_query
5. Returns response with generated query
```

**Critical Observations**:
- QueryAgent already receives `schema_context` dict in process()
- Agent has access to LLM via Strands SDK
- Tools are synchronous functions but use `_run_async()` for async operations
- System prompt is dynamically generated with schema info
- No RAG integration currently in QueryAgent

### 2.2 Existing RAG Infrastructure

**Key Files**:
- `/home/ubuntu/text2DSL-opensearch-design/src/text2x/services/rag_service.py` - RAG service layer
- `/home/ubuntu/text2DSL-opensearch-design/src/text2x/services/opensearch_service.py` - OpenSearch client
- `/home/ubuntu/text2DSL-opensearch-design/src/text2x/api/routes/rag.py` - RAG API endpoints

**RAGService.search_examples()** provides:
- Hybrid search (vector + keyword)
- Provider filtering
- Query intent filtering
- Sample query inclusion
- Similarity scoring
- Returns list of RAGExample objects

**Current Usage**:
- RAG API endpoint exists but is standalone
- NOT currently integrated into QueryAgent flow
- OpenSearch service initialized in app startup

### 2.3 API Entry Point

**File**: `/home/ubuntu/text2DSL-opensearch-design/src/text2x/api/routes/query.py`

**Current Flow** (lines 58-275):
```python
1. Receive QueryRequest
2. Get provider from database
3. Create/retrieve QueryAgent instance
4. Get schema context from provider
5. Call agent.process() with schema_context
6. Build QueryResponse from agent result
7. Return to client
```

**Key Insight**: Schema context is already being injected - we can add RAG examples in the same way.

---

## 3. Integration Design

### 3.1 When to Retrieve Examples

**Decision: At Query Planning Phase (Before LLM Call)**

**Rationale**:
1. ✅ Examples inform initial query generation
2. ✅ Reduces LLM iterations by providing good starting point
3. ✅ Caching is effective (same NL query = same examples)
4. ✅ Simpler architecture than mid-execution retrieval

**NOT During**:
- Validation phase: Too late, query already generated
- Execution phase: Examples don't help with execution
- Iterative refinement: Would need complex caching logic

**Trigger Point**: In `query.py` route handler, after schema context retrieval, before calling `agent.process()`

### 3.2 How to Present Results to Agents

**Decision: Inject Examples into System Prompt Context**

**Method**: Extend the `input_data` dict passed to `agent.process()` with a new key:

```python
agent_result = await agent.process({
    "user_message": request.query,
    "provider_id": request.provider_id,
    "schema_context": schema_context,        # Existing
    "rag_examples": rag_examples,             # NEW
    "enable_execution": enable_execution,
    "reset_conversation": not request.conversation_id,
})
```

**QueryAgent Modification**: Update system prompt generation to include examples:

```python
# In strands_agent.py, get_system_prompt() function
def get_system_prompt(schema_context: Dict[str, Any], query_language: str, rag_examples: List[Dict] = None) -> str:
    # ... existing prompt ...

    if rag_examples:
        examples_section = "\n\n**Relevant Example Queries:**\n\n"
        for i, ex in enumerate(rag_examples[:3], 1):  # Limit to top 3
            examples_section += f"Example {i} (similarity: {ex['score']:.2f}):\n"
            examples_section += f"Question: {ex['question']}\n"
            examples_section += f"Query: {ex['sql']}\n\n"

        # Inject before "Your responsibilities" section
        return base_prompt.replace(
            "**Your responsibilities:**",
            examples_section + "**Your responsibilities:**"
        )

    return base_prompt
```

**Alternative Rejected**: Tool-based retrieval
- ❌ Adds latency (LLM must decide to call tool)
- ❌ LLM might skip calling the tool
- ❌ More complex to implement
- ✅ Our approach: Proactive, always available, zero LLM round-trips

### 3.3 Caching Strategy

**Goal**: Avoid redundant OpenSearch queries for identical/similar NL inputs

**Decision: In-Memory LRU Cache with Redis Backup**

**Implementation Layers**:

1. **Application-Level Cache** (In RAGService):
   ```python
   from functools import lru_cache
   from hashlib import sha256

   class RAGService:
       def __init__(self, ...):
           self._search_cache = {}  # Dict[str, Tuple[List[RAGExample], float]]
           self._cache_ttl = 3600  # 1 hour

       def _cache_key(self, query: str, provider_id: str, query_intent: str) -> str:
           """Generate cache key from search parameters."""
           content = f"{query}:{provider_id}:{query_intent}"
           return sha256(content.encode()).hexdigest()

       async def search_examples(self, query: str, provider_id: str, ...):
           cache_key = self._cache_key(query, provider_id, query_intent)

           # Check cache
           if cache_key in self._search_cache:
               cached_results, cached_time = self._search_cache[cache_key]
               if time.time() - cached_time < self._cache_ttl:
                   logger.info(f"RAG cache hit: {cache_key[:8]}")
                   return cached_results

           # Cache miss - fetch from OpenSearch
           results = await self._search_opensearch(...)

           # Update cache
           self._search_cache[cache_key] = (results, time.time())

           return results
   ```

2. **Redis Cache** (Optional, for multi-instance deployments):
   ```python
   # Store serialized results in Redis with TTL
   cache_key = f"rag:examples:{hash(query)}:{provider_id}"
   cached = await redis_client.get(cache_key)
   if cached:
       return json.loads(cached)

   results = await opensearch_search(...)
   await redis_client.setex(cache_key, 3600, json.dumps(results))
   ```

**Cache Invalidation**:
- Time-based: TTL of 1 hour (configurable)
- Event-based: Clear cache when new examples approved
- Manual: Admin endpoint to flush cache

**Cache Metrics** (via Prometheus):
- `rag_cache_hits_total`
- `rag_cache_misses_total`
- `rag_cache_hit_rate`

### 3.4 Code Locations for Integration

**Files to Modify**:

1. **`src/text2x/api/routes/query.py`** (lines ~180-190)
   - Add RAG example retrieval before `agent.process()` call
   - Inject examples into input_data dict
   ```python
   # After schema_context retrieval (line ~178)

   # NEW: Retrieve RAG examples
   rag_examples = []
   if app_state.opensearch_client:
       try:
           rag_service = RAGService(
               opensearch_service=OpenSearchService(
                   settings=settings,
                   opensearch_client=app_state.opensearch_client
               )
           )
           raw_examples = await rag_service.search_examples(
               query=request.query,
               provider_id=request.provider_id,
               limit=3,
               min_similarity=0.6,
               include_sample_queries=True,
           )
           # Convert to dict format for agent
           rag_examples = [
               {
                   "question": ex.natural_language_query,
                   "sql": ex.get_query_for_rag() if hasattr(ex, 'get_query_for_rag') else ex.generated_query,
                   "score": getattr(ex, 'similarity_score', 0.0),
               }
               for ex in raw_examples
           ]
           logger.info(f"Retrieved {len(rag_examples)} RAG examples for query")
       except Exception as e:
           logger.warning(f"Failed to retrieve RAG examples: {e}")
           # Continue without examples - graceful degradation

   # Process query through QueryAgent
   agent_result = await agent.process({
       "user_message": request.query,
       "provider_id": request.provider_id,
       "schema_context": schema_context,
       "rag_examples": rag_examples,  # NEW
       "enable_execution": enable_execution,
       "reset_conversation": not request.conversation_id,
   })
   ```

2. **`src/text2x/agentcore/agents/query/strands_agent.py`**
   - Update `get_system_prompt()` signature (line 150)
   - Add examples section to prompt
   - Update `QueryAgent._update_agent()` to pass examples
   - Update `QueryAgent.process()` to extract and pass examples
   ```python
   # Line 150: Update signature
   def get_system_prompt(
       schema_context: Dict[str, Any],
       query_language: str,
       rag_examples: List[Dict] = None  # NEW
   ) -> str:
       # ... existing prompt generation ...

       # NEW: Add examples section
       if rag_examples:
           examples_text = "\n\n**📚 Relevant Example Queries:**\n\n"
           examples_text += "Use these similar queries as guidance, but adapt them to the user's specific question.\n\n"

           for i, ex in enumerate(rag_examples[:3], 1):
               examples_text += f"**Example {i}** (relevance: {ex['score']:.0%}):\n"
               examples_text += f"- Question: {ex['question']}\n"
               examples_text += f"- Query: {ex['sql']}\n\n"

           # Inject before responsibilities section
           prompt = prompt.replace(
               "**Your responsibilities:**",
               examples_text + "**Your responsibilities:**"
           )

       return prompt

   # Lines 823-862: Update process() method
   async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
       user_message = input_data["user_message"]
       provider_id = input_data.get("provider_id", "")
       schema_context = input_data.get("schema_context", {})
       rag_examples = input_data.get("rag_examples", [])  # NEW
       enable_execution = input_data.get("enable_execution", False)
       reset_conversation = input_data.get("reset_conversation", False)

       # Store examples for system prompt generation
       self._rag_examples = rag_examples  # NEW
       self._update_schema_context(schema_context)

       # ... rest of method ...

   # Lines 794-802: Update _update_agent()
   def _update_agent(self):
       tools = self._get_tools_for_language(self._query_language)
       self._agent = Agent(
           model=self._model,
           system_prompt=get_system_prompt(
               self._schema_context,
               self._query_language,
               getattr(self, '_rag_examples', [])  # NEW
           ),
           tools=tools,
           name=self.name,
           description=f"Query agent for {self._query_language}",
       )
   ```

3. **`src/text2x/services/rag_service.py`** (lines 158-200)
   - Add caching logic to `search_examples()` method
   - Add cache statistics tracking
   ```python
   class RAGService:
       def __init__(self, ...):
           # ... existing init ...
           self._search_cache: Dict[str, Tuple[List[RAGExample], float]] = {}
           self._cache_ttl = 3600  # 1 hour
           self._cache_hits = 0
           self._cache_misses = 0

       def _cache_key(self, query: str, provider_id: str, query_intent: Optional[str]) -> str:
           """Generate deterministic cache key."""
           content = f"{query}:{provider_id}:{query_intent or 'none'}"
           return hashlib.sha256(content.encode()).hexdigest()

       async def search_examples(self, query: str, provider_id: str, ...) -> List[RAGExample]:
           # Check cache first
           cache_key = self._cache_key(query, provider_id, query_intent)

           if cache_key in self._search_cache:
               cached_results, cached_time = self._search_cache[cache_key]
               if time.time() - cached_time < self._cache_ttl:
                   self._cache_hits += 1
                   logger.debug(f"RAG cache hit: {cache_key[:8]} (hits: {self._cache_hits})")
                   return cached_results
               else:
                   # Expired
                   del self._search_cache[cache_key]

           self._cache_misses += 1
           logger.debug(f"RAG cache miss: {cache_key[:8]} (misses: {self._cache_misses})")

           # ... existing search logic ...

           # Cache results
           self._search_cache[cache_key] = (examples, time.time())

           # Limit cache size (LRU-style)
           if len(self._search_cache) > 1000:
               # Remove oldest entries
               sorted_cache = sorted(
                   self._search_cache.items(),
                   key=lambda x: x[1][1]  # Sort by timestamp
               )
               for old_key, _ in sorted_cache[:100]:  # Remove oldest 100
                   del self._search_cache[old_key]

           return examples

       def get_cache_stats(self) -> Dict[str, Any]:
           """Return cache statistics."""
           total = self._cache_hits + self._cache_misses
           hit_rate = self._cache_hits / total if total > 0 else 0.0
           return {
               "hits": self._cache_hits,
               "misses": self._cache_misses,
               "hit_rate": hit_rate,
               "size": len(self._search_cache),
           }
   ```

4. **`src/text2x/utils/observability.py`** (NEW metrics)
   - Add RAG-specific metrics
   ```python
   # Add to existing metrics
   rag_examples_retrieved = Counter(
       "rag_examples_retrieved_total",
       "Total RAG examples retrieved",
       ["provider_type", "has_examples"]
   )

   rag_retrieval_latency = Histogram(
       "rag_retrieval_seconds",
       "RAG example retrieval latency",
       ["provider_type"]
   )

   rag_cache_operations = Counter(
       "rag_cache_operations_total",
       "RAG cache operations",
       ["operation"]  # hit, miss, eviction
   )

   def record_rag_retrieval(provider_type: str, count: int, latency: float):
       """Record RAG retrieval metrics."""
       rag_examples_retrieved.labels(
           provider_type=provider_type,
           has_examples=str(count > 0)
       ).inc()
       rag_retrieval_latency.labels(provider_type=provider_type).observe(latency)
   ```

**New Files to Create**:

None - all changes are modifications to existing files.

### 3.5 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                                     │
│  POST /query { "query": "Show active users", "provider_id": "..." }     │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│            API ROUTE: /src/text2x/api/routes/query.py                   │
│                                                                           │
│  1. Validate request                                                     │
│  2. Get provider from DB                                                 │
│  3. Get/create QueryAgent                                                │
│  4. Retrieve schema context ◄────────────┐                              │
│  5. **NEW** Retrieve RAG examples ◄──────┼──────────┐                   │
│  6. Call agent.process({                 │          │                   │
│       user_message,                      │          │                   │
│       schema_context,                    │          │                   │
│       rag_examples  ← NEW                │          │                   │
│     })                                   │          │                   │
└────────────────────────────────┬─────────┴──────────┴───────────────────┘
                                 │          ▲          ▲
                                 │          │          │
                     ┌───────────┼──────────┘          │
                     │           │                     │
                     │           │         ┌───────────┴──────────────┐
                     │           │         │   RAGService              │
                     │           │         │   (/services/rag_service) │
                     │           │         │                           │
                     │           │         │  1. Check cache           │
                     │           │         │  2. If miss:              │
                     │           │         │     - Call OpenSearch     │
                     │           │         │     - Cache results       │
                     │           │         │  3. Return examples       │
                     │           │         └───────────┬───────────────┘
                     │           │                     │
                     │           │                     ▼
                     │           │         ┌─────────────────────────┐
                     │           │         │  OpenSearchService      │
                     │           │         │                         │
                     │           │         │  - Vector similarity    │
                     │           │         │  - Keyword search       │
                     │           │         │  - Hybrid ranking       │
                     │           │         └─────────────────────────┘
                     │           │
                     │           └────► ProviderRepository
                     │                  (get schema)
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│         QueryAgent.process() (/agentcore/agents/query/strands_agent.py) │
│                                                                           │
│  1. Extract input: user_message, schema_context, **rag_examples**       │
│  2. Update system prompt with:                                           │
│     - Schema info (existing)                                             │
│     - **RAG examples (NEW)**                                             │
│  3. Create/update Strands Agent with enhanced prompt                     │
│  4. Invoke LLM with tools                                                │
│  5. LLM generates query (informed by examples in context)                │
│  6. Return response                                                      │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    API RESPONSE                                          │
│  {                                                                       │
│    "generated_query": "SELECT ...",                                      │
│    "confidence_score": 0.95,                                             │
│    "rag_examples_used": 3  ← NEW metric                                 │
│  }                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.6 Error Handling and Fallbacks

**Principle**: RAG retrieval failure should NOT block query generation

**Graceful Degradation**:

```python
# In query.py
rag_examples = []
try:
    if app_state.opensearch_client:
        rag_examples = await rag_service.search_examples(...)
        logger.info(f"Retrieved {len(rag_examples)} RAG examples")
except OpenSearchConnectionError as e:
    logger.warning(f"OpenSearch unavailable, proceeding without examples: {e}")
    # Record metric
    record_rag_retrieval_failure("opensearch_down")
except Exception as e:
    logger.error(f"RAG retrieval failed: {e}", exc_info=True)
    record_rag_retrieval_failure("unknown_error")

# Always proceed with agent call, even if rag_examples is empty
agent_result = await agent.process({
    "user_message": request.query,
    "schema_context": schema_context,
    "rag_examples": rag_examples,  # May be empty list
    ...
})
```

**Error Scenarios**:

| Scenario | Behavior | User Impact |
|----------|----------|-------------|
| OpenSearch down | Skip RAG, use schema only | Slightly lower accuracy |
| Embedding service down | Skip vector search, use keyword only | Reduced example quality |
| Cache corruption | Clear cache, fetch fresh | Temporary latency increase |
| Slow OpenSearch | Timeout after 2s, proceed | No blocking |
| No examples found | Continue with empty list | Same as before |

**Timeout Configuration**:
```python
# In OpenSearchService
async def search(self, query: str, timeout: float = 2.0):
    try:
        async with asyncio.timeout(timeout):
            return await self._execute_search(query)
    except asyncio.TimeoutError:
        logger.warning(f"OpenSearch search timed out after {timeout}s")
        return []  # Return empty results
```

### 3.7 Performance Considerations

**Latency Budget**:
- Total query processing: < 5s (existing)
- RAG retrieval: < 500ms (target)
- Breakdown:
  - Cache lookup: < 10ms
  - OpenSearch query: < 300ms
  - Result processing: < 50ms
  - Safety buffer: 140ms

**Optimization Strategies**:

1. **Parallel Execution** (Already in Design):
   ```python
   # In query.py - execute schema and RAG retrieval in parallel
   schema_task = asyncio.create_task(query_provider.get_schema())
   rag_task = asyncio.create_task(rag_service.search_examples(...))

   schema, rag_examples = await asyncio.gather(schema_task, rag_task)
   ```

2. **Result Limits**:
   - Retrieve top 5 from OpenSearch
   - Show top 3 to LLM (reduce prompt size)
   - Configurable via settings

3. **Connection Pooling**:
   - OpenSearch client uses connection pool (already configured)
   - Reuse client instance (stored in app_state)

4. **Prompt Size Management**:
   - Truncate long example queries (max 500 chars)
   - Omit metadata not needed by LLM
   - Format compactly

**Monitoring**:
```python
# Metrics to track
- rag_retrieval_latency_seconds (histogram)
- rag_cache_hit_rate (gauge)
- rag_examples_per_query (histogram)
- rag_opensearch_errors_total (counter)
```

---

## 4. Implementation Plan

### Phase 1: Core Integration (Week 1)

**Tasks**:
1. ✅ Modify `query.py` to retrieve RAG examples
2. ✅ Update `strands_agent.py` to accept and use examples
3. ✅ Add basic error handling and fallbacks
4. ✅ Add logging for debugging

**Acceptance Criteria**:
- QueryAgent receives RAG examples in process()
- System prompt includes examples
- Query generation works with and without examples
- No breaking changes to existing functionality

### Phase 2: Caching & Performance (Week 1)

**Tasks**:
1. ✅ Implement in-memory cache in RAGService
2. ✅ Add cache metrics and statistics
3. ✅ Implement cache invalidation logic
4. ✅ Add timeout handling for OpenSearch

**Acceptance Criteria**:
- Cache hit rate > 30% in typical usage
- RAG retrieval latency < 500ms (95th percentile)
- System handles OpenSearch downtime gracefully

### Phase 3: Observability & Tuning (Week 2)

**Tasks**:
1. ✅ Add Prometheus metrics for RAG operations
2. ✅ Create Grafana dashboard for RAG monitoring
3. ✅ Add detailed trace logging
4. ✅ Performance testing and optimization

**Acceptance Criteria**:
- All RAG operations emit metrics
- Dashboard shows cache hit rate, latency, errors
- Comprehensive logging for troubleshooting

### Phase 4: Testing & Documentation (Week 2)

**Tasks**:
1. ✅ Unit tests for RAG integration
2. ✅ Integration tests with mock OpenSearch
3. ✅ End-to-end tests with real queries
4. ✅ Update API documentation
5. ✅ Create integration guide

**Acceptance Criteria**:
- Test coverage > 80% for new code
- All edge cases covered (no examples, cache miss, etc.)
- Documentation complete and reviewed

---

## 5. Coordination with Other Teammates

### Schema Architect Dependencies

**Question**: Does the current index schema meet AgentCore needs?

**Required Fields** (from QueryAgent perspective):
- ✅ `question`: Natural language query
- ✅ `sql`: Generated query
- ✅ `difficulty`: Complexity level
- ⚠️  `involved_tables`: Not in current schema - NEED TO ADD
- ⚠️  `query_intent`: Not in current schema - NEED TO ADD
- ⚠️  `provider_type`: Not in current schema - NEED TO ADD

**Action Items for Schema Architect**:
1. Add `involved_tables` field (array of strings)
2. Add `query_intent` field (keyword: aggregation, filter, join, etc.)
3. Add `provider_type` field (keyword: postgres, mongodb, splunk)
4. Consider adding `query_language` field for multi-dialect support

### Query Patterns Analyst Dependencies

**Question**: How should RAGService API be called by AgentCore?

**Current API** (from rag_service.py):
```python
await rag_service.search_examples(
    query: str,
    provider_id: str,
    limit: int = 5,
    query_intent: Optional[str] = None,
    min_similarity: float = 0.7,
    include_sample_queries: bool = True,
) -> List[RAGExample]
```

**AgentCore Needs**:
- ✅ Simple async interface - SATISFIED
- ✅ Provider filtering - SATISFIED
- ✅ Result limiting - SATISFIED
- ⚠️  Need to convert RAGExample objects to dict format for prompt injection
- ⚠️  Need to handle multiple query languages (SQL vs MongoDB)

**Action Items for Query Patterns Analyst**:
1. Confirm min_similarity threshold (currently 0.7 in code, 0.5 in RAG API)
2. Define query_intent taxonomy (aggregation, filter, join, etc.)
3. Add method to RAGExample for clean dict serialization
4. Consider separate indices for different query languages

### Embeddings Expert Dependencies

**Question**: Any model hosting constraints we need to know about?

**Current Setup** (from OPENSEARCH_RAG_SETUP.md):
- Model: `amazon.titan-embed-text-v2:0`
- Dimensions: 1024
- Provider: AWS Bedrock
- Region: us-east-1

**AgentCore Needs**:
- ✅ Embeddings must be generated at query time - HANDLED BY RAGService
- ✅ Latency must be < 200ms - NEED TO VERIFY
- ⚠️  Need fallback if Bedrock unavailable - NOT IMPLEMENTED
- ⚠️  Multi-region support for global deployments - NOT IMPLEMENTED

**Action Items for Embeddings Expert**:
1. Confirm Bedrock latency SLA (target < 200ms for embedding generation)
2. Design fallback strategy if Bedrock unavailable (use keyword search only?)
3. Consider local embedding model for dev environments
4. Document any rate limits or quotas that affect caching strategy

---

## 6. Configuration

**New Environment Variables**:

```bash
# RAG Integration
RAG_ENABLED=true                      # Enable/disable RAG integration
RAG_EXAMPLES_LIMIT=5                  # Max examples to retrieve
RAG_EXAMPLES_IN_PROMPT=3              # Max examples to show in prompt
RAG_MIN_SIMILARITY=0.6                # Minimum similarity threshold
RAG_CACHE_TTL=3600                    # Cache TTL in seconds
RAG_CACHE_SIZE=1000                   # Max cache entries
RAG_TIMEOUT=2.0                       # OpenSearch timeout in seconds

# OpenSearch (existing)
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_INDEX=text2dsl-queries
```

**Settings Class Update** (`src/text2x/config.py`):
```python
class Settings(BaseSettings):
    # ... existing settings ...

    # RAG integration
    rag_enabled: bool = True
    rag_examples_limit: int = 5
    rag_examples_in_prompt: int = 3
    rag_min_similarity: float = 0.6
    rag_cache_ttl: int = 3600
    rag_cache_size: int = 1000
    rag_timeout: float = 2.0
```

---

## 7. Testing Strategy

### Unit Tests

**File**: `tests/unit/test_rag_integration.py`

```python
def test_query_route_retrieves_rag_examples():
    """Test that query route retrieves RAG examples."""
    # Mock RAGService.search_examples
    # Call query endpoint
    # Assert examples were retrieved and passed to agent

def test_query_agent_includes_examples_in_prompt():
    """Test that QueryAgent includes examples in system prompt."""
    # Create agent with examples
    # Assert system prompt contains example text

def test_graceful_degradation_on_rag_failure():
    """Test that query processing continues if RAG fails."""
    # Mock RAGService to raise exception
    # Call query endpoint
    # Assert query still processes successfully

def test_rag_cache_hit():
    """Test RAG cache returns cached results."""
    # Call search_examples twice with same query
    # Assert second call uses cache (no OpenSearch call)

def test_rag_cache_expiration():
    """Test RAG cache expires after TTL."""
    # Call search_examples
    # Wait for TTL to expire
    # Call again
    # Assert cache miss and fresh fetch
```

### Integration Tests

**File**: `tests/integration/test_rag_agentcore_integration.py`

```python
async def test_end_to_end_query_with_rag():
    """Test complete query flow with RAG examples."""
    # Setup: Index sample queries in test OpenSearch
    # Send query request
    # Assert response contains generated query
    # Assert metrics show RAG examples retrieved

async def test_query_accuracy_improves_with_examples():
    """Test that queries are more accurate with RAG examples."""
    # Create test cases with expected outputs
    # Run queries with RAG enabled
    # Run same queries with RAG disabled
    # Assert accuracy improvement
```

### Performance Tests

**File**: `tests/performance/test_rag_latency.py`

```python
def test_rag_retrieval_latency():
    """Test RAG retrieval meets latency targets."""
    # Warm up cache
    # Measure 100 queries
    # Assert p95 latency < 500ms
    # Assert p99 latency < 1000ms
```

---

## 8. Rollout Plan

### Stage 1: Feature Flag (Week 1)
- Deploy with `RAG_ENABLED=false` by default
- Enable for internal testing only
- Monitor for errors and performance issues

### Stage 2: Gradual Rollout (Week 2)
- Enable for 10% of requests (canary)
- Compare metrics: query accuracy, latency, error rate
- Increase to 50% if metrics are positive

### Stage 3: Full Rollout (Week 3)
- Enable for 100% of requests
- Monitor closely for first 48 hours
- Have rollback plan ready

### Rollback Criteria
- RAG retrieval error rate > 5%
- p95 latency increase > 20%
- Query accuracy decrease
- OpenSearch cluster issues

---

## 9. Success Metrics

**Primary Metrics**:
- Query accuracy: +10% improvement (measured via expert reviews)
- User satisfaction: +5% increase (measured via feedback)
- RAG cache hit rate: > 30%

**Secondary Metrics**:
- RAG retrieval latency: p95 < 500ms
- OpenSearch error rate: < 1%
- Examples used per query: avg 2-3

**Monitoring Dashboard** (Grafana):
- RAG retrieval latency over time
- Cache hit rate over time
- Examples retrieved per query (histogram)
- RAG errors and fallbacks
- Query accuracy correlation with RAG usage

---

## 10. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| OpenSearch downtime blocks queries | Medium | High | Graceful degradation, continue without examples |
| Cache poisoning with bad examples | Low | Medium | Cache only approved examples, TTL expiration |
| Latency increase degrades UX | Medium | Medium | Strict timeout, parallel execution, caching |
| Examples confuse LLM instead of helping | Low | High | Careful prompt engineering, limit to top 3 |
| Cache memory usage too high | Low | Low | LRU eviction, configurable size limit |

---

## 11. Future Enhancements

**Post-MVP Improvements**:

1. **Intelligent Example Selection**:
   - Use LLM to filter examples for relevance
   - Rank by complexity match (simple query = simple examples)

2. **Dynamic Example Weighting**:
   - Track which examples lead to successful queries
   - Boost high-performing examples in search results

3. **Multi-Turn Context**:
   - Retrieve examples based on conversation history
   - Learn user preferences over time

4. **Cross-Language Examples**:
   - Show MongoDB examples for SQL queries (and vice versa)
   - Help users learn multiple query languages

5. **Redis Distributed Cache**:
   - Share cache across multiple backend instances
   - Improve hit rate in scaled deployments

---

## 12. Open Questions

**For team-lead approval**:

1. ✅ **Approved approach**: Inject examples into system prompt (vs tool-based retrieval)?
2. ⚠️  **Cache strategy**: In-memory only, or add Redis for distributed cache?
3. ⚠️  **Example limit**: 3 examples in prompt, or configurable up to 5?
4. ⚠️  **Similarity threshold**: 0.6 default, or 0.7 (more conservative)?
5. ⚠️  **Fallback behavior**: Continue without examples, or return error?

**For Schema Architect**:
1. ⚠️  Need to add `involved_tables`, `query_intent`, `provider_type` fields?
2. ⚠️  Should we have separate indices per query language?

**For Query Patterns Analyst**:
1. ⚠️  Define query_intent taxonomy (aggregation, filter, join, etc.)?
2. ⚠️  Best format for serializing RAGExample to dict?

**For Embeddings Expert**:
1. ⚠️  Bedrock latency SLA for embedding generation?
2. ⚠️  Fallback strategy if Bedrock unavailable?

---

## 13. Summary

**Core Design Decision**: Proactive example injection into system prompt

**Integration Point**: API route layer, before calling agent.process()

**Data Flow**: Query → RAG retrieval (cached) → Examples in prompt → LLM generation

**Key Benefits**:
- ✅ Simple, non-invasive integration
- ✅ Graceful degradation if RAG fails
- ✅ Caching reduces latency and cost
- ✅ Observable and monitorable

**Next Steps**:
1. Get team-lead approval on plan
2. Coordinate with teammates on dependencies
3. Begin Phase 1 implementation
4. Iterate based on testing and feedback

---

## Document Metadata

- **Author**: Integration Engineer (Agent)
- **Created**: 2026-02-11
- **Status**: AWAITING APPROVAL
- **Dependencies**: Schema Architect, Query Patterns Analyst, Embeddings Expert
- **Estimated Effort**: 2-3 weeks
- **Risk Level**: Low (graceful degradation ensures safety)
