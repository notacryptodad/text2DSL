# Expert Review Queue API Reference

## Overview
The Expert Review Queue allows domain experts to review, approve, reject, or correct queries that require human oversight. This creates a continuous feedback loop that improves the RAG index and query generation accuracy.

## API Endpoints

### 1. Get Review Queue
```http
GET /api/v1/review/queue?page=1&page_size=20&provider_id=postgresql
```

**Query Parameters:**
- `page` (optional, default: 1): Page number
- `page_size` (optional, default: 20, max: 100): Items per page
- `provider_id` (optional): Filter by provider
- `status_filter` (optional): Filter by status (pending_review, approved, rejected)

**Response:**
```json
[
  {
    "id": "uuid",
    "conversation_id": "uuid",
    "turn_id": "uuid",
    "provider_id": "postgresql",
    "user_input": "Show me all orders from last month",
    "generated_query": "SELECT * FROM orders WHERE created_at >= DATE_TRUNC('month', NOW() - INTERVAL '1 month')",
    "confidence_score": 0.65,
    "validation_status": "valid",
    "reason_for_review": "low_confidence",
    "created_at": "2024-01-15T10:30:00Z",
    "priority": 35
  }
]
```

**Priority Levels:**
- 100: Validation failures (highest)
- 50: Negative user feedback
- 20-70: Low confidence (scaled by score)
- 10: Multiple clarifications (lowest)

---

### 2. Get Review Item Details
```http
GET /api/v1/review/queue/{item_id}
```

**Response:**
```json
{
  "id": "uuid",
  "provider_id": "postgresql",
  "natural_language_query": "Show me all orders from last month",
  "generated_query": "SELECT * FROM orders WHERE ...",
  "is_good_example": true,
  "status": "pending_review",
  "involved_tables": ["orders"],
  "query_intent": "filter",
  "complexity_level": "simple",
  "reviewed_by": null,
  "reviewed_at": null,
  "expert_corrected_query": null,
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### 3. Submit Review Decision
```http
PUT /api/v1/review/queue/{item_id}
```

**Request Body:**
```json
{
  "approved": true,
  "corrected_query": "SELECT * FROM orders WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')",
  "feedback": "Fixed date calculation to use CURRENT_DATE"
}
```

**Fields:**
- `approved` (required): Boolean indicating approval/rejection
- `corrected_query` (optional): Expert-corrected query (required if correcting)
- `feedback` (optional): Review notes/feedback

**Response:**
```json
{
  "id": "uuid",
  "provider_id": "postgresql",
  "natural_language_query": "Show me all orders from last month",
  "generated_query": "SELECT * FROM orders WHERE ...",
  "is_good_example": false,
  "status": "approved",
  "involved_tables": ["orders"],
  "query_intent": "filter",
  "complexity_level": "simple",
  "reviewed_by": "expert",
  "reviewed_at": "2024-01-15T11:00:00Z",
  "expert_corrected_query": "SELECT * FROM orders WHERE ...",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### 4. Get Review Statistics
```http
GET /api/v1/review/stats
```

**Response:**
```json
{
  "pending_reviews": 15,
  "status_breakdown": {
    "pending_review": 15,
    "approved": 142,
    "rejected": 8
  },
  "by_provider": {
    "postgresql": 10,
    "athena": 5
  },
  "oldest_pending": "2024-01-10T08:00:00Z",
  "oldest_age_hours": 120
}
```

---

## Review Workflow

### 1. Item Auto-Queued (System)
When the query generation system detects issues:
- Low confidence (< 0.7)
- Validation failure
- User thumbs-down
- Multiple clarifications (≥ 3)

### 2. Expert Reviews (Human)
The expert:
1. Fetches queue: `GET /review/queue`
2. Reviews item details: `GET /review/queue/{id}`
3. Makes decision:
   - **Approve**: Good query, add to RAG as-is
   - **Reject**: Bad query, mark to avoid
   - **Correct**: Fix query, then approve

### 3. RAG Index Updated (System)
- Approved items → immediately available for retrieval
- Corrections → used instead of original query
- Rejected items → tracked but not used

### 4. Future Queries Improved (System)
Similar user queries now retrieve the reviewed examples, improving accuracy.

---

## Example Workflows

### Approve Good Query
```bash
# 1. Get queue
curl GET /api/v1/review/queue

# 2. Review looks good, approve
curl -X PUT /api/v1/review/queue/{id} \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "feedback": "Query is correct"}'
```

### Correct and Approve
```bash
# Query has a minor issue, correct it
curl -X PUT /api/v1/review/queue/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "corrected_query": "SELECT * FROM orders WHERE status = '\''completed'\''",
    "feedback": "Fixed string quoting"
  }'
```

### Reject Bad Query
```bash
# Query is fundamentally wrong, reject
curl -X PUT /api/v1/review/queue/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "approved": false,
    "feedback": "Query uses wrong table"
  }'
```

---

## Integration with Review Service

### ReviewService Methods

```python
from text2x.services import ReviewService, ReviewTrigger, ReviewDecision

review_service = ReviewService()

# Auto-queue a turn for review
example_id = await review_service.auto_queue_for_review(
    turn_id=turn_id,
    trigger=ReviewTrigger.LOW_CONFIDENCE,
    provider_id="postgresql",
)

# Process expert decision
result = await review_service.process_review_decision(
    item_id=example_id,
    decision=ReviewDecision.CORRECT,
    reviewer="expert_alice",
    corrected_query="SELECT ...",
    notes="Fixed date handling",
)

# Check if should queue
should_queue, trigger = await review_service.should_queue_for_review(
    confidence_score=0.65,
    validation_passed=True,
    has_negative_feedback=False,
)
```

### RAGService Methods

```python
from text2x.services import RAGService

rag_service = RAGService()

# Add example directly (bypass review)
example = await rag_service.add_example(
    nl_query="Show all users",
    generated_query="SELECT * FROM users",
    is_good=True,
    provider_id="postgresql",
    auto_approve=True,  # Skip review queue
)

# Search for similar examples
results = await rag_service.search_examples(
    query="Show me orders",
    provider_id="postgresql",
    limit=5,
)

# Get statistics
stats = await rag_service.get_statistics(provider_id="postgresql")
```

---

## Triggers Reference

| Trigger | Threshold | Priority | Description |
|---------|-----------|----------|-------------|
| `VALIDATION_FAILURE` | N/A | 100 | Query failed syntax/semantic validation |
| `NEGATIVE_FEEDBACK` | N/A | 50 | User clicked thumbs-down |
| `LOW_CONFIDENCE` | < 0.7 | 20-70 | System confidence below threshold |
| `MULTIPLE_CLARIFICATIONS` | ≥ 3 | 10 | Required multiple user clarifications |

---

## Decision Types

| Decision | Effect | RAG Status | Use Case |
|----------|--------|------------|----------|
| `APPROVE` | Mark as approved | Good example | Query is correct as-is |
| `REJECT` | Mark as rejected | Bad example | Query is wrong, avoid this pattern |
| `CORRECT` | Approve with correction | Good example (corrected) | Query has minor issues, use corrected version |

---

## Best Practices

### For Experts:
1. **Prioritize by urgency**: Start with validation failures (priority 100)
2. **Provide feedback**: Always add notes explaining decisions
3. **Correct when possible**: Don't reject fixable queries
4. **Check metadata**: Review confidence scores and validation results
5. **Monitor stats**: Track review queue size and age

### For Developers:
1. **Auto-queue appropriately**: Use correct triggers
2. **Provide context**: Include schema context and reasoning traces
3. **Track metrics**: Monitor review completion times
4. **Handle async**: Review queue processing can be async
5. **Cache results**: Approved examples are immediately available

---

## Error Handling

### Common Errors:

**404 Not Found**
```json
{
  "error": "not_found",
  "message": "Review item {id} not found",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**400 Bad Request**
```json
{
  "error": "validation_error",
  "message": "corrected_query is required when decision is CORRECT",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**500 Internal Server Error**
```json
{
  "error": "update_error",
  "message": "Failed to update review item",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Monitoring & Observability

### Metrics Tracked:
- `review_queue_size{reason}` - Queue size by trigger reason
- `review_completion_time{approved}` - Time from queue to review
- `review_decisions_total{decision}` - Total decisions by type
- `rag_examples_total{status}` - Total examples by status

### Health Checks:
- Queue size < 100 (warning if higher)
- Oldest pending < 24 hours (warning if older)
- Approval rate > 60% (investigate if lower)

---

## Related Documentation
- [Design.md Section 15.4](../design.md#154-scenario-4-expert-review-queue) - Architecture details
- [SCENARIO_4_IMPLEMENTATION.md](../SCENARIO_4_IMPLEMENTATION.md) - Implementation notes
- [Test Suite](../tests/test_review_flow.py) - 25 comprehensive tests
