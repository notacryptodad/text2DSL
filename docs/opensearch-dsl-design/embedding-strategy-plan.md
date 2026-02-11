# Embedding Strategy Plan for DSL Sample Semantic Search

## Context
The text2DSL system needs semantic search capabilities to find DSL examples (SQL, NoSQL, Splunk SPL, etc.) that are conceptually similar to a user's natural language query, even when exact keywords don't match.

## Current State Analysis

### Existing Implementation
- **Embedding Model**: AWS Bedrock Titan Embed v2 (`amazon.titan-embed-text-v2:0`)
- **Vector Dimensions**: 1024
- **OpenSearch**: Currently used for RAG examples with k-NN vector search
- **Hybrid Search**: Already implemented (70% vector + 30% keyword)
- **Index Setup**: HNSW algorithm with cosine similarity
- **Usage**: Embeddings generated for natural language queries in RAGExample model

### Current Architecture
The system has:
1. **Dynamic RAG Examples**: User-generated query examples stored in PostgreSQL + OpenSearch
2. **Static Sample Queries**: 30 sample queries in `text2dsl-queries` index
3. **Hybrid Search**: Vector similarity + BM25 keyword matching
4. **Multi-provider Support**: SQL, NoSQL, Splunk SPL

## Plan: Embedding Strategy Document

### Phase 1: Research & Analysis (Research current implementation)

**Tasks:**
1. Analyze current embedding performance characteristics
   - Review Titan v2 embedding dimension (1024) and its accuracy trade-offs
   - Document current similarity metrics (cosine similarity via HNSW)
   - Assess current hybrid search weights (0.7 vector, 0.3 keyword)

2. Evaluate what is currently embedded
   - Natural language queries are embedded (via `nl_query` field)
   - Generated DSL queries are NOT embedded (stored as text only)
   - Metadata fields used for filtering (provider_id, query_intent, complexity_level)

3. Research alternative embedding models
   - **Sentence-Transformers**:
     * all-MiniLM-L6-v2 (384 dims) - fast, good for general semantic search
     * all-mpnet-base-v2 (768 dims) - better accuracy, moderate size
     * multi-qa-mpnet-base-dot-v1 (768 dims) - optimized for Q&A retrieval
   - **OpenAI**: text-embedding-3-small (1536 dims), text-embedding-3-large (3072 dims)
   - **Cohere**: embed-english-v3.0 (1024 dims)
   - **AWS Bedrock Options**: Titan v2 (current), Cohere Embed on Bedrock

4. Analyze query patterns and DSL sample characteristics
   - Review sample queries in fixtures (30 queries with simple/medium/complex difficulty)
   - Identify common query intents (aggregation, filter, join, etc.)
   - Assess multi-provider requirements (SQL vs NoSQL vs Splunk)

### Phase 2: Strategy Recommendations (Create comprehensive document)

**Document Structure:**

1. **Executive Summary**
   - Keep AWS Bedrock Titan v2 as primary embedding model
   - Rationale: Already integrated, AWS-native, good performance
   - Recommend enhancements to current strategy

2. **Embedding Model Recommendation**
   - **Primary Model**: AWS Bedrock Titan Embed v2 (`amazon.titan-embed-text-v2:0`)
     * Pros: AWS-native, 1024 dimensions (good accuracy/performance balance), already integrated
     * Cons: Proprietary, costs per API call, no local deployment
   - **Fallback/Alternative**: Sentence-Transformers (multi-qa-mpnet-base-dot-v1)
     * Pros: Open-source, free, optimized for Q&A retrieval, can run locally
     * Cons: Requires separate hosting, 768 dimensions (different index config)
   - **Justification**: Titan v2 provides excellent out-of-box performance with minimal ops overhead

3. **Vector Dimensions**
   - **Recommendation**: Keep 1024 dimensions (Titan v2 default)
   - **Trade-offs Analysis**:
     * Higher dimensions (1536-3072): Better accuracy, higher storage/compute cost
     * Current 1024: Optimal balance for production workloads
     * Lower dimensions (384-768): Faster, but accuracy drop unacceptable for SQL generation

4. **What to Embed**
   - **Primary**: Natural language query text (current approach is correct)
   - **Consideration**: Add description field embeddings for richer context
   - **Do NOT embed**: Generated DSL queries (use keyword search instead)
   - **Rationale**:
     * NL queries capture user intent semantically
     * DSL syntax is better matched via keywords/patterns
     * Embedding both would dilute semantic relevance

5. **Similarity Metric**
   - **Recommendation**: Cosine similarity (current approach)
   - **Alternatives Evaluated**:
     * Dot product: Faster but magnitude-dependent (not normalized)
     * L2 (Euclidean): Good for distance-based, but cosine better for text
   - **Justification**: Cosine similarity is standard for text embeddings (magnitude-invariant)

6. **Model Hosting Strategy**
   - **Current**: AWS Bedrock (serverless, pay-per-use)
   - **Recommendation**: Continue with Bedrock for production
   - **Alternative for Dev/Test**:
     * Consider sentence-transformers locally for cost savings in non-prod
     * Docker container with embedding service API
   - **Hybrid Approach**: Bedrock primary, local fallback for dev

7. **Hybrid Search Configuration**
   - **Current Weights**: 0.7 vector + 0.3 keyword (70/30 split)
   - **Recommendation**: Make weights configurable per query intent
     * Aggregation queries: 0.8 vector + 0.2 keyword (concepts matter more)
     * Exact filters: 0.5 vector + 0.5 keyword (keywords matter more)
     * Complex joins: 0.7 vector + 0.3 keyword (balanced)
   - **A/B Testing Plan**: Track retrieval quality metrics to tune weights

8. **Performance Considerations**
   - **Embedding Generation**: ~100-200ms per query via Bedrock API
   - **Search Latency**: ~50-100ms for k-NN search (HNSW with ef_search=512)
   - **Optimization**: Cache embeddings for repeated queries (Redis)
   - **Batch Processing**: Use batch embedding for bulk indexing (25 docs per batch)

9. **Multi-Provider Support**
   - **Challenge**: SQL vs NoSQL vs Splunk have different query languages
   - **Strategy**: Use provider_id filtering + provider-specific fine-tuning
   - **Recommendation**: Single embedding model with provider-aware retrieval
   - **Future Enhancement**: Provider-specific embedding models if quality drops

### Phase 3: Vector Field Specifications (For Schema Architect)

**OpenSearch Index Requirements:**

```json
{
  "settings": {
    "index.knn": true,
    "index.knn.algo_param.ef_search": 512,
    "number_of_shards": 2,
    "number_of_replicas": 1
  },
  "mappings": {
    "properties": {
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
      "provider_id": {"type": "keyword"},
      "query_intent": {"type": "keyword"},
      "complexity_level": {"type": "keyword"}
    }
  }
}
```

**Key Parameters:**
- `dimension`: 1024 (Titan v2 embedding size)
- `space_type`: cosinesimil (cosine similarity metric)
- `ef_search`: 512 (search-time accuracy parameter)
- `ef_construction`: 512 (index-time accuracy parameter)
- `m`: 16 (HNSW connectivity parameter)

### Phase 4: Coordination Points

**Schema Architect:**
- Ensure vector field configuration matches 1024 dimensions
- Validate HNSW parameters (ef_search=512, m=16)
- Confirm cosine similarity metric
- Challenge if vector field deviates from specifications

**Query Patterns Analyst:**
- Coordinate on hybrid search weight configuration
- Provide input on query intent-based weight adjustment
- Share findings on keyword vs semantic search balance
- Align on similarity threshold recommendations (current: 0.7)

**Integration Engineer:**
- Embedding generation pipeline integration
- Caching strategy for repeated queries
- Batch embedding for bulk operations
- Error handling and fallback mechanisms

## Success Criteria

1. **Document Completeness**: All sections of embedding-strategy.md written with clear rationale
2. **Technical Accuracy**: Recommendations backed by research and current implementation analysis
3. **Actionable Specs**: Clear vector field specifications for Schema Architect
4. **Team Alignment**: Coordination points defined for all teammates
5. **Future-Proof**: Strategy supports multi-provider expansion and model upgrades

## Risks & Mitigation

1. **Risk**: Bedrock API costs for high-volume embeddings
   - **Mitigation**: Implement Redis caching, batch processing, rate limiting

2. **Risk**: Titan v2 model changes or deprecation
   - **Mitigation**: Abstract embedding interface, support multiple models

3. **Risk**: Accuracy drops for non-SQL providers (NoSQL, Splunk)
   - **Mitigation**: Provider-specific filtering, potential model fine-tuning

4. **Risk**: Team disagreement on embedding approach
   - **Mitigation**: Data-driven decisions, A/B testing, metrics tracking

## Timeline

1. **Phase 1 - Research**: Complete analysis of current implementation and alternatives
2. **Phase 2 - Document**: Write comprehensive embedding-strategy.md
3. **Phase 3 - Specifications**: Provide vector field specs to Schema Architect
4. **Phase 4 - Coordination**: Align with Query Patterns Analyst and Integration Engineer

## Open Questions for Team Lead

1. Should we support multiple embedding models (primary + fallback)?
2. What is the acceptable latency budget for embedding generation?
3. Should we implement provider-specific embedding models or single unified model?
4. What metrics should we track for embedding quality (NDCG, MRR, precision@k)?
