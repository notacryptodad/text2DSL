# OpenSearch DSL Design Documentation

This directory contains the complete OpenSearch index design for storing DSL (Domain-Specific Language) samples in the text2DSL RAG system.

## Overview

The design supports multi-provider DSL storage with advanced search capabilities:
- **SQL** queries (PostgreSQL, MySQL, etc.)
- **MongoDB** queries
- **Splunk** SPL queries
- **Custom** provider queries

## Documents

### 1. [opensearch-index-mapping.json](./opensearch-index-mapping.json)
Complete OpenSearch index configuration including:
- Index settings (shards, replicas, k-NN config)
- Field mappings (20+ fields for comprehensive metadata)
- Custom analyzers (natural language, DSL-specific)
- HNSW vector configuration for semantic search

**Use this file to**: Create new indices for DSL samples

### 2. [index-design-explanation.md](./index-design-explanation.md)
Detailed design documentation covering:
- Design philosophy and rationale
- Field-by-field explanation
- Text analyzer specifications
- Search strategy (hybrid vector + keyword)
- Performance characteristics
- Best practices

**Use this document to**: Understand design decisions and implementation details

### 3. [migration-guide.md](./migration-guide.md)
Step-by-step migration instructions:
- Migrating from existing `text2dsl-queries` index
- Blue-green deployment strategy
- Validation procedures
- Python automation scripts
- Rollback procedures
- Testing checklist

**Use this guide to**: Migrate from old to new index structure

### 4. [analyzer-config.json](./analyzer-config.json)
Custom analyzer configurations:
- Natural language analyzer
- SQL keyword analyzer (100+ keywords)
- MongoDB query analyzer (60+ operators)
- Splunk SPL analyzer (80+ commands)

**Use this file to**: Configure provider-specific text analysis

## Quick Start

### Create New Index

```bash
# Create SQL samples index
curl -X PUT "localhost:9200/text2dsl-samples-sql" \
  -H 'Content-Type: application/json' \
  -d @opensearch-index-mapping.json
```

### Index a Sample Document

```bash
curl -X POST "localhost:9200/text2dsl-samples-sql/_doc" \
  -H 'Content-Type: application/json' \
  -d '{
  "id": "sample_1",
  "provider_type": "sql",
  "provider_id": "postgres-prod",
  "natural_language_query": "How many customers do we have?",
  "dsl_query": "SELECT COUNT(*) FROM customers",
  "dsl_query_analyzed": "SELECT COUNT(*) FROM customers",
  "embedding": [0.123, 0.456, ...],
  "embedding_model": "titan-v2",
  "query_intent": "aggregation",
  "complexity_level": "simple",
  "difficulty": "simple",
  "involved_tables": ["customers"],
  "involved_fields": ["*"],
  "is_good_example": true,
  "status": "approved",
  "source": "sample",
  "usage_count": 0,
  "success_rate": 1.0,
  "avg_similarity_score": 0.0,
  "created_at": "2026-02-11T00:00:00Z",
  "updated_at": "2026-02-11T00:00:00Z",
  "indexed_at": "2026-02-11T00:00:00Z"
}'
```

### Search for Similar Queries

```bash
curl -X POST "localhost:9200/text2dsl-samples-sql/_search" \
  -H 'Content-Type: application/json' \
  -d '{
  "size": 5,
  "query": {
    "script_score": {
      "query": {
        "bool": {
          "must": [
            {
              "match": {
                "natural_language_query": {
                  "query": "count all users",
                  "boost": 0.3
                }
              }
            }
          ],
          "filter": [
            {"term": {"status": "approved"}},
            {"term": {"is_good_example": true}}
          ]
        }
      },
      "script": {
        "source": "cosineSimilarity(params.query_vector, '\''embedding'\'') + 1.0",
        "params": {
          "query_vector": [0.123, 0.456, ...]
        }
      }
    }
  }
}'
```

## Key Features

### Multi-Provider Support
- Provider-specific indices for SQL, MongoDB, Splunk
- Flexible schema accommodates different DSL types
- Custom analyzers per provider

### Hybrid Search
- **Vector similarity** (70%): Semantic matching via embeddings
- **Keyword matching** (30%): Exact term matching
- Configurable balance based on use case

### Quality Tracking
- Good vs. bad examples
- Review workflow (pending/approved/rejected)
- Expert corrections
- Usage metrics (count, success rate)

### Rich Metadata
- Query intent classification (aggregation, filter, join, etc.)
- Complexity levels (simple, medium, complex)
- Involved tables and fields
- Source tracking

### Performance
- k-NN HNSW for fast vector search
- Optimized sharding and replication
- Custom analyzers for efficient text matching
- Expected latency: <100ms p50, <500ms p99

## Design Principles

1. **Separation by Provider**: Each provider gets its own index for performance isolation
2. **Comprehensive Metadata**: Rich fields for sophisticated filtering and ranking
3. **Hybrid Retrieval**: Combines semantic and keyword search for best results
4. **Quality Control**: Built-in review workflow with expert corrections
5. **Usage Analytics**: Track which examples are most valuable
6. **Future-Proof**: Schema designed for evolution with versioning support

## Architecture Integration

This index design integrates with:
- **RAG Service** (`src/text2x/services/rag_service.py`): Retrieves similar examples
- **Indexing Script** (`scripts/index_sample_queries.py`): Populates indices
- **AgentCore**: Query generation agents consume retrieved examples
- **Review UI**: Expert review and correction workflow

## Schema Overview

### Core Fields (Required)
- `id`, `provider_type`, `provider_id`
- `natural_language_query`, `dsl_query`
- `embedding`, `embedding_model`
- `status`, `is_good_example`

### Classification Fields
- `query_intent`, `complexity_level`
- `involved_tables`, `involved_fields`

### Quality Fields
- `reviewed_by`, `reviewed_at`
- `expert_corrected_query`

### Analytics Fields
- `usage_count`, `success_rate`
- `avg_similarity_score`

### Metadata Fields
- `source`, `source_conversation_id`
- `source_metadata` (flexible JSON)

## Next Steps

1. **Review** the design documents
2. **Create indices** using the mapping file
3. **Migrate** existing data (see migration guide)
4. **Update** application code to use new fields
5. **Monitor** performance and adjust as needed

## Expert Coordination

This design incorporates input from:
- **Embeddings Expert**: Vector field configuration (dimension, HNSW parameters)
- **Query Patterns Analyst**: Search patterns and scoring balance
- **Integration Engineer**: API requirements and data flow

## Support

For questions or issues:
- Review the [explanation document](./index-design-explanation.md)
- Check the [migration guide](./migration-guide.md)
- Consult OpenSearch documentation: https://opensearch.org/docs/

---

**Version**: 1.0
**Created**: 2026-02-11
**Team**: opensearch-dsl-design
**Architect**: schema-architect
