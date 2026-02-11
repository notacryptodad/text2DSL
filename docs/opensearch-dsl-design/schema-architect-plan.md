# OpenSearch Index Mapping Design Plan - Schema Architect

## Current Understanding

After exploring the text2DSL codebase, I understand:

### DSL Sample Structure
1. **Current Implementation** (from `/home/ubuntu/text2DSL-opensearch-design/scripts/index_sample_queries.py`):
   - Index: `text2dsl-queries`
   - Fields: `id`, `embedding` (1024-dim knn_vector), `question`, `sql`, `difficulty`, `created_at`
   - Sample data: 30 SQL queries from `/home/ubuntu/text2DSL-opensearch-design/tests/fixtures/sample_queries.json`

2. **RAG Examples Model** (from `/home/ubuntu/text2DSL-opensearch-design/src/text2x/models/rag.py`):
   - Provider-specific DSL samples (SQL, MongoDB, Splunk)
   - Natural language query + generated query pairs
   - Metadata: provider_id, involved_tables, query_intent, complexity_level
   - Review status: pending_review, approved, rejected
   - Expert corrections and feedback

3. **Multi-Provider Support** (from `/home/ubuntu/text2DSL-opensearch-design/src/text2x/providers/`):
   - SQL Provider (PostgreSQL, MySQL)
   - NoSQL Provider (MongoDB)
   - Splunk Provider (SPL)
   - Custom providers via plugin system

### Current Limitations
- Existing index only supports SQL queries
- No multi-provider support in OpenSearch schema
- Missing metadata fields for advanced filtering
- No support for MongoDB queries, Splunk SPL, or other DSLs
- Limited text analysis configuration
- No version tracking for schema evolution

## Proposed Design

### Index Naming Strategy
Create provider-specific indices with a common pattern:
- `text2dsl-samples-sql` - SQL queries
- `text2dsl-samples-mongodb` - MongoDB queries
- `text2dsl-samples-splunk` - Splunk SPL queries
- `text2dsl-samples-custom-{provider}` - Custom provider queries

**Rationale**: Separate indices per provider allow:
- Provider-specific field mappings
- Independent scaling and tuning
- Simpler query filtering
- Better performance isolation

### Core Index Structure

#### 1. **Document Fields**

**Identity & Core Content**:
- `id` (keyword) - Unique document identifier
- `provider_type` (keyword) - sql, mongodb, splunk, custom
- `provider_id` (keyword) - Specific provider instance identifier
- `natural_language_query` (text) - User's original question
- `dsl_query` (text) - Generated DSL query (not analyzed for exact matching)
- `dsl_query_analyzed` (text) - Same content with analysis for pattern matching

**Semantic Search**:
- `embedding` (knn_vector, 1024-dim) - Titan v2 embeddings
- `embedding_model` (keyword) - Track which model generated the embedding

**Metadata & Classification**:
- `query_intent` (keyword) - aggregation, filter, join, sort, group_by, etc.
- `complexity_level` (keyword) - simple, medium, complex
- `difficulty` (keyword) - Alias for complexity_level (backward compatibility)
- `involved_tables` (keyword array) - Tables/collections referenced
- `involved_fields` (keyword array) - Fields/columns referenced

**Quality & Review**:
- `is_good_example` (boolean) - Good example to learn from vs. bad to avoid
- `status` (keyword) - pending_review, approved, rejected
- `reviewed_by` (keyword) - Reviewer username/ID
- `reviewed_at` (date) - Review timestamp
- `expert_corrected_query` (text) - Expert's corrected version if applicable

**Source Tracking**:
- `source` (keyword) - sample, user_generated, expert_created, system_generated
- `source_conversation_id` (keyword) - Link to original conversation
- `source_metadata` (object) - Flexible JSON for provider-specific metadata

**Usage & Performance**:
- `usage_count` (integer) - How many times this example was retrieved
- `success_rate` (float) - Percentage of successful uses (0.0-1.0)
- `avg_similarity_score` (float) - Average similarity when retrieved

**Timestamps**:
- `created_at` (date) - When sample was added
- `updated_at` (date) - Last modification time
- `indexed_at` (date) - When indexed in OpenSearch

#### 2. **Text Analyzers**

**Standard Analyzer** (for natural_language_query):
- Tokenization: Standard tokenizer
- Filters: lowercase, stop words (English), stemming (porter)
- Purpose: General keyword matching with fuzzy tolerance

**DSL Query Analyzer** (for dsl_query_analyzed):
- Tokenization: Whitespace tokenizer (preserve SQL syntax)
- Filters: lowercase only (no stemming to preserve keywords)
- Purpose: Pattern matching in queries without breaking syntax

**Custom SQL Analyzer** (for SQL-specific index):
- Tokenization: Pattern tokenizer with SQL keyword recognition
- Filters: lowercase, SQL keyword preservation
- Purpose: Better matching of SQL patterns (SELECT, JOIN, WHERE, etc.)

#### 3. **Index Settings**

**k-NN Configuration**:
```json
{
  "index.knn": true,
  "index.knn.algo_param.ef_search": 512
}
```

**Sharding & Replication**:
- `number_of_shards`: 2 (small to medium dataset, can scale)
- `number_of_replicas`: 1 (high availability)

**Refresh Interval**:
- `refresh_interval`: "5s" (balance between real-time and performance)

**Performance Tuning**:
- `max_result_window`: 10000 (allow deep pagination)
- `max_inner_result_window`: 100 (for nested queries)

#### 4. **Vector Field Configuration**

**HNSW Algorithm**:
- `method.name`: "hnsw" (Hierarchical Navigable Small World)
- `method.space_type`: "cosinesimil" (cosine similarity for semantic search)
- `method.engine`: "nmslib" (efficient library for approximate nearest neighbor)

**HNSW Parameters** (to coordinate with Embeddings Expert):
- `ef_construction`: 512 (build quality - higher = more accurate)
- `m`: 16 (connections per node - balance between accuracy and memory)
- Dimension: 1024 (Titan v2 output size)

**Questions for Embeddings Expert**:
1. Should we support multiple embedding models (different dimensions)?
2. Should we pre-compute embeddings or generate on-the-fly?
3. What's the optimal ef_search value for our use case?
4. Should we implement embedding versioning for model updates?

### Hybrid Search Strategy

**Search Query Pattern** (to coordinate with Query Patterns Analyst):
```json
{
  "query": {
    "script_score": {
      "query": {
        "bool": {
          "must": [
            {"match": {"provider_type": "sql"}}
          ],
          "should": [
            {"match": {"natural_language_query": {"query": "user_query", "boost": 0.3}}},
            {"match": {"query_intent": {"query": "aggregation", "boost": 0.2}}}
          ],
          "filter": [
            {"term": {"status": "approved"}},
            {"term": {"is_good_example": true}}
          ]
        }
      },
      "script": {
        "source": "0.7 * cosineSimilarity(params.query_vector, 'embedding') + 1.0 + 0.3 * _score"
      }
    }
  }
}
```

**Questions for Query Patterns Analyst**:
1. What's the optimal balance between vector and keyword scores?
2. Should we implement multi-stage retrieval (coarse then fine)?
3. What filters are most important for production use?
4. Should we support advanced features like MMR (Maximal Marginal Relevance)?

### AgentCore Integration

**Data Needs** (to coordinate with Integration Engineer):

1. **Indexing Pipeline**:
   - Batch indexing of approved RAG examples
   - Real-time indexing of expert-corrected queries
   - Bulk import of sample datasets

2. **Search API Requirements**:
   - Hybrid search with configurable weights
   - Provider-specific filtering
   - Intent-based retrieval
   - Complexity-based ranking
   - Minimum similarity thresholds

3. **Schema Evolution**:
   - Version tracking for index schema changes
   - Migration path for existing documents
   - Backward compatibility layer

**Questions for Integration Engineer**:
1. What's the expected query volume per second?
2. How should we handle index updates without downtime?
3. Should we implement a staging index for new samples?
4. What monitoring metrics are needed?

## Implementation Steps

### Phase 1: Design Documentation (Current Phase)
1. ✓ Explore codebase and understand current structure
2. ✓ Design comprehensive index mapping
3. Create `opensearch-index-mapping.json` with full schema
4. Write explanation document with design rationale
5. Wait for team lead approval

### Phase 2: Expert Coordination (After Approval)
1. Consult Embeddings Expert on vector configuration
2. Consult Query Patterns Analyst on search requirements
3. Consult Integration Engineer on data flow and APIs
4. Incorporate feedback and finalize design

### Phase 3: Implementation
1. Create index templates for each provider type
2. Implement custom analyzers
3. Test with sample data
4. Validate performance characteristics
5. Document usage and migration guide

## Open Questions

1. **Versioning**: Should we version the schema for future changes?
2. **Multi-language**: Support for non-English queries?
3. **Security**: Field-level security or role-based access?
4. **Monitoring**: What OpenSearch metrics should we track?
5. **Backup**: Index snapshot strategy?
6. **TTL**: Should old/unused samples expire?

## Dependencies

- Embeddings Expert: Vector field specifications and embedding strategy
- Query Patterns Analyst: Search patterns and ranking strategy
- Integration Engineer: AgentCore data flow and API design

## Deliverables

1. `opensearch-index-mapping.json` - Complete index mapping for all provider types
2. `index-design-explanation.md` - Detailed design rationale and usage guide
3. `migration-guide.md` - How to migrate from existing index structure
4. `analyzer-config.json` - Custom analyzer definitions
