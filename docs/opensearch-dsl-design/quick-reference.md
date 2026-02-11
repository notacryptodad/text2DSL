# OpenSearch DSL Index - Quick Reference

## Index Names

```
text2dsl-samples-sql       # SQL queries
text2dsl-samples-mongodb   # MongoDB queries
text2dsl-samples-splunk    # Splunk SPL queries
text2dsl-samples-custom-*  # Custom provider queries
```

## Essential Fields

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `id` | keyword | Unique identifier | "sample_123" |
| `provider_type` | keyword | Provider type | "sql", "mongodb", "splunk" |
| `natural_language_query` | text | User's question | "How many customers?" |
| `dsl_query` | text | Generated query | "SELECT COUNT(*) FROM customers" |
| `embedding` | knn_vector | 1024-dim vector | [0.123, 0.456, ...] |
| `status` | keyword | Review status | "approved", "pending_review", "rejected" |
| `is_good_example` | boolean | Quality flag | true, false |
| `query_intent` | keyword | Query type | "aggregation", "filter", "join" |
| `complexity_level` | keyword | Difficulty | "simple", "medium", "complex" |

## Common Query Patterns

### 1. Hybrid Search (Recommended)

```json
{
  "size": 5,
  "query": {
    "script_score": {
      "query": {
        "bool": {
          "must": [
            {
              "match": {
                "natural_language_query": {
                  "query": "USER_QUERY",
                  "boost": 0.3
                }
              }
            }
          ],
          "filter": [
            {"term": {"provider_type": "sql"}},
            {"term": {"status": "approved"}},
            {"term": {"is_good_example": true}}
          ]
        }
      },
      "script": {
        "source": "0.7 * (cosineSimilarity(params.query_vector, 'embedding') + 1.0) + 0.3 * _score",
        "params": {
          "query_vector": [EMBEDDING_VECTOR]
        }
      }
    }
  }
}
```

### 2. Vector-Only Search

```json
{
  "size": 5,
  "query": {
    "knn": {
      "embedding": {
        "vector": [EMBEDDING_VECTOR],
        "k": 5
      }
    }
  },
  "filter": [
    {"term": {"status": "approved"}}
  ]
}
```

### 3. Keyword-Only Search

```json
{
  "size": 5,
  "query": {
    "bool": {
      "must": [
        {
          "match": {
            "natural_language_query": "USER_QUERY"
          }
        }
      ],
      "filter": [
        {"term": {"status": "approved"}}
      ]
    }
  }
}
```

### 4. Filter by Intent

```json
{
  "size": 5,
  "query": {
    "bool": {
      "must": [
        {"match": {"natural_language_query": "USER_QUERY"}}
      ],
      "filter": [
        {"term": {"query_intent": "aggregation"}},
        {"term": {"status": "approved"}}
      ]
    }
  }
}
```

### 5. Filter by Complexity

```json
{
  "size": 5,
  "query": {
    "bool": {
      "must": [
        {"match": {"natural_language_query": "USER_QUERY"}}
      ],
      "filter": [
        {"term": {"complexity_level": "simple"}},
        {"term": {"status": "approved"}}
      ]
    }
  }
}
```

### 6. Filter by Tables

```json
{
  "size": 5,
  "query": {
    "bool": {
      "must": [
        {"match": {"natural_language_query": "USER_QUERY"}}
      ],
      "filter": [
        {"terms": {"involved_tables": ["customers", "orders"]}},
        {"term": {"status": "approved"}}
      ]
    }
  }
}
```

## Index Management Commands

### Create Index

```bash
curl -X PUT "localhost:9200/text2dsl-samples-sql" \
  -H 'Content-Type: application/json' \
  -d @opensearch-index-mapping.json
```

### Delete Index

```bash
curl -X DELETE "localhost:9200/text2dsl-samples-sql"
```

### Check Index Status

```bash
curl "localhost:9200/_cat/indices/text2dsl-samples-*?v"
```

### Get Index Mapping

```bash
curl "localhost:9200/text2dsl-samples-sql/_mapping?pretty"
```

### Get Index Settings

```bash
curl "localhost:9200/text2dsl-samples-sql/_settings?pretty"
```

### Count Documents

```bash
curl "localhost:9200/text2dsl-samples-sql/_count?pretty"
```

### Refresh Index

```bash
curl -X POST "localhost:9200/text2dsl-samples-sql/_refresh"
```

## Document Operations

### Index a Document

```bash
curl -X POST "localhost:9200/text2dsl-samples-sql/_doc/sample_123" \
  -H 'Content-Type: application/json' \
  -d '{
  "id": "sample_123",
  "provider_type": "sql",
  "provider_id": "postgres-prod",
  "natural_language_query": "How many customers?",
  "dsl_query": "SELECT COUNT(*) FROM customers",
  "dsl_query_analyzed": "SELECT COUNT(*) FROM customers",
  "embedding": [...],
  "embedding_model": "titan-v2",
  "query_intent": "aggregation",
  "complexity_level": "simple",
  "involved_tables": ["customers"],
  "is_good_example": true,
  "status": "approved",
  "source": "sample",
  "created_at": "2026-02-11T00:00:00Z",
  "updated_at": "2026-02-11T00:00:00Z",
  "indexed_at": "2026-02-11T00:00:00Z"
}'
```

### Update a Document

```bash
curl -X POST "localhost:9200/text2dsl-samples-sql/_update/sample_123" \
  -H 'Content-Type: application/json' \
  -d '{
  "doc": {
    "status": "approved",
    "reviewed_by": "expert_user",
    "reviewed_at": "2026-02-11T12:00:00Z"
  }
}'
```

### Get a Document

```bash
curl "localhost:9200/text2dsl-samples-sql/_doc/sample_123?pretty"
```

### Delete a Document

```bash
curl -X DELETE "localhost:9200/text2dsl-samples-sql/_doc/sample_123"
```

### Bulk Index Documents

```bash
curl -X POST "localhost:9200/_bulk" \
  -H 'Content-Type: application/x-ndjson' \
  --data-binary @bulk_data.ndjson
```

## Python Examples

### Create Index

```python
from opensearchpy import OpenSearch

client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    http_auth=None,
    use_ssl=False,
)

# Load mapping
with open("opensearch-index-mapping.json") as f:
    mapping = json.load(f)

# Create index
client.indices.create(
    index="text2dsl-samples-sql",
    body=mapping
)
```

### Index Document

```python
document = {
    "id": "sample_123",
    "provider_type": "sql",
    "natural_language_query": "How many customers?",
    "dsl_query": "SELECT COUNT(*) FROM customers",
    "embedding": [0.123, 0.456, ...],  # 1024-dim
    "status": "approved",
    "is_good_example": True,
    "query_intent": "aggregation",
    "complexity_level": "simple",
    "involved_tables": ["customers"],
    "created_at": "2026-02-11T00:00:00Z",
}

client.index(
    index="text2dsl-samples-sql",
    id="sample_123",
    body=document
)
```

### Search Documents

```python
query = {
    "size": 5,
    "query": {
        "bool": {
            "must": [
                {"match": {"natural_language_query": "customer count"}}
            ],
            "filter": [
                {"term": {"status": "approved"}},
                {"term": {"is_good_example": True}}
            ]
        }
    }
}

response = client.search(
    index="text2dsl-samples-sql",
    body=query
)

for hit in response["hits"]["hits"]:
    print(f"Score: {hit['_score']}")
    print(f"Query: {hit['_source']['natural_language_query']}")
    print(f"DSL: {hit['_source']['dsl_query']}")
```

### Hybrid Search with Vector

```python
# Generate embedding for query
query_text = "How many customers do we have?"
query_vector = generate_embedding(query_text)  # Your embedding function

search_body = {
    "size": 5,
    "query": {
        "script_score": {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "natural_language_query": {
                                    "query": query_text,
                                    "boost": 0.3
                                }
                            }
                        }
                    ],
                    "filter": [
                        {"term": {"status": "approved"}},
                        {"term": {"is_good_example": True}}
                    ]
                }
            },
            "script": {
                "source": "0.7 * (cosineSimilarity(params.query_vector, 'embedding') + 1.0) + 0.3 * _score",
                "params": {
                    "query_vector": query_vector
                }
            }
        }
    }
}

response = client.search(
    index="text2dsl-samples-sql",
    body=search_body
)
```

## Field Value Enums

### provider_type
- `sql` - SQL queries
- `mongodb` - MongoDB queries
- `splunk` - Splunk SPL queries
- `custom` - Custom provider queries

### status
- `pending_review` - Awaiting review
- `approved` - Approved for use
- `rejected` - Rejected

### query_intent
- `aggregation` - COUNT, SUM, AVG, etc.
- `filter` - WHERE clauses
- `join` - Multi-table joins
- `sort` - ORDER BY
- `group_by` - GROUP BY
- `subquery` - Nested queries
- `window_function` - Window functions
- `cte` - Common Table Expressions
- `union` - Set operations
- `insert`, `update`, `delete`, `create` - DML/DDL

### complexity_level
- `simple` - Single table, basic operations
- `medium` - Joins, aggregations
- `complex` - Advanced features

### source
- `sample` - Sample dataset
- `user_generated` - From user feedback
- `expert_created` - Manually created
- `system_generated` - Auto-generated

## Performance Tips

1. **Always use filters**: Filter on `status` and `provider_type` to reduce search space
2. **Limit result size**: Use `size` parameter (5-10 for most cases)
3. **Use bulk API**: For indexing multiple documents
4. **Pre-compute embeddings**: Generate embeddings before indexing
5. **Refresh strategically**: Use `refresh=false` for bulk operations
6. **Monitor query latency**: Aim for <100ms p50, <500ms p99
7. **Use aliases**: For zero-downtime schema updates

## Troubleshooting

### Slow searches
- Check `ef_search` parameter (default 512)
- Verify filters are applied correctly
- Monitor shard allocation

### Missing results
- Verify document status is "approved"
- Check embedding vector dimensions (must be 1024)
- Ensure query filters aren't too restrictive

### Indexing failures
- Validate embedding dimension (exactly 1024)
- Check required fields are present
- Verify JSON formatting

### Memory issues
- Reduce `number_of_replicas` if needed
- Adjust `ef_construction` parameter
- Monitor JVM heap usage

## Monitoring Queries

### Index Stats

```bash
curl "localhost:9200/text2dsl-samples-sql/_stats?pretty"
```

### Search Stats

```bash
curl "localhost:9200/_nodes/stats/indices/search?pretty"
```

### Cluster Health

```bash
curl "localhost:9200/_cluster/health?pretty"
```

---

**Version**: 1.0
**Last Updated**: 2026-02-11
