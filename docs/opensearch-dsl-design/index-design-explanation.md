# OpenSearch Index Design Explanation

## Overview

This document explains the design rationale for the OpenSearch index mapping used to store DSL (Domain-Specific Language) samples for the text2DSL RAG (Retrieval-Augmented Generation) system.

## Design Philosophy

### Multi-Provider Architecture

The index is designed to support multiple query providers:
- **SQL** (PostgreSQL, MySQL, etc.)
- **NoSQL** (MongoDB, DynamoDB)
- **Splunk** (SPL - Splunk Processing Language)
- **Custom** (Plugin-based providers)

**Index Strategy**: Provider-specific indices following the pattern `text2dsl-samples-{provider}`:
- `text2dsl-samples-sql`
- `text2dsl-samples-mongodb`
- `text2dsl-samples-splunk`
- `text2dsl-samples-custom-{name}`

**Rationale**:
- **Performance Isolation**: Each provider index can be tuned independently
- **Schema Flexibility**: Provider-specific fields without conflicts
- **Simplified Filtering**: No need for complex provider type filters
- **Independent Scaling**: Scale high-volume providers without affecting others

## Index Settings

### Sharding and Replication

```json
{
  "number_of_shards": 2,
  "number_of_replicas": 1
}
```

**Shards (2)**:
- Appropriate for small to medium datasets (1K-100K documents)
- Allows horizontal scaling if needed
- Reduces overhead compared to over-sharding
- Each shard can be ~500MB-5GB

**Replicas (1)**:
- High availability (tolerates 1 node failure)
- Load balancing for read operations
- Zero downtime for maintenance

### Refresh Interval

```json
{
  "refresh_interval": "5s"
}
```

**5 seconds** balances:
- **Real-time needs**: Expert-corrected queries available quickly
- **Performance**: Not so frequent as to impact indexing throughput
- **User experience**: Acceptable delay for new examples to appear

### Result Windows

```json
{
  "max_result_window": 10000,
  "max_inner_result_window": 100
}
```

- **max_result_window (10000)**: Supports deep pagination if needed
- **max_inner_result_window (100)**: For nested queries and aggregations

### k-NN Configuration

```json
{
  "knn": true,
  "knn.algo_param.ef_search": 512
}
```

- **knn: true**: Enables k-NN vector search
- **ef_search: 512**: Quality of approximate search (higher = more accurate, slower)

## Field Mappings

### Identity Fields

#### `id` (keyword)
- Unique document identifier
- Used for updates and deletions
- Not analyzed for exact matching

#### `provider_type` (keyword)
- Values: `sql`, `mongodb`, `splunk`, `custom`
- Critical filter field
- Indexed as keyword for exact matching

#### `provider_id` (keyword)
- Specific provider instance (e.g., "postgres-prod", "mongodb-staging")
- Allows filtering examples by specific database connections
- Supports multi-tenancy

### Core Content Fields

#### `natural_language_query` (text)
```json
{
  "type": "text",
  "analyzer": "natural_language_analyzer",
  "fields": {
    "keyword": {
      "type": "keyword",
      "ignore_above": 256
    }
  }
}
```

**Analyzer**: Standard with English stopwords
- Tokenizes user questions into searchable terms
- Removes common stopwords ("the", "is", "at")
- Enables fuzzy matching and partial matches

**Keyword subfield**:
- Exact matching for specific queries
- Sorting and aggregations
- Limited to 256 characters

#### `dsl_query` (text, not indexed)
```json
{
  "type": "text",
  "index": false
}
```

- Stores the actual DSL query (SQL, MongoDB, SPL)
- **Not indexed**: Saves space, DSL is retrieved not searched
- Used only for display/execution

#### `dsl_query_analyzed` (text)
```json
{
  "type": "text",
  "analyzer": "dsl_query_analyzer"
}
```

- **Same content** as `dsl_query` but analyzed
- Enables pattern matching in queries (find queries with "JOIN", "GROUP BY")
- Whitespace tokenizer preserves SQL structure
- Lowercase filter for case-insensitive matching

### Vector Search Fields

#### `embedding` (knn_vector)
```json
{
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
}
```

**HNSW Algorithm**:
- **Hierarchical Navigable Small World**: Graph-based approximate nearest neighbor
- **Cosine Similarity**: Measures semantic similarity (0 to 1)
- **nmslib Engine**: Optimized C++ implementation

**Parameters**:
- **dimension: 1024**: Titan v2 embedding size
- **ef_construction: 512**: Build quality (higher = better recall)
- **m: 16**: Graph connectivity (balance between accuracy and memory)

**Performance Characteristics**:
- Search: O(log N) with high recall
- Build: O(N log N)
- Memory: ~4KB per document (1024 floats × 4 bytes)

#### `embedding_model` (keyword)
- Tracks which model generated the embedding
- Values: "titan-v2", "titan-v1", "custom-model"
- Enables versioning and migration

### Metadata Fields

#### `query_intent` (keyword)
Classification of query purpose:
- `aggregation` - SUM, AVG, COUNT, etc.
- `filter` - WHERE clauses
- `join` - Multi-table queries
- `sort` - ORDER BY
- `group_by` - GROUP BY operations
- `subquery` - Nested queries
- `window_function` - ROW_NUMBER, RANK, etc.
- `cte` - Common Table Expressions
- `union` - Set operations
- `insert`, `update`, `delete`, `create` - DML/DDL

**Use Case**: Filter examples by intent type during retrieval

#### `complexity_level` (keyword)
- `simple` - Single table, basic filters
- `medium` - Joins, aggregations
- `complex` - Multiple joins, subqueries, window functions

**Use Case**: Match query complexity to user skill level

#### `difficulty` (keyword)
- Alias for `complexity_level`
- Maintains backward compatibility with existing code
- Same values: `simple`, `medium`, `complex`

#### `involved_tables` (keyword array)
```json
{
  "type": "keyword"
}
```

- Array of table/collection names referenced in query
- Example: `["customers", "orders", "order_items"]`
- **Use Case**: Find examples using specific tables

#### `involved_fields` (keyword array)
- Array of field/column names used
- Example: `["customer_id", "total", "created_at"]`
- **Use Case**: Find examples with specific field patterns

### Quality and Review Fields

#### `is_good_example` (boolean)
- `true`: Good example to learn from
- `false`: Bad example to avoid repeating mistakes

**Use Case**: System can learn from both successes and failures

#### `status` (keyword)
- `pending_review` - Awaiting expert review
- `approved` - Approved for RAG retrieval
- `rejected` - Not suitable for retrieval

**Use Case**: Only retrieve approved examples for query generation

#### `reviewed_by` (keyword)
- Username or ID of the reviewer
- Tracks accountability

#### `reviewed_at` (date)
- Timestamp of review
- ISO 8601 format

#### `expert_corrected_query` (text, not indexed)
- Expert's corrected version if original was wrong
- Takes precedence over `dsl_query` for RAG
- Not indexed (only used for retrieval)

### Source Tracking Fields

#### `source` (keyword)
- `sample` - From sample dataset
- `user_generated` - From user feedback
- `expert_created` - Manually created by expert
- `system_generated` - Auto-generated by system

**Use Case**: Track example provenance

#### `source_conversation_id` (keyword)
- Links to original conversation that generated this example
- UUID format
- Enables tracing back to context

#### `source_metadata` (object)
```json
{
  "type": "object",
  "enabled": true,
  "dynamic": true
}
```

- Flexible JSON object for provider-specific metadata
- **Dynamic**: Can add new fields without schema changes
- Examples:
  - SQL: `{"database": "postgres", "version": "14.2"}`
  - MongoDB: `{"collection": "users", "index_used": "email_idx"}`
  - Splunk: `{"sourcetype": "access_log", "time_range": "24h"}`

### Usage Metrics Fields

#### `usage_count` (integer)
- How many times this example was retrieved
- Incremented on each RAG fetch
- **Use Case**: Identify most valuable examples

#### `success_rate` (float)
- Percentage of successful uses (0.0 to 1.0)
- Calculated as: `successful_uses / total_uses`
- **Use Case**: Rank by effectiveness

#### `avg_similarity_score` (float)
- Average similarity score when retrieved
- Range: 0.0 to 1.0
- **Use Case**: Identify broadly relevant examples

### Timestamp Fields

#### `created_at` (date)
- When the sample was first added
- ISO 8601 format

#### `updated_at` (date)
- Last modification time
- Updated on any field change

#### `indexed_at` (date)
- When the document was indexed in OpenSearch
- Useful for debugging indexing delays

## Text Analyzers

### Natural Language Analyzer

```json
{
  "type": "standard",
  "stopwords": "_english_"
}
```

**Purpose**: Analyze user questions for keyword matching

**Process**:
1. **Tokenization**: "How many customers do we have?" → ["How", "many", "customers", "do", "we", "have"]
2. **Lowercase**: ["how", "many", "customers", "do", "we", "have"]
3. **Stop words removal**: ["many", "customers", "have"]
4. **Result**: Searchable tokens for matching

**Characteristics**:
- Good for natural language queries
- Handles punctuation automatically
- Language-aware (English)

### DSL Query Analyzer

```json
{
  "type": "custom",
  "tokenizer": "whitespace",
  "filter": ["lowercase"]
}
```

**Purpose**: Analyze DSL queries for pattern matching

**Process**:
1. **Tokenization**: "SELECT name FROM users" → ["SELECT", "name", "FROM", "users"]
2. **Lowercase**: ["select", "name", "from", "users"]
3. **Result**: Preserves SQL structure while enabling case-insensitive search

**Characteristics**:
- Preserves syntax structure
- No stemming (keeps "ordering" vs "order" distinct)
- Simple and fast

### SQL Keyword Analyzer

```json
{
  "type": "custom",
  "tokenizer": "sql_keyword_tokenizer",
  "filter": ["lowercase", "sql_keyword_filter"]
}
```

**Purpose**: Specialized analyzer for SQL pattern matching

**Tokenizer**: Pattern-based tokenization on spaces, commas, parentheses

**Filter**: Preserves SQL keywords (SELECT, JOIN, WHERE, etc.)

**Use Case**: Find queries with specific SQL patterns while respecting syntax

## Search Strategy

### Hybrid Search

The index supports **hybrid search** combining vector similarity and keyword matching:

```
Final Score = 0.7 × Vector Score + 0.3 × Keyword Score
```

**Vector Component (70%)**:
- Semantic similarity via embeddings
- Finds conceptually similar queries
- High recall for paraphrased questions

**Keyword Component (30%)**:
- Exact/fuzzy term matching
- Handles specific terminology
- Good for technical terms not in embeddings

### Filtering Strategy

**Must Filters** (hard requirements):
- `provider_type`: Only fetch examples for correct provider
- `status`: Only approved examples
- `is_good_example`: Typically true (learn from good examples)

**Should Filters** (soft preferences):
- `query_intent`: Prefer matching intent types
- `complexity_level`: Prefer similar complexity
- `involved_tables`: Boost examples using same tables

### Ranking Boosters

Additional ranking factors:
1. **Recency**: Newer examples may be more relevant
2. **Usage Count**: Popular examples are proven valuable
3. **Success Rate**: Prioritize examples that work well
4. **Exact Match**: Boost exact keyword matches

## Performance Considerations

### Memory Usage

**Per Document**:
- Vector: ~4KB (1024 × 4 bytes)
- Metadata: ~1-2KB
- Text fields: Variable (typically 0.5-2KB)
- **Total**: ~5-8KB per document

**For 10K documents**: ~50-80MB
**For 100K documents**: ~500-800MB

### Search Latency

**Expected Performance**:
- **p50**: <50ms
- **p95**: <200ms
- **p99**: <500ms

**Factors**:
- HNSW parameters (ef_search)
- Filter selectivity
- Document count
- Shard allocation

### Indexing Throughput

**Expected Performance**:
- **Bulk indexing**: 100-500 docs/sec
- **Single document**: 10-50 docs/sec
- **With embedding generation**: 5-20 docs/sec (Bedrock API limit)

## Migration from Existing Index

### Backward Compatibility

The new schema maintains compatibility with existing `text2dsl-queries` index:

**Field Mapping**:
- Old `question` → New `natural_language_query`
- Old `sql` → New `dsl_query`
- Old `difficulty` → New `difficulty` (unchanged)
- Old `embedding` → New `embedding` (unchanged)

### Migration Steps

1. **Create new indices** with updated schema
2. **Reindex** existing documents with field mapping
3. **Add missing fields** with default values
4. **Test** search queries on new indices
5. **Update application** to use new indices
6. **Deprecate** old index after validation

### Sample Migration Script

```python
# Reindex from old to new index
POST _reindex
{
  "source": {
    "index": "text2dsl-queries"
  },
  "dest": {
    "index": "text2dsl-samples-sql"
  },
  "script": {
    "source": """
      ctx._source.natural_language_query = ctx._source.remove('question');
      ctx._source.dsl_query = ctx._source.remove('sql');
      ctx._source.provider_type = 'sql';
      ctx._source.provider_id = 'default';
      ctx._source.status = 'approved';
      ctx._source.is_good_example = true;
      ctx._source.source = 'sample';
      ctx._source.indexed_at = new Date();
    """
  }
}
```

## Best Practices

### Indexing

1. **Batch Operations**: Use bulk API for multiple documents
2. **Embedding Generation**: Pre-compute embeddings before indexing
3. **Validation**: Validate DSL syntax before indexing
4. **Metadata**: Always populate critical fields (provider_type, status, query_intent)

### Searching

1. **Filter First**: Apply must filters to reduce candidate set
2. **Hybrid Search**: Use both vector and keyword components
3. **Min Similarity**: Set threshold (e.g., 0.7) to filter low-quality matches
4. **Result Size**: Limit to top K (5-10) for best performance

### Maintenance

1. **Index Aliases**: Use aliases for zero-downtime updates
2. **Monitoring**: Track search latency, indexing rate, error rate
3. **Optimization**: Periodically merge segments, force-merge after bulk loads
4. **Backup**: Regular snapshots for disaster recovery

## Future Enhancements

### Potential Improvements

1. **Multi-Language Support**: Analyzers for non-English queries
2. **Query Expansion**: Synonym support for domain terminology
3. **Learning to Rank**: ML-based ranking using click-through data
4. **Federated Search**: Cross-provider search with unified scoring
5. **Time-Based Decay**: Reduce relevance of old examples over time
6. **Diversity**: MMR algorithm to avoid redundant results

### Schema Evolution

The schema is designed for evolution:
- **Dynamic object**: `source_metadata` allows new fields
- **Versioning**: `embedding_model` tracks model versions
- **Aliases**: Enable seamless schema updates

## References

- [OpenSearch k-NN Documentation](https://opensearch.org/docs/latest/search-plugins/knn/)
- [HNSW Algorithm Paper](https://arxiv.org/abs/1603.09320)
- [Text Analysis Guide](https://opensearch.org/docs/latest/analyzers/)
- [Hybrid Search Best Practices](https://opensearch.org/blog/hybrid-search/)

---

**Document Version**: 1.0
**Last Updated**: 2026-02-11
**Author**: Schema Architect - opensearch-dsl-design team
