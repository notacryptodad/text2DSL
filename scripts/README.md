# Scripts

Utility scripts for managing the Text2DSL system.

## index_sample_queries.py

Indexes sample queries from `tests/fixtures/sample_queries.json` into OpenSearch for RAG retrieval.

### Features
- Creates OpenSearch index with k-NN vector search configuration
- Generates embeddings using AWS Bedrock Titan v2
- Indexes 30 sample SQL queries with embeddings
- Supports hybrid search (vector + keyword matching)

### Prerequisites
- OpenSearch running on localhost:9200 (or configure via environment variables)
- AWS credentials configured with access to Bedrock
- Python 3.11+ with project dependencies installed

### Usage

```bash
# Using default settings (localhost:9200, index: text2dsl-queries)
python scripts/index_sample_queries.py

# Using environment variables
OPENSEARCH_HOST=localhost \
OPENSEARCH_PORT=9200 \
OPENSEARCH_INDEX=text2dsl-queries \
AWS_REGION=us-east-1 \
python scripts/index_sample_queries.py
```

### Environment Variables

- `OPENSEARCH_HOST`: OpenSearch host (default: localhost)
- `OPENSEARCH_PORT`: OpenSearch port (default: 9200)
- `OPENSEARCH_INDEX`: Index name (default: text2dsl-queries)
- `AWS_REGION`: AWS region for Bedrock (default: us-east-1)

### Output

The script will:
1. Load 30 sample queries from the fixture file
2. Create the OpenSearch index with k-NN configuration
3. Generate embeddings for each query using Bedrock Titan
4. Index all queries with progress updates
5. Report success/failure counts

### Index Schema

The `text2dsl-queries` index contains:
- `id`: Query identifier (e.g., "sample_1")
- `embedding`: 1024-dimensional vector from Titan v2
- `question`: Natural language query (text, analyzed)
- `sql`: SQL query (text, not analyzed)
- `difficulty`: Query difficulty level (keyword)
- `created_at`: Timestamp (date)

### Integration

The RAG service (`src/text2x/services/rag_service.py`) automatically searches this index when `include_sample_queries=True` is set in the `search_examples()` method.
