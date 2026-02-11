# Search Query Patterns Plan - Query Patterns Analyst

## Executive Summary

This plan outlines the design of OpenSearch query patterns for finding relevant DSL examples to power the text2DSL RAG system. The goal is to provide fast, accurate, and semantically relevant search capabilities that agents can use during query generation.

## 1. Current State Analysis

### Existing Implementation
From code exploration, the system currently has:

**OpenSearch Integration:**
- Index: `text2dsl-queries` (sample queries) and dynamic RAG index
- Embedding model: AWS Bedrock Titan v2 (1024 dimensions)
- k-NN algorithm: HNSW with cosine similarity
- Hybrid search: Combines vector + BM25 keyword matching (70% vector, 30% keyword)

**RAG Service (`src/text2x/services/rag_service.py`):**
- `search_examples()` method supports hybrid retrieval
- Searches both dynamic RAG examples and static sample queries
- Filters by provider_id, query_intent, min_similarity
- Merges and ranks results by similarity score

**OpenSearch Service (`src/text2x/services/opensearch_service.py`):**
- `search_similar()` method implements hybrid search
- `_build_vector_query()` for pure k-NN search
- `_build_hybrid_query()` for combined vector + keyword search
- Script scoring for weighted combination

**Sample Data:**
- 30 sample queries in `tests/fixtures/sample_queries.json`
- Difficulty levels: simple, medium, complex
- E-commerce domain (customers, orders, products)

### Current Gaps
1. **Limited query pattern diversity** - Only basic hybrid search implemented
2. **No re-ranking strategies** - Results rely solely on initial scoring
3. **Missing specialized filters** - No query type classification or metadata filtering
4. **No query expansion** - No synonym handling or semantic expansion
5. **Limited tuning guidance** - No documented relevance tuning parameters
6. **No multi-match strategies** - Single field keyword matching only

## 2. Requirements

### Functional Requirements
1. **Keyword Search**: Match exact terms, phrases, and SQL patterns
2. **Semantic Search**: Find conceptually similar queries using vector embeddings
3. **Hybrid Search**: Combine keyword + semantic with configurable weights
4. **Re-ranking**: Improve result ordering with RRF or custom scoring
5. **Filtering**: Support query type, difficulty, provider, tables, intent
6. **Query Expansion**: Handle synonyms and semantic variations
7. **Multi-field Search**: Search across question, SQL, tables, intent fields

### Non-Functional Requirements
1. **Performance**: Sub-200ms response time for p95
2. **Accuracy**: Top-5 results should include relevant examples (>80% precision)
3. **Scalability**: Support 10K+ indexed examples per workspace
4. **Configurability**: Tunable weights, thresholds, and ranking parameters

## 3. Search Query Pattern Designs

### 3.1 Keyword Search Patterns

#### Pattern 1: Simple Match Query
**Use Case**: Basic keyword matching on natural language queries
**Performance**: Fast (BM25), good for exact term matches
**Implementation**:
```json
{
  "query": {
    "bool": {
      "must": [
        {
          "match": {
            "question": {
              "query": "{{user_query}}",
              "operator": "or"
            }
          }
        }
      ],
      "filter": [
        {"term": {"status": "approved"}},
        {"term": {"provider_id": "{{provider}}"}}
      ]
    }
  }
}
```

#### Pattern 2: Multi-Match Query
**Use Case**: Search across multiple fields (question, SQL, tables)
**Performance**: Medium, more comprehensive coverage
**Implementation**:
```json
{
  "query": {
    "bool": {
      "must": [
        {
          "multi_match": {
            "query": "{{user_query}}",
            "fields": [
              "question^3",
              "sql^2",
              "involved_tables^1.5",
              "query_intent^1"
            ],
            "type": "best_fields",
            "tie_breaker": 0.3
          }
        }
      ],
      "filter": [
        {"term": {"status": "approved"}},
        {"term": {"provider_id": "{{provider}}"}}
      ]
    }
  }
}
```

#### Pattern 3: Query String Search
**Use Case**: Advanced queries with operators (AND, OR, phrase, wildcard)
**Performance**: Flexible but requires query sanitization
**Implementation**:
```json
{
  "query": {
    "bool": {
      "must": [
        {
          "query_string": {
            "query": "{{sanitized_query}}",
            "fields": ["question^3", "sql^2"],
            "default_operator": "OR",
            "analyze_wildcard": true
          }
        }
      ],
      "filter": [
        {"term": {"status": "approved"}},
        {"term": {"provider_id": "{{provider}}"}}
      ]
    }
  }
}
```

### 3.2 Semantic/Vector Search Patterns

#### Pattern 4: Pure k-NN Search
**Use Case**: Find semantically similar queries using embeddings
**Performance**: Excellent for conceptual similarity
**Implementation**:
```json
{
  "size": 10,
  "query": {
    "bool": {
      "must": [
        {
          "knn": {
            "embedding": {
              "vector": "{{query_embedding}}",
              "k": 10
            }
          }
        }
      ],
      "filter": [
        {"term": {"status": "approved"}},
        {"term": {"provider_id": "{{provider}}"}}
      ]
    }
  }
}
```

#### Pattern 5: k-NN with Pre-Filter
**Use Case**: Limit k-NN search to specific metadata (difficulty, intent)
**Performance**: Faster, more targeted results
**Implementation**:
```json
{
  "size": 10,
  "query": {
    "bool": {
      "must": [
        {
          "knn": {
            "embedding": {
              "vector": "{{query_embedding}}",
              "k": 10,
              "filter": {
                "bool": {
                  "must": [
                    {"term": {"status": "approved"}},
                    {"term": {"provider_id": "{{provider}}"}},
                    {"term": {"difficulty": "{{difficulty}}"}},
                    {"term": {"query_intent": "{{intent}}"}}
                  ]
                }
              }
            }
          }
        }
      ]
    }
  }
}
```

### 3.3 Hybrid Search Patterns

#### Pattern 6: Script Score Hybrid (Current Implementation)
**Use Case**: Weighted combination of vector + keyword scores
**Performance**: Balanced relevance, slower due to script scoring
**Implementation**:
```json
{
  "size": 10,
  "query": {
    "script_score": {
      "query": {
        "bool": {
          "should": [
            {
              "match": {
                "question": {
                  "query": "{{user_query}}",
                  "boost": 0.3
                }
              }
            }
          ],
          "filter": [
            {"term": {"status": "approved"}},
            {"term": {"provider_id": "{{provider}}"}}
          ]
        }
      },
      "script": {
        "source": "float vectorScore = cosineSimilarity(params.query_vector, 'embedding') + 1.0; float keywordScore = _score; return 0.7 * vectorScore + 0.3 * keywordScore;",
        "params": {
          "query_vector": "{{query_embedding}}"
        }
      }
    }
  }
}
```

**Tuning Parameters:**
- `vector_weight`: Default 0.7 (favor semantic similarity)
- `keyword_weight`: Default 0.3 (boost exact matches)
- Adjust weights based on query characteristics:
  - High vector weight (0.8-0.9) for vague/conceptual queries
  - High keyword weight (0.5-0.6) for specific term queries

#### Pattern 7: RRF Hybrid (Reciprocal Rank Fusion)
**Use Case**: Combine vector + keyword results using rank-based fusion
**Performance**: Often better than weighted scoring, no script overhead
**Implementation** (requires two queries + client-side merge):
```python
# Query 1: Vector search
vector_results = search_knn(query_embedding, k=20)

# Query 2: Keyword search
keyword_results = search_match(user_query, k=20)

# RRF Fusion (client-side)
def reciprocal_rank_fusion(results_list, k=60):
    scores = {}
    for results in results_list:
        for rank, doc_id in enumerate(results):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

fused_results = reciprocal_rank_fusion([vector_results, keyword_results])
```

**RRF Formula**: `score = sum(1 / (k + rank))` where k=60 (default)

### 3.4 Advanced Re-Ranking Patterns

#### Pattern 8: Boost by Metadata
**Use Case**: Promote results based on quality signals
**Performance**: Fast, combines with any base query
**Implementation**:
```json
{
  "query": {
    "function_score": {
      "query": {
        "// base query here (match, knn, hybrid)"
      },
      "functions": [
        {
          "filter": {"term": {"is_good_example": true}},
          "weight": 1.2
        },
        {
          "filter": {"term": {"reviewed_by": "expert"}},
          "weight": 1.15
        },
        {
          "filter": {"term": {"complexity_level": "{{matched_complexity}}"}},
          "weight": 1.1
        },
        {
          "gauss": {
            "created_at": {
              "origin": "now",
              "scale": "30d",
              "decay": 0.5
            }
          }
        }
      ],
      "score_mode": "multiply",
      "boost_mode": "multiply"
    }
  }
}
```

**Boost Factors:**
- `is_good_example=true`: 1.2x boost
- `reviewed_by=expert`: 1.15x boost
- Matching complexity level: 1.1x boost
- Recency decay: Favor recent examples (30-day half-life)

#### Pattern 9: Custom Scoring with Multiple Signals
**Use Case**: Complex relevance logic combining multiple factors
**Performance**: Flexible but computationally expensive
**Implementation**:
```json
{
  "query": {
    "script_score": {
      "query": {
        "// base query"
      },
      "script": {
        "source": "
          float baseScore = _score;
          float vectorScore = cosineSimilarity(params.query_vector, 'embedding') + 1.0;
          float qualityBoost = doc['is_good_example'].value ? 1.2 : 1.0;
          float complexityMatch = doc['complexity_level'].value == params.target_complexity ? 1.15 : 1.0;
          float tableOverlap = 0.0;
          for (table in params.target_tables) {
            if (doc['involved_tables'].contains(table)) {
              tableOverlap += 0.1;
            }
          }
          return baseScore * vectorScore * qualityBoost * complexityMatch * (1.0 + tableOverlap);
        ",
        "params": {
          "query_vector": "{{embedding}}",
          "target_complexity": "{{complexity}}",
          "target_tables": ["customers", "orders"]
        }
      }
    }
  }
}
```

### 3.5 Filtering and Query Classification

#### Pattern 10: Metadata Filters
**Use Case**: Narrow results by query characteristics
**Implementation**:
```json
{
  "query": {
    "bool": {
      "must": [
        "// main search query"
      ],
      "filter": [
        {"term": {"status": "approved"}},
        {"term": {"provider_id": "{{provider}}"}},
        {"term": {"query_intent": "aggregation"}},
        {"terms": {"involved_tables": ["orders", "customers"]}},
        {"range": {"complexity_level": {"gte": "medium"}}},
        {"range": {"created_at": {"gte": "now-6M"}}}
      ]
    }
  }
}
```

**Filter Categories:**
- **Status**: `approved`, `rejected`, `pending_review`
- **Provider**: `postgres`, `mongodb`, `splunk`, etc.
- **Intent**: `aggregation`, `filter`, `join`, `window`, `subquery`, etc.
- **Tables**: Array of involved table names
- **Complexity**: `simple`, `medium`, `complex`
- **Recency**: Time-based filters

## 4. Search Strategy Decision Tree

```
User Query Analysis
├─ Has specific table names?
│  ├─ YES → Use Pattern 10 (metadata filters)
│  └─ NO → Continue
├─ Is query vague/conceptual?
│  ├─ YES → Use Pattern 4 (pure k-NN, high vector weight)
│  └─ NO → Continue
├─ Has specific SQL keywords (JOIN, GROUP BY, etc)?
│  ├─ YES → Use Pattern 6 (hybrid with high keyword weight)
│  └─ NO → Continue
├─ Requires broad coverage?
│  ├─ YES → Use Pattern 7 (RRF hybrid)
│  └─ NO → Use Pattern 6 (script score hybrid - default)
└─ Post-processing:
   ├─ Apply Pattern 8 (metadata boost)
   └─ Return top-K results
```

## 5. Relevance Tuning Recommendations

### 5.1 Query Understanding
- Classify query complexity (simple/medium/complex)
- Extract table names, SQL keywords, intent signals
- Determine if query is conceptual vs. specific

### 5.2 Weight Tuning
| Query Type | Vector Weight | Keyword Weight | Rationale |
|------------|---------------|----------------|-----------|
| Conceptual | 0.8-0.9 | 0.1-0.2 | Favor semantic similarity |
| Specific terms | 0.4-0.5 | 0.5-0.6 | Favor exact keyword matches |
| SQL patterns | 0.6 | 0.4 | Balance both signals |
| Default | 0.7 | 0.3 | Current optimal balance |

### 5.3 Boost Tuning
- Good examples: 1.1-1.3x boost (current: 1.2x)
- Expert reviewed: 1.1-1.2x boost (current: 1.15x)
- Complexity match: 1.05-1.15x boost (current: 1.1x)
- Recency decay: 30-90 day scale (current: not implemented)

### 5.4 Threshold Tuning
- Min similarity score: 0.6-0.8 (current: 0.7)
  - Lower (0.6) for broader recall
  - Higher (0.8) for precision
- Top-K results: 3-10 (current: 5)
  - Fewer for simple queries
  - More for complex/ambiguous queries

## 6. Implementation Plan

### Phase 1: Document Current Patterns (This Task)
- ✅ Analyze existing implementation
- ✅ Design query pattern templates
- Create `search-query-templates.json` with examples
- Document relevance tuning guidelines

### Phase 2: Enhancements (Integration Engineer)
- Implement query classification logic
- Add RRF hybrid search option
- Implement metadata boost scoring
- Add configurable weight parameters

### Phase 3: Testing & Tuning (Post-Integration)
- A/B test different strategies
- Benchmark query performance
- Tune weights and thresholds based on metrics
- Collect user feedback on result relevance

## 7. Deliverables

1. **search-query-templates.json**: Concrete OpenSearch DSL examples for each pattern
2. **relevance-tuning-guide.md**: Detailed tuning recommendations and decision logic
3. This plan document for team review

## 8. Coordination Points

### With Schema Architect
- Ensure index mapping supports all query patterns
- Verify field analyzers (standard vs. keyword)
- Confirm k-NN configuration (HNSW params)

### With Embeddings Expert
- Validate embedding dimension compatibility (1024)
- Confirm cosine similarity metric choice
- Discuss embedding quality for domain-specific queries

### With Integration Engineer
- Define agent invocation interface
- Specify query result format
- Discuss caching strategies
- Plan performance monitoring

## 9. Success Metrics

- **Relevance**: Top-5 precision >80% (manual evaluation)
- **Performance**: p95 latency <200ms
- **Coverage**: >90% of queries return ≥3 relevant results
- **Diversity**: Results span different SQL patterns/complexity levels

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Script scoring overhead | High latency | Implement RRF as alternative, benchmark both |
| Embedding quality varies | Poor semantic matches | Tune keyword weight higher, add synonym expansion |
| Limited sample data | Cannot tune effectively | Generate synthetic queries, use production logs |
| Cold start problem | No results for new workspaces | Include cross-workspace sample queries |

---

## Next Steps

1. **Get team lead approval** on this plan
2. **Coordinate with Schema Architect** on mapping validation
3. **Coordinate with Embeddings Expert** on similarity metrics
4. **Create search-query-templates.json** with concrete examples
5. **Write relevance-tuning-guide.md** with detailed recommendations
6. **Hand off to Integration Engineer** for implementation
