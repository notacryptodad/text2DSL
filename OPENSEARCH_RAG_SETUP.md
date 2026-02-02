# OpenSearch RAG Setup - Complete

This document describes the OpenSearch RAG (Retrieval-Augmented Generation) setup for the text2DSL project.

## Overview

The RAG system uses OpenSearch with k-NN vector search to find similar SQL queries based on natural language questions. It combines:
- **Vector similarity search** using Bedrock Titan embeddings (1024 dimensions)
- **Keyword matching** using BM25 full-text search
- **Hybrid search** combining both approaches with weighted scoring

## Components

### 1. Sample Queries Index

**Index Name:** `text2dsl-queries`

**Location:** OpenSearch at `localhost:9200` (no authentication)

**Status:** ✅ Created and indexed with 30 sample queries

**Schema:**
- `id`: Query identifier (keyword)
- `embedding`: 1024-dimensional vector from Titan v2 (knn_vector)
- `question`: Natural language query (text, analyzed)
- `sql`: SQL query (text, not analyzed)
- `difficulty`: Query difficulty level - simple/medium/complex (keyword)
- `created_at`: Timestamp (date)

**k-NN Configuration:**
- Algorithm: HNSW (Hierarchical Navigable Small World)
- Distance metric: Cosine similarity
- Engine: nmslib
- Parameters: ef_construction=512, m=16

### 2. Indexing Script

**File:** `scripts/index_sample_queries.py`

**Purpose:** Indexes sample queries from `tests/fixtures/sample_queries.json` into OpenSearch

**Features:**
- Creates index with k-NN configuration if it doesn't exist
- Generates embeddings using AWS Bedrock Titan v2
- Batch indexes all 30 sample queries
- Provides progress updates during indexing

**Usage:**
```bash
# Default settings (localhost:9200, index: text2dsl-queries)
python scripts/index_sample_queries.py

# With custom settings
OPENSEARCH_HOST=localhost \
OPENSEARCH_PORT=9200 \
OPENSEARCH_INDEX=text2dsl-queries \
AWS_REGION=us-east-1 \
python scripts/index_sample_queries.py
```

**Last Run:** Successfully indexed 30 queries on 2026-02-02

### 3. RAG Service Updates

**File:** `src/text2x/services/rag_service.py`

**Updates:**
- Added `include_sample_queries` parameter to `search_examples()` method
- Added `_search_sample_queries()` helper method
- Automatically includes sample queries in search results
- Merges and ranks results from both dynamic RAG examples and static sample queries

**Usage Example:**
```python
from text2x.services.rag_service import RAGService

rag_service = RAGService(opensearch_service=opensearch_service)

# Search with sample queries included (default)
examples = await rag_service.search_examples(
    query="How many customers do we have?",
    provider_id="postgres",
    limit=5,
    include_sample_queries=True  # Default is True
)

# Results will include:
# - Dynamic RAG examples from the database
# - Static sample queries from the text2dsl-queries index
# - All ranked by similarity score
```

## Embedding Model

**Model:** `amazon.titan-embed-text-v2:0`

**Dimensions:** 1024

**Provider:** AWS Bedrock

**Region:** us-east-1 (configurable)

## Verification

### Index Status
```bash
# Check index exists and document count
curl http://localhost:9200/text2dsl-queries/_count

# Output: {"count":30,...}
```

### Sample Documents
```bash
# View sample indexed documents
curl "http://localhost:9200/text2dsl-queries/_search?size=2&pretty"
```

### Index Mapping
```bash
# Check index configuration
curl "http://localhost:9200/text2dsl-queries/_mapping?pretty"
```

## Configuration

The following environment variables control the OpenSearch RAG setup:

```bash
# OpenSearch connection
OPENSEARCH_HOST=localhost          # Default: localhost
OPENSEARCH_PORT=9200               # Default: 9200
OPENSEARCH_INDEX=text2dsl-queries  # Default: text2dsl-queries

# AWS Bedrock for embeddings
AWS_REGION=us-east-1              # Default: us-east-1
BEDROCK_REGION=us-east-1          # Default: us-east-1
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
```

## Integration

The RAG system is integrated into the query generation pipeline:

1. **User submits natural language query**
2. **RAG service searches for similar examples**
   - Generates embedding for user query
   - Searches dynamic RAG examples (from user feedback)
   - Searches static sample queries (from fixture)
   - Combines and ranks results by similarity
3. **Top examples are used as context for LLM**
4. **LLM generates SQL query using examples**

## Benefits

1. **Improved query generation** - LLM has relevant examples to learn from
2. **Better handling of common queries** - Sample queries cover typical SQL patterns
3. **Learning from feedback** - Dynamic examples capture successful user queries
4. **Semantic search** - Vector embeddings find conceptually similar queries
5. **Hybrid approach** - Combines vector and keyword search for best results

## Maintenance

### Re-indexing
If sample queries are updated, re-run the indexing script:
```bash
python scripts/index_sample_queries.py
```

### Adding new samples
1. Update `tests/fixtures/sample_queries.json`
2. Run the indexing script
3. New queries will be available immediately

### Monitoring
Check OpenSearch cluster health:
```bash
curl http://localhost:9200/_cluster/health?pretty
```

## Status

✅ OpenSearch index created
✅ 30 sample queries indexed with embeddings
✅ RAG service updated to use sample queries
✅ Indexing script working and tested
✅ Documentation complete
✅ Changes pushed to main branch

The OpenSearch RAG setup is complete and operational!
