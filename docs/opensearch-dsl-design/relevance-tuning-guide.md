# OpenSearch Relevance Tuning Guide

## Overview

This guide provides detailed recommendations for tuning OpenSearch search queries to maximize relevance for DSL example retrieval in the text2DSL RAG system. Proper tuning ensures agents receive the most useful examples to guide query generation.

## Table of Contents

1. [Query Classification](#1-query-classification)
2. [Pattern Selection](#2-pattern-selection)
3. [Weight Tuning](#3-weight-tuning)
4. [Boost Tuning](#4-boost-tuning)
5. [Threshold Tuning](#5-threshold-tuning)
6. [Field-Specific Tuning](#6-field-specific-tuning)
7. [Performance vs Relevance Trade-offs](#7-performance-vs-relevance-trade-offs)
8. [A/B Testing Methodology](#8-ab-testing-methodology)
9. [Monitoring and Metrics](#9-monitoring-and-metrics)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Query Classification

Before searching, classify the user's query to select the optimal search pattern and parameters.

### 1.1 Query Characteristics

**Identify key signals:**

```python
def classify_query(user_query: str, context: dict) -> dict:
    """Classify query to determine search strategy."""

    classification = {
        "has_sql_keywords": False,
        "has_table_names": False,
        "is_conceptual": True,
        "complexity": "medium",
        "intent": None,
        "specificity": "medium"
    }

    # SQL keyword detection
    sql_keywords = [
        "SELECT", "JOIN", "WHERE", "GROUP BY", "HAVING",
        "ORDER BY", "LIMIT", "UNION", "SUBQUERY", "CTE"
    ]

    upper_query = user_query.upper()
    classification["has_sql_keywords"] = any(
        kw in upper_query for kw in sql_keywords
    )

    # Table name detection (from schema context)
    known_tables = context.get("tables", [])
    classification["has_table_names"] = any(
        table.lower() in user_query.lower()
        for table in known_tables
    )

    # Conceptual vs specific
    # Conceptual: "show insights", "analyze data", "find patterns"
    # Specific: "count customers", "join orders and products"
    conceptual_terms = ["insight", "analyze", "pattern", "trend", "report"]
    specific_terms = ["count", "sum", "average", "total", "join", "filter"]

    has_conceptual = any(term in user_query.lower() for term in conceptual_terms)
    has_specific = any(term in user_query.lower() for term in specific_terms)

    classification["is_conceptual"] = has_conceptual and not has_specific

    # Complexity estimation
    complexity_indicators = {
        "simple": ["count", "list", "show", "get", "find"],
        "complex": ["join", "subquery", "window", "recursive", "multiple"]
    }

    if any(ind in user_query.lower() for ind in complexity_indicators["complex"]):
        classification["complexity"] = "complex"
    elif any(ind in user_query.lower() for ind in complexity_indicators["simple"]):
        classification["complexity"] = "simple"

    # Intent detection
    intent_keywords = {
        "aggregation": ["count", "sum", "average", "total", "group"],
        "filter": ["where", "filter", "only", "exclude"],
        "join": ["join", "combine", "merge", "relate"],
        "window": ["rank", "row_number", "partition"],
        "subquery": ["nested", "subquery", "inner query"]
    }

    for intent, keywords in intent_keywords.items():
        if any(kw in user_query.lower() for kw in keywords):
            classification["intent"] = intent
            break

    # Specificity
    word_count = len(user_query.split())
    if word_count <= 3:
        classification["specificity"] = "low"
    elif word_count >= 8:
        classification["specificity"] = "high"

    return classification
```

### 1.2 Classification Examples

| Query | SQL Keywords | Tables | Conceptual | Complexity | Intent | Specificity |
|-------|--------------|--------|------------|------------|--------|-------------|
| "show customer insights" | No | Maybe | Yes | Simple | None | Low |
| "GROUP BY customer_id with SUM" | Yes | No | No | Medium | Aggregation | High |
| "join orders and customers on id" | Yes | Yes | No | Medium | Join | High |
| "count total orders" | No | Yes | No | Simple | Aggregation | Medium |
| "nested subquery with window function" | Yes | No | No | Complex | Window/Subquery | High |

---

## 2. Pattern Selection

Use the classification to select the optimal search pattern.

### 2.1 Decision Logic

```python
def select_pattern(classification: dict, context: dict) -> str:
    """Select best search pattern based on classification."""

    # Pattern 10: Known metadata - use filters
    if (classification["has_table_names"] and
        classification["intent"] is not None):
        return "metadata_filters"

    # Pattern 5: Known metadata for k-NN prefilter
    if (classification["intent"] is not None and
        classification["complexity"] != "medium"):
        return "knn_with_prefilter"

    # Pattern 4: Pure semantic for conceptual queries
    if classification["is_conceptual"] and classification["specificity"] == "low":
        return "pure_knn"

    # Pattern 2: Multi-match for high specificity
    if classification["specificity"] == "high" and classification["has_sql_keywords"]:
        return "multi_match"

    # Pattern 6: Default hybrid (most common)
    return "hybrid_script_score"

def get_search_params(classification: dict, pattern: str) -> dict:
    """Get search parameters based on classification."""

    params = {
        "vector_weight": 0.7,
        "keyword_weight": 0.3,
        "min_similarity": 0.7,
        "top_k": 5
    }

    # Adjust weights based on query type
    if classification["is_conceptual"]:
        params["vector_weight"] = 0.9
        params["keyword_weight"] = 0.1
    elif classification["has_sql_keywords"]:
        params["vector_weight"] = 0.5
        params["keyword_weight"] = 0.5

    # Adjust thresholds based on specificity
    if classification["specificity"] == "low":
        params["min_similarity"] = 0.65  # More lenient
    elif classification["specificity"] == "high":
        params["min_similarity"] = 0.75  # More strict

    # Adjust top_k based on complexity
    if classification["complexity"] == "complex":
        params["top_k"] = 10
    elif classification["complexity"] == "simple":
        params["top_k"] = 3

    return params
```

### 2.2 Pattern Selection Matrix

| Query Type | Characteristics | Recommended Pattern | Alternative |
|------------|----------------|---------------------|-------------|
| Conceptual | Vague, no keywords | Pure k-NN (4) | Hybrid high vector (6) |
| Specific SQL | SQL keywords present | Multi-match (2) | Hybrid high keyword (6) |
| Table-specific | Tables + intent known | Metadata filters (10) | k-NN prefilter (5) |
| Balanced | Mix of natural + technical | Hybrid script score (6) | RRF (7) |
| Complex multi-signal | Multiple factors | Custom scoring (9) | Metadata boost (8) |

---

## 3. Weight Tuning

### 3.1 Vector vs Keyword Weights

**Hybrid search combines two scores:**
```
final_score = (vector_weight × vector_score) + (keyword_weight × keyword_score)
```

**Guidelines:**

| Query Characteristic | Vector Weight | Keyword Weight | Example |
|---------------------|---------------|----------------|---------|
| Very conceptual | 0.85-0.95 | 0.05-0.15 | "show insights" |
| Conceptual | 0.75-0.85 | 0.15-0.25 | "analyze patterns" |
| **Balanced (default)** | **0.65-0.75** | **0.25-0.35** | "top customers" |
| Specific | 0.50-0.65 | 0.35-0.50 | "GROUP BY customer" |
| Very specific | 0.40-0.50 | 0.50-0.60 | "LEFT JOIN with WHERE" |

### 3.2 Tuning Procedure

1. **Start with defaults** (0.7 / 0.3)
2. **Run baseline queries** - Collect 20-30 representative queries
3. **Evaluate top-5 precision** - Manually assess relevance
4. **Adjust weights:**
   - If semantic matches too weak → Increase vector weight
   - If missing exact term matches → Increase keyword weight
5. **Re-test and iterate**

### 3.3 Weight Adjustment Examples

**Example 1: Conceptual query performing poorly**

```
Query: "show customer behavior patterns"
Issue: Top results are about specific SQL patterns, not conceptual
Current: vector=0.7, keyword=0.3
Solution: Increase vector weight to 0.85, reduce keyword to 0.15
```

**Example 2: Missing SQL keyword matches**

```
Query: "queries with GROUP BY and HAVING clause"
Issue: Results don't contain HAVING examples
Current: vector=0.7, keyword=0.3
Solution: Increase keyword weight to 0.5, reduce vector to 0.5
```

### 3.4 Dynamic Weight Adjustment

```python
def adjust_weights_dynamically(query: str, classification: dict) -> tuple:
    """Dynamically adjust weights based on query analysis."""

    base_vector = 0.7
    base_keyword = 0.3

    # Conceptual adjustment
    if classification["is_conceptual"]:
        base_vector += 0.2
        base_keyword -= 0.2

    # SQL keyword adjustment
    if classification["has_sql_keywords"]:
        sql_keyword_count = sum(
            1 for kw in ["JOIN", "GROUP", "HAVING", "WHERE", "SUBQUERY"]
            if kw in query.upper()
        )
        adjustment = min(0.2, sql_keyword_count * 0.1)
        base_keyword += adjustment
        base_vector -= adjustment

    # Table name adjustment
    if classification["has_table_names"]:
        base_keyword += 0.05
        base_vector -= 0.05

    # Normalize
    total = base_vector + base_keyword
    base_vector /= total
    base_keyword /= total

    return base_vector, base_keyword
```

---

## 4. Boost Tuning

Boost factors multiply the base relevance score to promote high-quality results.

### 4.1 Quality Boost Factors

| Factor | Recommended Range | Default | Rationale |
|--------|------------------|---------|-----------|
| `is_good_example` | 1.1 - 1.3 | 1.2 | Favor learning from good examples |
| `reviewed_by=expert` | 1.1 - 1.2 | 1.15 | Expert review = higher quality |
| `complexity_match` | 1.05 - 1.15 | 1.1 | Match query complexity |
| `table_overlap` | 1.2 - 1.5 | 1.25 | Same tables = relevant context |
| `intent_match` | 1.1 - 1.2 | 1.15 | Match query intent |

### 4.2 Recency Decay

**Favor recent examples:**

```json
{
  "gauss": {
    "created_at": {
      "origin": "now",
      "scale": "30d",
      "offset": "7d",
      "decay": 0.5
    }
  }
}
```

**Parameters:**
- `origin`: Reference point (now)
- `scale`: Half-life (30 days = score drops to 0.5)
- `offset`: Grace period (no decay for 7 days)
- `decay`: Decay rate at scale distance

**Tuning scale:**
- **Fast decay (15-20 days)**: Rapidly changing environments
- **Medium decay (30-45 days)**: Default, balanced
- **Slow decay (60-90 days)**: Stable environments

### 4.3 Boost Combination Modes

**score_mode**: How to combine multiple boost functions

| Mode | Formula | Use Case |
|------|---------|----------|
| `multiply` | score = func1 × func2 × func3 | Compounding boosts |
| `sum` | score = func1 + func2 + func3 | Additive boosts |
| `avg` | score = (func1 + func2 + func3) / 3 | Balanced average |
| `max` | score = max(func1, func2, func3) | Take best signal |
| `min` | score = min(func1, func2, func3) | Conservative |

**boost_mode**: How to combine query score with boost score

| Mode | Formula | Use Case |
|------|---------|----------|
| `multiply` | final = query_score × boost_score | Default, balanced |
| `sum` | final = query_score + boost_score | Additive influence |
| `replace` | final = boost_score | Ignore query score |
| `avg` | final = (query_score + boost_score) / 2 | Balanced |

### 4.4 Boost Tuning Example

```json
{
  "function_score": {
    "query": { "...base query..." },
    "functions": [
      {
        "filter": {"term": {"is_good_example": true}},
        "weight": 1.2
      },
      {
        "filter": {"term": {"complexity_level": "medium"}},
        "weight": 1.15
      },
      {
        "filter": {"terms": {"involved_tables": ["orders", "customers"]}},
        "weight": 1.3
      }
    ],
    "score_mode": "multiply",
    "boost_mode": "multiply",
    "max_boost": 2.5,
    "min_score": 0.5
  }
}
```

**Result:** Good medium-complexity example with matching tables gets:
- Base score: 10.0
- Boost: 1.2 × 1.15 × 1.3 = 1.794
- Final: 10.0 × 1.794 = 17.94 (capped at 25.0)

---

## 5. Threshold Tuning

### 5.1 Minimum Similarity Score

Controls precision vs recall trade-off.

| Threshold | Effect | Use Case |
|-----------|--------|----------|
| **0.8+** | High precision, low recall | Need very similar examples only |
| **0.7** (default) | Balanced | General purpose |
| **0.6** | Lower precision, high recall | Exploratory, broad coverage |
| **0.5** | Very permissive | Cold start, few examples |

### 5.2 Top-K Results

Number of examples to return.

| Query Complexity | Top-K | Rationale |
|-----------------|-------|-----------|
| Simple | 3-5 | Few examples sufficient |
| Medium | 5-7 | Default balanced |
| Complex | 7-10 | More context needed |
| Exploratory | 10-20 | Broad coverage |

### 5.3 Minimum Should Match

For multi-term queries, how many terms must match?

```json
{
  "match": {
    "question": {
      "query": "customer orders revenue total",
      "minimum_should_match": "75%"
    }
  }
}
```

| Setting | Match Requirement | Use Case |
|---------|------------------|----------|
| `100%` | All terms | Very strict |
| `75%` | 3 of 4 terms | High precision |
| **`50%`** (default) | 2 of 4 terms | Balanced |
| `30%` | 1-2 of 4 terms | High recall |
| `2<75% 5<50%` | Dynamic by term count | Adaptive |

### 5.4 Adaptive Threshold Logic

```python
def get_adaptive_thresholds(
    query: str,
    classification: dict,
    initial_results_count: int
) -> dict:
    """Adjust thresholds based on query and result count."""

    thresholds = {
        "min_similarity": 0.7,
        "top_k": 5,
        "minimum_should_match": "50%"
    }

    # If too few results, relax thresholds
    if initial_results_count < 3:
        thresholds["min_similarity"] = 0.6
        thresholds["top_k"] = 10
        thresholds["minimum_should_match"] = "30%"

    # If query is complex, get more examples
    if classification["complexity"] == "complex":
        thresholds["top_k"] = 10

    # If query is very specific, be stricter
    if classification["specificity"] == "high":
        thresholds["min_similarity"] = 0.75
        thresholds["minimum_should_match"] = "75%"

    return thresholds
```

---

## 6. Field-Specific Tuning

### 6.1 Field Boost Values

Control which fields contribute most to relevance.

```json
{
  "multi_match": {
    "query": "customer orders",
    "fields": [
      "question^3.0",
      "sql^2.0",
      "involved_tables^1.5",
      "query_intent^1.0"
    ]
  }
}
```

**Recommended boosts:**

| Field | Boost | Rationale |
|-------|-------|-----------|
| `question` | 2.5-3.5 | Primary natural language signal |
| `sql` | 1.5-2.5 | Important for SQL pattern matching |
| `involved_tables` | 1.2-1.8 | Context relevance |
| `query_intent` | 0.8-1.2 | Secondary signal |
| `complexity_level` | 0.5-1.0 | Tertiary signal |

### 6.2 Analyzer Configuration

Different fields need different analyzers.

| Field | Analyzer | Rationale |
|-------|----------|-----------|
| `question` | `standard` | Tokenize natural language |
| `sql` | `keyword` or `whitespace` | Preserve SQL structure |
| `involved_tables` | `keyword` | Exact table name matching |
| `provider_id` | `keyword` | Exact match only |
| `status` | `keyword` | Exact match only |

### 6.3 Multi-Match Type

```json
{
  "multi_match": {
    "query": "...",
    "type": "best_fields",
    "tie_breaker": 0.3
  }
}
```

| Type | Behavior | Use Case |
|------|----------|----------|
| `best_fields` | Use best matching field | Default, clear winner |
| `most_fields` | Combine all field scores | Broad coverage |
| `cross_fields` | Treat as one big field | Multi-word terms |
| `phrase` | Require phrase match | Exact phrase queries |

**tie_breaker**: How much to consider other fields
- `0.0`: Only best field counts
- `0.3`: Add 30% of other fields (default)
- `1.0`: Treat all fields equally

---

## 7. Performance vs Relevance Trade-offs

### 7.1 Search Strategy Performance

| Pattern | Latency | Accuracy | Resource Usage |
|---------|---------|----------|----------------|
| Simple match (1) | ~10ms | Low-Medium | Very Low |
| Multi-match (2) | ~15ms | Medium | Low |
| Pure k-NN (4) | ~30ms | Medium-High | Medium |
| k-NN prefilter (5) | ~20ms | High | Medium |
| Hybrid script score (6) | ~50ms | High | High |
| RRF (7) | ~40ms | High | Medium |
| Custom scoring (9) | ~80ms | Highest | Very High |

### 7.2 Optimization Strategies

**When to use faster patterns:**
- Real-time user-facing queries (<100ms requirement)
- High query volume (>100 QPS)
- Limited compute resources

**When to use slower patterns:**
- Batch processing
- Critical queries requiring highest accuracy
- Low query volume (<10 QPS)

### 7.3 Caching Strategy

```python
import hashlib
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_search(query_hash: str, provider_id: str) -> list:
    """Cache search results for identical queries."""
    # Actual search implementation
    pass

def search_with_cache(query: str, provider_id: str, ttl_minutes: int = 10) -> list:
    """Search with caching."""
    query_hash = hashlib.md5(f"{query}:{provider_id}".encode()).hexdigest()

    # Check cache (implement with Redis or similar)
    cached = get_from_cache(query_hash)
    if cached and not is_expired(cached, ttl_minutes):
        return cached

    # Perform search
    results = perform_opensearch_query(query, provider_id)

    # Store in cache
    set_in_cache(query_hash, results, ttl_minutes)

    return results
```

### 7.4 Performance Optimization Checklist

- ✅ Use filters instead of must clauses when possible
- ✅ Pre-filter k-NN with metadata to reduce candidate set
- ✅ Cache frequent queries (5-10 min TTL)
- ✅ Use RRF instead of script_score for high-load scenarios
- ✅ Index optimization: Proper shard count, replica count
- ✅ Monitor slow queries and optimize patterns
- ✅ Use async/parallel queries where applicable

---

## 8. A/B Testing Methodology

### 8.1 Test Setup

**Test two search strategies:**

```python
def ab_test_search(query: str, provider_id: str, user_id: str) -> dict:
    """A/B test different search strategies."""

    # Assign user to variant
    variant = "A" if hash(user_id) % 2 == 0 else "B"

    if variant == "A":
        # Control: Current strategy
        results = search_hybrid(query, provider_id, vector_weight=0.7)
    else:
        # Treatment: New strategy
        results = search_hybrid(query, provider_id, vector_weight=0.8)

    # Log for analysis
    log_search_results(user_id, variant, query, results)

    return {
        "results": results,
        "variant": variant
    }
```

### 8.2 Metrics to Track

**Primary Metrics:**
- **Click-Through Rate (CTR)**: Which results do users select?
- **Success Rate**: Does user refine query or accept result?
- **Time to Success**: How quickly do users find relevant example?

**Secondary Metrics:**
- **Query Refinements**: How often do users modify query?
- **Result Diversity**: Are results from different complexity/intent?
- **Null Rate**: How often are there <3 results?

### 8.3 Evaluation Procedure

1. **Run test for 1-2 weeks** with sufficient traffic
2. **Collect metrics** for both variants
3. **Statistical significance** - Use t-test or chi-square
4. **Manual evaluation** - Sample 50-100 queries, assess relevance
5. **Make decision** - Roll out winner or iterate

### 8.4 Example Test Plan

```
Test: Increase vector weight for conceptual queries

Hypothesis: Conceptual queries will have better relevance with higher vector weight

Variants:
- A (Control): vector_weight=0.7 for all queries
- B (Treatment): vector_weight=0.85 for conceptual, 0.7 for others

Success Criteria:
- CTR increase >5% for conceptual queries (p<0.05)
- No degradation in non-conceptual queries
- Top-5 precision >80% (manual eval)

Duration: 2 weeks
Sample Size: 1000+ conceptual queries
```

---

## 9. Monitoring and Metrics

### 9.1 Query Performance Metrics

**Track for each query:**

```python
{
  "query_id": "uuid",
  "query_text": "...",
  "provider_id": "postgres",
  "pattern_used": "hybrid_script_score",
  "vector_weight": 0.7,
  "keyword_weight": 0.3,
  "latency_ms": 45,
  "num_results": 5,
  "top_score": 0.92,
  "min_score": 0.71,
  "cache_hit": false,
  "timestamp": "2026-02-11T16:00:00Z"
}
```

### 9.2 Relevance Metrics

**Manual Evaluation (sample 100 queries/week):**

```
Top-K Precision = (Relevant results in top-K) / K

Top-1 Precision: >60%
Top-5 Precision: >80%
Top-10 Precision: >70%
```

**Automated Signals:**
- **Click position**: Lower is better (clicked result rank)
- **Dwell time**: Longer = more relevant
- **Query refinement rate**: Lower is better
- **Zero results rate**: <5%

### 9.3 Performance Monitoring

**Set up alerts:**

```yaml
alerts:
  - name: search_latency_high
    condition: p95_latency > 200ms
    action: notify_team

  - name: zero_results_rate_high
    condition: zero_results_rate > 10%
    action: investigate_patterns

  - name: opensearch_errors
    condition: error_rate > 1%
    action: page_oncall
```

### 9.4 Dashboard Metrics

**Real-time dashboard should show:**
- Queries per second
- P50, P95, P99 latency
- Error rate
- Zero results rate
- Pattern usage distribution
- Top queries (by frequency)
- Slow queries (>200ms)
- Cache hit rate

---

## 10. Troubleshooting

### 10.1 Common Issues

#### Issue 1: Poor Relevance for Conceptual Queries

**Symptoms:**
- Top results are too specific
- Missing semantic matches

**Diagnosis:**
```python
# Check vector weight
print(f"Vector weight: {vector_weight}")  # Should be 0.8+ for conceptual

# Check embedding quality
similarity = cosine_similarity(query_embedding, result_embeddings)
print(f"Similarity scores: {similarity}")  # Should be >0.7
```

**Solutions:**
- Increase vector weight to 0.85-0.9
- Lower min_similarity threshold to 0.65
- Check embedding model quality
- Add more conceptual examples to index

#### Issue 2: Missing Exact Keyword Matches

**Symptoms:**
- Results don't contain specific SQL terms
- Low precision for specific queries

**Diagnosis:**
```python
# Check keyword weight
print(f"Keyword weight: {keyword_weight}")  # Should be 0.5+ for specific

# Check if terms are in results
for result in results:
    print(f"Query terms in result: {count_matching_terms(query, result)}")
```

**Solutions:**
- Increase keyword weight to 0.5-0.6
- Use multi_match across question and sql fields
- Add field boosts (sql^2)
- Check analyzer configuration

#### Issue 3: High Latency

**Symptoms:**
- Queries taking >200ms
- Performance degradation

**Diagnosis:**
```python
# Check pattern used
print(f"Pattern: {pattern}")  # script_score is slowest

# Check candidate set size
print(f"k-NN candidates: {k}")  # High k = slower

# Check OpenSearch cluster health
print(cluster.health())
```

**Solutions:**
- Use RRF instead of script_score
- Reduce k-NN k parameter (try 10-20)
- Pre-filter k-NN with metadata
- Enable query caching
- Scale OpenSearch cluster

#### Issue 4: Too Few Results

**Symptoms:**
- <3 results returned
- High zero results rate

**Diagnosis:**
```python
# Check threshold
print(f"Min similarity: {min_similarity}")  # Too high?

# Check filter constraints
print(f"Filters: {filters}")  # Too restrictive?

# Check index size
print(f"Total examples: {index_count}")  # Enough data?
```

**Solutions:**
- Lower min_similarity to 0.6
- Relax filters (remove intent, complexity)
- Add more examples to index
- Include sample queries
- Use broader query pattern (pure k-NN)

#### Issue 5: Low Diversity in Results

**Symptoms:**
- All results very similar
- Same complexity/intent

**Diagnosis:**
```python
# Check result similarity
for i, r1 in enumerate(results):
    for r2 in results[i+1:]:
        sim = similarity(r1, r2)
        print(f"Result similarity: {sim}")  # >0.95 = duplicates
```

**Solutions:**
- Use collapse feature to deduplicate
- Boost different complexity levels
- Include metadata filters for diversity
- Increase top-k and diversify client-side

### 10.2 Debugging Queries

**Add explain=true to understand scoring:**

```json
{
  "query": { "..." },
  "explain": true
}
```

**Inspect explain output:**
```json
{
  "_explanation": {
    "value": 15.2,
    "description": "sum of:",
    "details": [
      {
        "value": 10.5,
        "description": "weight(question:customer), result of:",
        "details": [...]
      },
      {
        "value": 4.7,
        "description": "script score function, computed with script:",
        "details": [...]
      }
    ]
  }
}
```

### 10.3 Iterative Tuning Process

```
1. Identify issue (low relevance, high latency, etc.)
   ↓
2. Diagnose root cause (check weights, patterns, thresholds)
   ↓
3. Form hypothesis (e.g., "increasing vector weight will help")
   ↓
4. Make controlled change (adjust one parameter)
   ↓
5. Test with representative queries (20-50 queries)
   ↓
6. Measure impact (precision, latency, etc.)
   ↓
7. A/B test if promising (statistical validation)
   ↓
8. Roll out or revert
   ↓
9. Monitor and iterate
```

---

## Summary

**Quick Reference Card:**

| Query Type | Pattern | Vector:Keyword | Min Score | Top-K |
|------------|---------|----------------|-----------|-------|
| Conceptual | pure_knn | 0.9:0.1 | 0.65 | 5 |
| Balanced | hybrid_script | 0.7:0.3 | 0.70 | 5 |
| Specific SQL | multi_match | 0.5:0.5 | 0.75 | 5 |
| Table-specific | metadata_filter | N/A | 0.70 | 5-10 |
| Complex | custom_scoring | 0.7:0.3 | 0.65 | 10 |

**Remember:**
- Start with defaults, tune based on metrics
- A/B test major changes
- Monitor performance and relevance continuously
- Iterate based on user feedback and data
- Document all tuning decisions and results

---

**For questions or issues, contact the Query Patterns Analyst or refer to search-query-templates.json for implementation details.**
