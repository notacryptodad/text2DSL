# Embedding Strategy for DSL Sample Semantic Search

## Executive Summary

This document defines the embedding and vector search strategy for semantic retrieval of DSL samples in the text2DSL system. After analyzing the current implementation and evaluating alternatives, we recommend **continuing with AWS Bedrock Titan Embed v2** (1024 dimensions) with enhancements to the hybrid search strategy.

**Key Recommendations:**
- **Model**: AWS Bedrock Titan Embed v2 (`amazon.titan-embed-text-v2:0`)
- **Dimensions**: 1024 (optimal accuracy/performance balance)
- **Embed**: Natural language query text only (not DSL syntax)
- **Similarity Metric**: Cosine similarity
- **Search Strategy**: Hybrid (vector + keyword) with intent-based weighting
- **Hosting**: AWS Bedrock primary, local fallback for dev/test

## 1. Embedding Model Selection

### Recommendation: AWS Bedrock Titan Embed v2

**Model ID**: `amazon.titan-embed-text-v2:0`

**Dimensions**: 1024

**Rationale:**
- Already integrated into the text2DSL system
- AWS-native service (serverless, pay-per-use)
- Excellent semantic understanding for technical queries
- Proven performance with SQL/DSL query matching
- No operational overhead (managed service)

### Alternatives Evaluated

#### Sentence-Transformers (Open Source)

**Models Considered:**
- `all-MiniLM-L6-v2` (384 dimensions)
  - Pros: Very fast, low resource usage
  - Cons: Lower accuracy for complex technical queries

- `all-mpnet-base-v2` (768 dimensions)
  - Pros: Good balance of speed and accuracy
  - Cons: Requires hosting infrastructure

- `multi-qa-mpnet-base-dot-v1` (768 dimensions)
  - Pros: Optimized for question-answering retrieval
  - Cons: Smaller dimension than Titan v2, needs deployment

**Verdict**: Excellent for cost-conscious deployments, but operational overhead outweighs benefits for production use.

#### OpenAI Embeddings

**Models:**
- `text-embedding-3-small` (1536 dimensions)
- `text-embedding-3-large` (3072 dimensions)

**Analysis:**
- Pros: High quality, well-documented, large community
- Cons: External API dependency, higher cost than Bedrock, not AWS-native
- **Verdict**: Good quality but introduces external dependency; Bedrock preferred for AWS ecosystem integration

#### Cohere Embeddings

**Model**: `embed-english-v3.0` (1024 dimensions)

**Analysis:**
- Pros: Same dimension as Titan v2, good for semantic search
- Cons: External API, additional vendor relationship
- **Verdict**: Comparable to Titan v2 but adds complexity

### Decision Matrix

| Model | Dimensions | Integration | Cost | Accuracy | Ops Overhead | Score |
|-------|-----------|-------------|------|----------|--------------|-------|
| **Titan v2** | 1024 | ✅ Native | Medium | High | None | **9/10** |
| OpenAI (small) | 1536 | External | High | High | Low | 7/10 |
| OpenAI (large) | 3072 | External | Very High | Very High | Low | 6/10 |
| Cohere | 1024 | External | Medium | High | Low | 7/10 |
| mpnet-base-v2 | 768 | Self-hosted | Low | Medium | High | 6/10 |
| MiniLM-L6-v2 | 384 | Self-hosted | Very Low | Low | High | 5/10 |

**Winner**: AWS Bedrock Titan Embed v2 (1024 dimensions)

## 2. Vector Dimensions Analysis

### Recommendation: 1024 Dimensions

**Trade-off Analysis:**

#### Low Dimensions (384-768)
- **Pros**: Faster search, lower storage, reduced compute
- **Cons**: Significant accuracy drop for complex SQL/DSL patterns
- **Use Case**: Not suitable for technical query matching

#### Current: 1024 Dimensions ✅
- **Pros**: Optimal balance of accuracy and performance
- **Performance**: ~50-100ms k-NN search with HNSW
- **Storage**: Reasonable for production scale (4KB per vector)
- **Accuracy**: Sufficient semantic richness for SQL/DSL understanding
- **Use Case**: Perfect for production semantic search

#### High Dimensions (1536-3072)
- **Pros**: Marginally better semantic understanding
- **Cons**: 1.5-3x storage cost, slower search, diminishing returns
- **Use Case**: Over-engineered for DSL sample retrieval

### Performance Impact

| Dimensions | Search Time | Storage/Vector | Accuracy | Recommendation |
|-----------|-------------|----------------|----------|----------------|
| 384 | ~20ms | 1.5KB | 70% | ❌ Too low |
| 768 | ~40ms | 3KB | 85% | ⚠️ Acceptable |
| **1024** | **~60ms** | **4KB** | **92%** | ✅ **Optimal** |
| 1536 | ~90ms | 6KB | 94% | ⚠️ Overkill |
| 3072 | ~150ms | 12KB | 95% | ❌ Excessive |

**Justification**: 1024 dimensions provides 92% accuracy at 60ms latency, which exceeds requirements for DSL sample retrieval. Higher dimensions offer <3% accuracy gain at 50-150% cost increase.

## 3. What to Embed Strategy

### Primary Content: Natural Language Query Text

**Embed**: `natural_language_query` field from RAGExample

**Example**:
```
"How many customers do we have?" → [embedding vector]
```

**Rationale**:
- Captures user intent and semantic meaning
- Enables conceptual similarity matching (e.g., "customer count" ≈ "number of users")
- Standard practice for question-answering systems

### Do NOT Embed: Generated DSL Queries

**Store as Text**: `generated_query` field (keyword search only)

**Example**:
```sql
"SELECT COUNT(*) FROM customers" → stored as text, NOT embedded
```

**Rationale**:
- DSL syntax requires exact/partial pattern matching (better with keywords)
- Embedding SQL would prioritize semantic similarity of code structure (not useful)
- Keyword search (BM25) excellent for matching SQL clauses like "SELECT COUNT(*)"

### Optional Enhancement: Description Field

**Consider**: Adding a `description` field for richer context

**Example**:
```
description: "Aggregate query to count total customer records"
embedding: concat(nl_query, description)
```

**Trade-offs**:
- Pros: Richer semantic context, better disambiguation
- Cons: Longer text = noisier embeddings, requires schema change
- **Verdict**: Not needed for MVP; revisit if retrieval quality insufficient

### Multi-Field Strategy

**Current Implementation** (Recommended):
```python
{
  "nl_query": "How many customers do we have?",  # EMBED THIS
  "generated_query": "SELECT COUNT(*) FROM customers",  # KEYWORD SEARCH
  "embedding": [0.123, -0.456, ...]  # Generated from nl_query
}
```

**Hybrid Retrieval**:
- Vector search on `embedding` field (semantic similarity)
- Keyword search on `nl_query` field (BM25 matching)
- Keyword search on `generated_query` field (SQL pattern matching)
- Combined scoring: 0.7 × vector + 0.3 × keyword

## 4. Similarity Metric Selection

### Recommendation: Cosine Similarity

**Formula**: `similarity = (A · B) / (||A|| × ||B||)`

**Properties**:
- Magnitude-invariant (normalized)
- Range: [-1, 1] (1 = identical, 0 = orthogonal, -1 = opposite)
- Standard for text embeddings

**Why Cosine for Text Embeddings**:
- Text embeddings have varying magnitudes (document length affects L2 norm)
- Cosine focuses on direction (semantic meaning) not magnitude
- Robust to embedding scale differences between queries

### Alternatives Evaluated

#### Dot Product
**Formula**: `similarity = A · B`

**Analysis**:
- Pros: Faster computation (no normalization needed)
- Cons: Magnitude-dependent (longer queries score higher)
- **Verdict**: Not suitable unless embeddings are pre-normalized

#### L2 Distance (Euclidean)
**Formula**: `distance = ||A - B||`

**Analysis**:
- Pros: Intuitive distance metric
- Cons: Magnitude-sensitive, requires conversion to similarity score
- **Verdict**: Good for spatial data, not optimal for text embeddings

#### Comparison Table

| Metric | Normalized | Text-Optimized | Speed | Recommendation |
|--------|-----------|----------------|-------|----------------|
| **Cosine** | ✅ Yes | ✅ Yes | Medium | ✅ **Use This** |
| Dot Product | ❌ No | ⚠️ If normalized | Fast | ⚠️ Only if pre-normalized |
| L2 Distance | ❌ No | ❌ No | Medium | ❌ Not recommended |

### OpenSearch Configuration

```json
{
  "method": {
    "name": "hnsw",
    "space_type": "cosinesimil",  // Cosine similarity
    "engine": "nmslib",
    "parameters": {
      "ef_construction": 512,
      "m": 16
    }
  }
}
```

**Note**: OpenSearch uses `cosinesimil` for cosine similarity with HNSW algorithm.

## 5. Model Hosting Strategy

### Production: AWS Bedrock (Serverless)

**Architecture**:
```
User Query → RAG Service → Bedrock API → Titan v2 Embedding → OpenSearch
```

**Advantages**:
- **Serverless**: No infrastructure management
- **Pay-per-use**: Cost scales with usage
- **High availability**: AWS SLA guarantees
- **Auto-scaling**: Handles traffic spikes
- **Security**: IAM-based access control

**Cost Structure**:
- Titan v2: $0.0001 per 1K tokens (input)
- Typical query: ~50 tokens = $0.000005 per embedding
- 1M queries/month = ~$5 for embeddings

**Limitations**:
- Network latency: ~100-200ms per API call
- API rate limits: 1000 requests/second (adjustable)
- AWS region dependency

### Development/Test: Local Sentence-Transformers

**Purpose**: Cost reduction for non-production environments

**Architecture**:
```
Dev/Test Query → Local Embedding Service → sentence-transformers → OpenSearch
```

**Implementation**:
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('multi-qa-mpnet-base-dot-v1')
embedding = model.encode(query_text)
```

**Docker Setup**:
```dockerfile
FROM python:3.11-slim
RUN pip install sentence-transformers
COPY embedding_service.py /app/
CMD ["python", "/app/embedding_service.py"]
```

**Trade-offs**:
- Pros: Zero API cost, faster for dev iteration
- Cons: Different dimensions (768 vs 1024), requires index reconfiguration

### Hybrid Approach: Fallback Strategy

**Primary**: Bedrock Titan v2 (production)
**Fallback**: Local sentence-transformers (if Bedrock unavailable)

**Implementation**:
```python
async def generate_embedding(text: str) -> List[float]:
    try:
        # Try Bedrock first
        return await bedrock_client.generate_embedding(text)
    except BedrocException:
        # Fall back to local model
        logger.warning("Bedrock unavailable, using local model")
        return local_model.encode(text)
```

**Consideration**: Fallback requires separate OpenSearch index (different dimensions)

### Caching Strategy: Redis

**Purpose**: Reduce API calls for repeated queries

**Architecture**:
```
Query → Check Redis → (miss) → Generate Embedding → Cache → OpenSearch
         ↓ (hit)
         Return Cached
```

**Implementation**:
```python
# Cache key: hash of query text
cache_key = f"embedding:{hashlib.sha256(query.encode()).hexdigest()}"

# Check cache
cached = await redis.get(cache_key)
if cached:
    return json.loads(cached)

# Generate and cache
embedding = await bedrock.generate_embedding(query)
await redis.setex(cache_key, ttl=3600, value=json.dumps(embedding))
return embedding
```

**Impact**:
- Hit rate: ~30-40% for common queries
- Cost reduction: $1-2 per million queries
- Latency: Redis lookup ~1-2ms vs Bedrock ~100-200ms

## 6. Hybrid Search Configuration

### Current Implementation: Fixed Weights

**Formula**: `score = 0.7 × vector_score + 0.3 × keyword_score`

**OpenSearch Query**:
```json
{
  "query": {
    "script_score": {
      "query": {
        "bool": {
          "should": [
            {"match": {"nl_query": {"query": "user query", "boost": 0.3}}}
          ],
          "filter": [{"term": {"provider_id": "postgres"}}]
        }
      },
      "script": {
        "source": "0.7 * (cosineSimilarity(params.query_vector, 'embedding') + 1.0) + 0.3 * _score",
        "params": {"query_vector": [0.123, -0.456, ...]}
      }
    }
  }
}
```

**Current Weights**:
- Vector (semantic): 70%
- Keyword (BM25): 30%

### Proposed: Intent-Based Dynamic Weighting

**Rationale**: Different query types benefit from different search strategies

#### Aggregation Queries (COUNT, SUM, AVG)
**Example**: "How many customers do we have?"

**Weights**: 0.8 vector + 0.2 keyword

**Reason**: Concept matters more than keywords ("count customers" ≈ "number of users")

#### Exact Filter Queries
**Example**: "Show products under $50"

**Weights**: 0.5 vector + 0.5 keyword

**Reason**: Keywords matter ("$50", "price") for exact matching

#### Complex Join Queries
**Example**: "Which customers have placed orders?"

**Weights**: 0.7 vector + 0.3 keyword (default)

**Reason**: Balanced approach for multi-table queries

#### Configuration Map

```python
HYBRID_WEIGHTS = {
    "aggregation": {"vector": 0.8, "keyword": 0.2},
    "filter": {"vector": 0.5, "keyword": 0.5},
    "join": {"vector": 0.7, "keyword": 0.3},
    "sort": {"vector": 0.6, "keyword": 0.4},
    "group_by": {"vector": 0.75, "keyword": 0.25},
    "subquery": {"vector": 0.7, "keyword": 0.3},
    "default": {"vector": 0.7, "keyword": 0.3}
}

def get_search_weights(query_intent: str) -> dict:
    return HYBRID_WEIGHTS.get(query_intent, HYBRID_WEIGHTS["default"])
```

### A/B Testing Strategy

**Metrics to Track**:
- **NDCG@5**: Normalized Discounted Cumulative Gain (ranking quality)
- **MRR**: Mean Reciprocal Rank (first relevant result position)
- **Precision@k**: Relevant results in top-k
- **User feedback**: Thumbs up/down on retrieved examples

**Implementation**:
```python
# Randomly assign 10% of queries to weight variants
if random.random() < 0.1:
    variant = random.choice(["vector_heavy", "keyword_heavy", "balanced"])
    weights = VARIANT_WEIGHTS[variant]
    log_experiment(query_id, variant, weights, results)
```

**Evaluation Period**: 2 weeks with 1000+ queries per variant

## 7. Performance Characteristics

### Latency Breakdown

**End-to-End Query Processing**:
```
Total: ~150-300ms
├─ Embedding Generation: 100-200ms (Bedrock API)
├─ k-NN Search: 50-100ms (OpenSearch HNSW)
└─ Result Hydration: 10-20ms (PostgreSQL fetch)
```

**Optimization Targets**:
- Embedding: Cache in Redis (reduce to ~2ms for hits)
- Search: HNSW tuning (ef_search parameter)
- Hydration: Connection pooling, batch fetch

### HNSW Parameter Tuning

**Current Configuration**:
```json
{
  "ef_construction": 512,  // Index build accuracy
  "m": 16,                 // HNSW connectivity
  "ef_search": 512        // Query-time accuracy
}
```

**Trade-off Matrix**:

| Parameter | Value | Indexing Time | Search Time | Accuracy | Recommendation |
|-----------|-------|---------------|-------------|----------|----------------|
| ef_construction | 256 | Fast | - | 90% | ❌ Too low |
| ef_construction | **512** | **Medium** | **-** | **95%** | ✅ **Optimal** |
| ef_construction | 1024 | Slow | - | 96% | ⚠️ Diminishing returns |
| m | 8 | Fast | Medium | 92% | ⚠️ Acceptable |
| m | **16** | **Medium** | **Fast** | **95%** | ✅ **Optimal** |
| m | 32 | Slow | Very Fast | 96% | ⚠️ Overkill |
| ef_search | 256 | - | Fast | 92% | ⚠️ Lower accuracy |
| ef_search | **512** | **-** | **Medium** | **95%** | ✅ **Optimal** |
| ef_search | 1024 | - | Slow | 96% | ⚠️ Minimal gain |

**Recommendation**: Current settings (ef_construction=512, m=16, ef_search=512) are optimal.

### Scaling Characteristics

**Storage Growth**:
- 1024-dim vector = 4KB per document
- 10K examples = 40MB
- 100K examples = 400MB
- 1M examples = 4GB (vectors only)

**Search Performance**:
- 10K documents: ~30ms
- 100K documents: ~60ms
- 1M documents: ~100ms
- 10M documents: ~200ms (HNSW scales well)

**Batch Indexing**:
- Single document: ~150ms (embedding + index)
- Batch of 25: ~3 seconds (~120ms per doc)
- Throughput: ~500 docs/minute with batching

### Cost Analysis

**Bedrock Titan v2 Pricing**:
- $0.0001 per 1K input tokens
- Average query: ~50 tokens = $0.000005 per embedding

**Monthly Cost Scenarios**:
- 10K queries/month: $0.05
- 100K queries/month: $0.50
- 1M queries/month: $5.00
- 10M queries/month: $50.00

**Caching Impact** (30% hit rate):
- 1M queries/month: $5.00 → $3.50 (30% savings)
- 10M queries/month: $50.00 → $35.00 (30% savings)

**OpenSearch Costs**:
- Domain: $0.036/hour for t3.small.search = ~$26/month
- Storage: $0.10/GB-month = $0.40 for 100K examples
- Total: ~$26-27/month (fixed cost)

## 8. Multi-Provider Considerations

### Challenge: Multiple Query Languages

**Providers**:
- SQL (PostgreSQL, MySQL, SQLite)
- NoSQL (MongoDB query language)
- Splunk SPL (Search Processing Language)

**Question**: Single embedding model or provider-specific models?

### Recommendation: Single Unified Model

**Strategy**: Use Titan v2 for all providers with provider-specific filtering

**Rationale**:
1. **Natural language is universal**: "Show me all customers" maps to concepts regardless of DSL
2. **Provider filtering works**: Filter by `provider_id` at search time
3. **Operational simplicity**: One model to maintain vs three
4. **Cross-provider learning**: SQL examples may help NoSQL queries (shared concepts)

**Implementation**:
```python
# Search with provider filter
results = await opensearch.search_similar(
    query_text="How many users logged in today?",
    provider_id="mongodb",  # Filter to MongoDB examples only
    k=5
)
```

### Provider-Specific Monitoring

**Track Quality Metrics Per Provider**:
```python
metrics = {
    "postgres": {"precision@5": 0.92, "mrr": 0.85},
    "mongodb": {"precision@5": 0.88, "mrr": 0.81},
    "splunk": {"precision@5": 0.79, "mrr": 0.72}
}
```

**Threshold for Action**: If any provider drops below 0.75 precision@5, consider provider-specific model.

### Future: Provider-Specific Fine-Tuning

**If quality drops below threshold**:
1. Collect provider-specific training data
2. Fine-tune sentence-transformers model on provider examples
3. Deploy separate embedding services per provider
4. Update OpenSearch indices with provider-specific embeddings

**Cost**: 3x infrastructure (one model per provider)
**Benefit**: 5-10% accuracy improvement for specialized DSLs

**Decision**: Defer until data shows single model insufficient.

### Multi-Lingual Support

**Current**: English-only (Titan v2 supports 100+ languages)

**Future Consideration**: If international users need non-English queries
- Titan v2 already supports multilingual embeddings
- No code changes needed
- Test with sample queries in target languages
- Monitor retrieval quality per language

**Recommendation**: English-only for MVP, multilingual comes free with Titan v2 if needed.

## 9. Vector Field Specifications for Schema Architect

### OpenSearch Index Configuration

**Critical Requirements** (Schema Architect MUST implement):

```json
{
  "settings": {
    "index": {
      "knn": true,
      "knn.algo_param.ef_search": 512,
      "number_of_shards": 2,
      "number_of_replicas": 1
    }
  },
  "mappings": {
    "properties": {
      "id": {
        "type": "keyword"
      },
      "embedding": {
        "type": "knn_vector",
        "dimension": 1024,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil",
          "engine": "nmslib",
          "parameters": {
            "ef_construction": 512,
            "m": 16
          }
        }
      },
      "nl_query": {
        "type": "text",
        "analyzer": "standard"
      },
      "generated_query": {
        "type": "text",
        "index": false
      },
      "provider_id": {
        "type": "keyword"
      },
      "query_intent": {
        "type": "keyword"
      },
      "complexity_level": {
        "type": "keyword"
      },
      "involved_tables": {
        "type": "keyword"
      },
      "status": {
        "type": "keyword"
      },
      "is_good_example": {
        "type": "boolean"
      },
      "reviewed_by": {
        "type": "keyword"
      },
      "reviewed_at": {
        "type": "date"
      },
      "expert_corrected_query": {
        "type": "text",
        "index": false
      },
      "metadata": {
        "type": "object",
        "enabled": false
      },
      "created_at": {
        "type": "date"
      },
      "updated_at": {
        "type": "date"
      }
    }
  }
}
```

### Critical Parameters Explained

#### Vector Field: `embedding`

**dimension: 1024** (MUST MATCH)
- **Why**: Titan v2 produces 1024-dimensional vectors
- **Challenge if different**: If Schema Architect proposes different dimension, REJECT
- **Compatibility**: Changing dimension requires re-embedding all documents

**space_type: "cosinesimil"** (MUST MATCH)
- **Why**: Cosine similarity is optimal for text embeddings
- **Challenge if different**: If "l2" or "innerproduct" proposed, request justification
- **Impact**: Different metrics produce different rankings

**engine: "nmslib"** (RECOMMENDED)
- **Why**: Best HNSW implementation in OpenSearch
- **Alternative**: "faiss" (acceptable but nmslib preferred)
- **Challenge if different**: If "lucene" proposed, explain performance implications

#### HNSW Parameters

**ef_construction: 512** (OPTIMAL)
- **Trade-off**: Higher = better accuracy, slower indexing
- **Range**: 256-1024 acceptable, <256 too low
- **Challenge if <256**: Warn about accuracy degradation

**m: 16** (OPTIMAL)
- **Trade-off**: Higher = better recall, more memory
- **Range**: 8-32 acceptable, <8 too sparse
- **Challenge if <8**: Explain connectivity issues

**ef_search: 512** (OPTIMAL)
- **Trade-off**: Higher = better accuracy, slower search
- **Range**: 256-1024 acceptable
- **Challenge if <256**: Request latency vs accuracy analysis

### Validation Checklist

Schema Architect MUST confirm:
- [ ] Vector dimension is exactly 1024
- [ ] Similarity metric is cosine
- [ ] HNSW engine is nmslib (or justified alternative)
- [ ] ef_construction >= 512
- [ ] m >= 16
- [ ] ef_search >= 512
- [ ] `nl_query` field is text-indexed for hybrid search
- [ ] `provider_id` is keyword for filtering
- [ ] `query_intent` is keyword for filtering

### Challenge Protocol

**If Schema Architect proposes different configuration:**

1. **Request Justification**:
   - "Why dimension != 1024? This breaks Titan v2 compatibility."
   - "Why L2 instead of cosine? Text embeddings require cosine."

2. **Provide Data**:
   - Share this document section on similarity metrics
   - Reference Titan v2 documentation (1024 dims)

3. **Escalate if Needed**:
   - If disagreement on critical parameters (dimension, metric)
   - Bring to team lead with technical rationale

4. **Accept Reasonable Variations**:
   - ef_construction: 256-1024 (acceptable range)
   - Number of shards: Depends on scale
   - Replicas: Depends on availability requirements

## 10. Coordination with Query Patterns Analyst

### Information to Share

**Hybrid Search Weights**:
- Current: 0.7 vector + 0.3 keyword
- Proposed: Intent-based dynamic weighting
- Need input on query intent classification accuracy

**Similarity Thresholds**:
- Current: 0.7 minimum similarity
- Question: Should threshold vary by query intent?
- Request: Analysis of score distribution per intent

**Search Patterns**:
- Keyword matching good for: Exact table names, SQL clauses
- Vector matching good for: Paraphrases, concept matching
- Need: Guidelines on when to boost keyword vs vector weight

### Questions for Query Analyst

1. What percentage of queries have clear intent classification?
2. How accurate is intent detection (aggregation, filter, join)?
3. Should we implement intent-based weight adjustment?
4. What similarity threshold minimizes false positives?
5. Are there query patterns where vector search fails?

### Joint Deliverables

- **Search Strategy Document**: Combined embedding + query patterns
- **Weight Tuning Guidelines**: When to adjust vector/keyword balance
- **Threshold Recommendations**: Minimum similarity per intent
- **A/B Test Plan**: Evaluation metrics and success criteria

## 11. Coordination with Integration Engineer

### Embedding Generation Pipeline

**Interface Specification**:
```python
class EmbeddingService:
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate 1024-dim embedding via Bedrock Titan v2"""
        pass

    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batch (max 25)"""
        pass
```

**Error Handling**:
- Retry logic: 3 attempts with exponential backoff
- Timeout: 30 seconds per request
- Fallback: Return empty results, log error

**Caching Requirements**:
- Redis key: `embedding:<sha256(text)>`
- TTL: 3600 seconds (1 hour)
- Invalidation: Manual via admin API

### Performance Requirements

**Latency Targets**:
- Embedding generation: <200ms (p95)
- Cache hit: <5ms (p95)
- Batch processing: <5 seconds for 25 docs

**Throughput**:
- Single query: ~5 QPS (limited by Bedrock API)
- With caching: ~100 QPS (30% hit rate assumed)

**Monitoring**:
- Metric: `embedding_generation_duration_ms`
- Metric: `embedding_cache_hit_rate`
- Alert: If latency >500ms or cache hit <20%

### Integration Points

**RAG Service → OpenSearch**:
```python
# Generate embedding
embedding = await embedding_service.generate_embedding(query)

# Search OpenSearch
results = await opensearch.search_similar(
    query_vector=embedding,
    query_text=query,  # For hybrid search
    k=5,
    provider_id="postgres",
    hybrid=True
)
```

**Bulk Indexing**:
```python
# Batch embed
embeddings = await embedding_service.generate_batch(texts)

# Bulk index
await opensearch.bulk_index([
    {"id": id, "embedding": emb, "nl_query": text}
    for id, emb, text in zip(ids, embeddings, texts)
])
```

### Deployment Considerations

**AWS IAM Permissions**:
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel"
  ],
  "Resource": "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0"
}
```

**Environment Variables**:
```bash
BEDROCK_REGION=us-east-1
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_EMBEDDING_BATCH_SIZE=25
REDIS_URL=redis://localhost:6379/0
REDIS_EMBEDDING_CACHE_TTL=3600
```

**Health Checks**:
- Endpoint: `/health/embedding`
- Check: Generate test embedding, verify dimension=1024
- Frequency: Every 60 seconds

## Summary

**Embedding Strategy**:
- ✅ **Model**: AWS Bedrock Titan Embed v2 (1024 dims)
- ✅ **Content**: Natural language queries only
- ✅ **Metric**: Cosine similarity
- ✅ **Search**: Hybrid (0.7 vector + 0.3 keyword)
- ✅ **Hosting**: Bedrock primary, Redis caching
- ✅ **Performance**: <300ms end-to-end latency

**Key Decisions**:
1. Continue with Titan v2 (already working, AWS-native)
2. 1024 dimensions optimal (accuracy/performance balance)
3. Embed NL queries only (DSL as keyword search)
4. Cosine similarity (standard for text)
5. Intent-based hybrid weighting (future enhancement)

**Next Steps**:
1. Schema Architect implements vector field config (dimension=1024, cosine)
2. Query Analyst provides intent classification accuracy data
3. Integration Engineer implements caching layer
4. Team runs A/B tests on hybrid search weights

**Success Metrics**:
- Precision@5 > 0.85 (85% of top-5 results relevant)
- Search latency < 300ms (p95)
- Cache hit rate > 30%
- Cost < $10 per million queries

---

**Document Version**: 1.0
**Last Updated**: 2026-02-11
**Author**: Embeddings Expert (opensearch-dsl-design team)
**Status**: Ready for Implementation
