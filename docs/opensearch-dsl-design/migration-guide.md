# Migration Guide: OpenSearch Index Schema Update

## Overview

This guide provides step-by-step instructions for migrating from the existing `text2dsl-queries` index to the new multi-provider index structure.

## What's Changing

### Index Structure

**Old**: Single index `text2dsl-queries`
**New**: Provider-specific indices `text2dsl-samples-{provider}`

### Field Changes

| Old Field | New Field | Notes |
|-----------|-----------|-------|
| `question` | `natural_language_query` | Renamed for clarity |
| `sql` | `dsl_query` | Generalized for multi-provider |
| `difficulty` | `complexity_level` | Primary field, `difficulty` is alias |
| `id` | `id` | Unchanged |
| `embedding` | `embedding` | Unchanged |
| `created_at` | `created_at` | Unchanged |
| (none) | `provider_type` | **New**: sql, mongodb, splunk, etc. |
| (none) | `provider_id` | **New**: Provider instance ID |
| (none) | `query_intent` | **New**: Query classification |
| (none) | `involved_tables` | **New**: Referenced tables |
| (none) | `is_good_example` | **New**: Quality indicator |
| (none) | `status` | **New**: Review status |
| (none) | Multiple new fields | See full schema |

## Migration Strategy

We recommend a **blue-green deployment** approach for zero downtime:

1. **Create new indices** (green)
2. **Reindex data** from old to new
3. **Validate** data integrity and search quality
4. **Switch traffic** to new indices
5. **Monitor** performance
6. **Deprecate** old index after validation period

## Prerequisites

- OpenSearch cluster accessible
- Admin credentials with index creation privileges
- Python 3.8+ for migration scripts
- AWS credentials configured (for embedding generation)

## Step-by-Step Migration

### Step 1: Create New Indices

Create the new indices with the updated schema:

```bash
# Create SQL samples index
curl -X PUT "localhost:9200/text2dsl-samples-sql" \
  -H 'Content-Type: application/json' \
  -d @opensearch-index-mapping.json

# Create MongoDB samples index
curl -X PUT "localhost:9200/text2dsl-samples-mongodb" \
  -H 'Content-Type: application/json' \
  -d @opensearch-index-mapping.json

# Create Splunk samples index
curl -X PUT "localhost:9200/text2dsl-samples-splunk" \
  -H 'Content-Type: application/json' \
  -d @opensearch-index-mapping.json
```

**Verify creation**:
```bash
curl "localhost:9200/_cat/indices/text2dsl-samples-*?v"
```

### Step 2: Reindex Existing Data

Use OpenSearch Reindex API with field transformation:

```bash
curl -X POST "localhost:9200/_reindex?wait_for_completion=false" \
  -H 'Content-Type: application/json' \
  -d '{
  "source": {
    "index": "text2dsl-queries"
  },
  "dest": {
    "index": "text2dsl-samples-sql"
  },
  "script": {
    "source": "ctx._source.natural_language_query = ctx._source.remove('\''question'\''); ctx._source.dsl_query = ctx._source.remove('\''sql'\''); ctx._source.dsl_query_analyzed = ctx._source.dsl_query; ctx._source.provider_type = '\''sql'\''; ctx._source.provider_id = '\''default'\''; ctx._source.status = '\''approved'\''; ctx._source.is_good_example = true; ctx._source.source = '\''sample'\''; ctx._source.query_intent = '\''unknown'\''; ctx._source.complexity_level = ctx._source.difficulty; ctx._source.involved_tables = ['\''unknown'\'']; ctx._source.usage_count = 0; ctx._source.success_rate = 1.0; ctx._source.avg_similarity_score = 0.0; ctx._source.embedding_model = '\''titan-v2'\''; ctx._source.indexed_at = new Date(); if (ctx._source.created_at == null) { ctx._source.created_at = new Date(); } ctx._source.updated_at = new Date();"
  }
}'
```

**Note**: This returns a task ID. Monitor progress with:
```bash
curl "localhost:9200/_tasks/{task_id}"
```

### Step 3: Validate Data Integrity

#### Count Documents
```bash
# Old index count
curl "localhost:9200/text2dsl-queries/_count" | jq .count

# New index count
curl "localhost:9200/text2dsl-samples-sql/_count" | jq .count
```

Counts should match.

#### Sample Document Comparison

**Old format**:
```bash
curl "localhost:9200/text2dsl-queries/_search?size=1&pretty"
```

**New format**:
```bash
curl "localhost:9200/text2dsl-samples-sql/_search?size=1&pretty"
```

Verify field mappings are correct.

#### Test Search Queries

Run sample hybrid search on new index:
```bash
curl -X POST "localhost:9200/text2dsl-samples-sql/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{
  "size": 5,
  "query": {
    "bool": {
      "must": [
        {
          "match": {
            "natural_language_query": {
              "query": "How many customers do we have?",
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
  }
}'
```

### Step 4: Create Index Aliases

Use aliases for seamless switching:

```bash
# Create alias pointing to new index
curl -X POST "localhost:9200/_aliases" \
  -H 'Content-Type: application/json' \
  -d '{
  "actions": [
    {
      "add": {
        "index": "text2dsl-samples-sql",
        "alias": "text2dsl-queries-active"
      }
    }
  ]
}'
```

### Step 5: Update Application Code

Update your application to use the new field names and index structure.

#### Python Example

**Before**:
```python
# Old code
query_body = {
    "query": {
        "match": {
            "question": user_query
        }
    }
}

results = await opensearch_client.search(
    index="text2dsl-queries",
    body=query_body
)

for hit in results["hits"]["hits"]:
    question = hit["_source"]["question"]
    sql = hit["_source"]["sql"]
```

**After**:
```python
# New code
query_body = {
    "query": {
        "bool": {
            "must": [
                {
                    "match": {
                        "natural_language_query": {
                            "query": user_query,
                            "boost": 0.3
                        }
                    }
                }
            ],
            "filter": [
                {"term": {"provider_type": "sql"}},
                {"term": {"status": "approved"}}
            ]
        }
    }
}

results = await opensearch_client.search(
    index="text2dsl-samples-sql",
    body=query_body
)

for hit in results["hits"]["hits"]:
    nl_query = hit["_source"]["natural_language_query"]
    dsl_query = hit["_source"]["dsl_query"]
    provider = hit["_source"]["provider_type"]
```

#### Update RAG Service

**File**: `src/text2x/services/rag_service.py`

Update the `_search_sample_queries` method to use new field names:

```python
# Change sample_index to provider-specific
sample_index = f"text2dsl-samples-{provider_id}"

# Update field references
"match": {
    "natural_language_query": {  # was: "question"
        "query": query,
        "boost": 0.3,
    }
}

# Access results with new field names
example = RAGExample(
    natural_language_query=source.get("natural_language_query", ""),  # was: "question"
    generated_query=source.get("dsl_query", ""),  # was: "sql"
    # ... other fields
)
```

### Step 6: Switch Traffic

Once validation is complete, switch application traffic:

```bash
# Update alias to point to new index
curl -X POST "localhost:9200/_aliases" \
  -H 'Content-Type: application/json' \
  -d '{
  "actions": [
    {
      "remove": {
        "index": "text2dsl-queries",
        "alias": "text2dsl-queries-active"
      }
    },
    {
      "add": {
        "index": "text2dsl-samples-sql",
        "alias": "text2dsl-queries-active"
      }
    }
  ]
}'
```

**Rollback plan**: If issues arise, reverse the alias change:
```bash
curl -X POST "localhost:9200/_aliases" \
  -H 'Content-Type: application/json' \
  -d '{
  "actions": [
    {
      "remove": {
        "index": "text2dsl-samples-sql",
        "alias": "text2dsl-queries-active"
      }
    },
    {
      "add": {
        "index": "text2dsl-queries",
        "alias": "text2dsl-queries-active"
      }
    }
  ]
}'
```

### Step 7: Monitor Performance

Monitor key metrics after migration:

```bash
# Search latency
curl "localhost:9200/_nodes/stats/indices/search?pretty" | jq '.nodes[].indices.search'

# Indexing rate
curl "localhost:9200/_nodes/stats/indices/indexing?pretty" | jq '.nodes[].indices.indexing'

# Index size
curl "localhost:9200/_cat/indices/text2dsl-samples-*?v&h=index,docs.count,store.size"
```

**Expected metrics**:
- Search latency: <100ms p50, <500ms p99
- Indexing rate: 100-500 docs/sec (bulk)
- Memory: ~5-8KB per document

### Step 8: Deprecate Old Index

After 30 days of stable operation:

```bash
# Create snapshot for backup
curl -X PUT "localhost:9200/_snapshot/my_backup/snapshot_text2dsl_queries?wait_for_completion=true" \
  -H 'Content-Type: application/json' \
  -d '{
  "indices": "text2dsl-queries",
  "ignore_unavailable": true,
  "include_global_state": false
}'

# Delete old index
curl -X DELETE "localhost:9200/text2dsl-queries"
```

## Migration Script

A Python script to automate the migration:

```python
#!/usr/bin/env python3
"""
Migrate from text2dsl-queries to text2dsl-samples-{provider} indices.
"""

import asyncio
import json
from opensearchpy import AsyncOpenSearch, RequestError
from typing import List, Dict, Any

class IndexMigration:
    def __init__(self, host: str = "localhost", port: int = 9200):
        self.client = AsyncOpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=None,
            use_ssl=False,
            verify_certs=False,
        )

    async def create_new_indices(self, mapping_file: str):
        """Create new provider-specific indices."""
        with open(mapping_file) as f:
            mapping = json.load(f)

        providers = ["sql", "mongodb", "splunk"]

        for provider in providers:
            index_name = f"text2dsl-samples-{provider}"
            try:
                await self.client.indices.create(
                    index=index_name,
                    body=mapping
                )
                print(f"✓ Created index: {index_name}")
            except RequestError as e:
                if "resource_already_exists_exception" in str(e):
                    print(f"⚠ Index {index_name} already exists")
                else:
                    raise

    async def reindex_data(self, source: str, dest: str):
        """Reindex data with field transformation."""
        reindex_body = {
            "source": {"index": source},
            "dest": {"index": dest},
            "script": {
                "source": """
                    ctx._source.natural_language_query = ctx._source.remove('question');
                    ctx._source.dsl_query = ctx._source.remove('sql');
                    ctx._source.dsl_query_analyzed = ctx._source.dsl_query;
                    ctx._source.provider_type = 'sql';
                    ctx._source.provider_id = 'default';
                    ctx._source.status = 'approved';
                    ctx._source.is_good_example = true;
                    ctx._source.source = 'sample';
                    ctx._source.query_intent = 'unknown';
                    ctx._source.complexity_level = ctx._source.difficulty;
                    ctx._source.involved_tables = ['unknown'];
                    ctx._source.usage_count = 0;
                    ctx._source.success_rate = 1.0;
                    ctx._source.avg_similarity_score = 0.0;
                    ctx._source.embedding_model = 'titan-v2';
                    ctx._source.indexed_at = new Date();
                    if (ctx._source.created_at == null) {
                        ctx._source.created_at = new Date();
                    }
                    ctx._source.updated_at = new Date();
                """
            }
        }

        response = await self.client.reindex(
            body=reindex_body,
            wait_for_completion=False
        )

        task_id = response["task"]
        print(f"Reindexing task started: {task_id}")

        # Monitor progress
        while True:
            task_status = await self.client.tasks.get(task_id=task_id)
            if task_status["completed"]:
                print(f"✓ Reindexing complete")
                break
            await asyncio.sleep(5)

    async def validate_counts(self, source: str, dest: str):
        """Validate document counts match."""
        source_count = await self.client.count(index=source)
        dest_count = await self.client.count(index=dest)

        source_total = source_count["count"]
        dest_total = dest_count["count"]

        if source_total == dest_total:
            print(f"✓ Document counts match: {source_total}")
            return True
        else:
            print(f"✗ Count mismatch: {source_total} vs {dest_total}")
            return False

    async def close(self):
        """Close OpenSearch client."""
        await self.client.close()

async def main():
    migration = IndexMigration()

    try:
        # Step 1: Create new indices
        print("Creating new indices...")
        await migration.create_new_indices("opensearch-index-mapping.json")

        # Step 2: Reindex data
        print("\nReindexing data...")
        await migration.reindex_data(
            source="text2dsl-queries",
            dest="text2dsl-samples-sql"
        )

        # Step 3: Validate
        print("\nValidating migration...")
        valid = await migration.validate_counts(
            source="text2dsl-queries",
            dest="text2dsl-samples-sql"
        )

        if valid:
            print("\n✓ Migration completed successfully!")
        else:
            print("\n✗ Migration validation failed")

    finally:
        await migration.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Rollback Procedure

If issues arise during migration:

1. **Stop application traffic** to new indices
2. **Switch alias** back to old index
3. **Investigate issues** in new indices
4. **Fix problems** and re-run migration
5. **Re-validate** before switching again

## Testing Checklist

Before going live, verify:

- [ ] All documents migrated (count matches)
- [ ] Field mappings correct (sample documents)
- [ ] Search queries work (hybrid search)
- [ ] Vector search functional (k-NN)
- [ ] Filters working (provider_type, status)
- [ ] Performance acceptable (latency <500ms)
- [ ] Application code updated
- [ ] Monitoring in place
- [ ] Rollback plan documented
- [ ] Team trained on new schema

## FAQ

### Q: Can I migrate gradually?
**A**: Yes, use aliases to route different query types to different indices during transition.

### Q: What happens to existing embeddings?
**A**: Embeddings are preserved during migration. The `embedding_model` field is added to track which model generated them.

### Q: Do I need to regenerate embeddings?
**A**: No, existing embeddings work with the new schema. Regenerate only if changing embedding models.

### Q: Can I keep both indices running?
**A**: Yes, use aliases to route traffic. Maintain old index as backup during validation period.

### Q: How long does migration take?
**A**: Depends on document count:
- 1K docs: ~30 seconds
- 10K docs: ~5 minutes
- 100K docs: ~30 minutes

## Support

For issues during migration:
- Check OpenSearch logs: `docker logs text2dsl-opensearch`
- Review task status: `GET /_tasks/{task_id}`
- Verify cluster health: `GET /_cluster/health`

---

**Version**: 1.0
**Last Updated**: 2026-02-11
**Author**: Schema Architect - opensearch-dsl-design team
