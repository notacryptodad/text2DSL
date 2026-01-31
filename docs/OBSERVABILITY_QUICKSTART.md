# Observability Quick Start Guide

A quick reference for using the observability features in Text2DSL API.

## Table of Contents
- [Configuration](#configuration)
- [Recording Metrics](#recording-metrics)
- [Structured Logging](#structured-logging)
- [Correlation IDs](#correlation-ids)
- [Health Checks](#health-checks)
- [Common Patterns](#common-patterns)

## Configuration

### Environment Variables

```bash
# Logging
LOG_FORMAT=json              # Use json or text
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Metrics
ENABLE_METRICS=true         # Enable/disable metrics collection

# Tracing
ENABLE_TRACING=true         # Enable/disable request tracing
```

## Recording Metrics

### Import Functions

```python
from text2x.utils.observability import (
    record_query_success,
    record_query_failure,
    record_validation_result,
    record_user_satisfaction,
    record_query_latency,
    record_iterations,
    record_agent_latency,
    record_tokens_used,
    record_cost,
    record_rag_retrieval,
    set_review_queue_size,
    record_review_completion_time,
)
```

### Usage Examples

```python
# Record query success/failure
record_query_success("postgresql")
record_query_failure("postgresql", "timeout")

# Record validation
record_validation_result("postgresql", passed=True)

# Record performance
record_query_latency("postgresql", 2.5)  # seconds
record_iterations("postgresql", 3)
record_agent_latency("query_builder", 0.8)  # seconds

# Record costs
record_tokens_used("input", 1500, "postgresql")
record_tokens_used("output", 300, "postgresql")
record_cost("postgresql", 0.012)  # USD

# Record RAG usage
record_rag_retrieval("postgresql")

# Record user feedback
record_user_satisfaction(rating=5, is_correct=True)

# Record review metrics
set_review_queue_size("low_confidence", 25)
record_review_completion_time(approved=True, duration_seconds=300)
```

## Structured Logging

### Basic Logging

```python
import logging
logger = logging.getLogger(__name__)

# Logs automatically include correlation_id and standard fields
logger.info("Processing started")
logger.warning("Low confidence detected", extra={"confidence": 0.65})
logger.error("Validation failed", exc_info=True)
```

### Log Context Enrichment

```python
from text2x.utils.observability import async_log_context

async with async_log_context(
    user_id="user-123",
    provider_id="postgres-main",
    conversation_id=str(conv_id),
    turn_id=str(turn_id),
):
    # All logs in this block include these fields
    logger.info("Processing query")
    await process_query()
    logger.info("Query completed")
```

### Log Output Format

JSON format (when `LOG_FORMAT=json`):
```json
{
  "timestamp": "2024-01-31T10:30:45.123456Z",
  "level": "INFO",
  "logger": "text2x.api.routes.query",
  "message": "Processing query",
  "module": "query",
  "function": "process_query",
  "line": 52,
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "user-123",
  "provider_id": "postgres-main"
}
```

## Correlation IDs

### Automatic (via Middleware)

Correlation IDs are automatically:
- Generated if not provided
- Extracted from `X-Correlation-ID` header
- Added to all logs
- Returned in response headers

### Manual Usage

```python
from text2x.utils.observability import (
    correlation_context,
    get_correlation_id,
    set_correlation_id,
)

# Using context manager
with correlation_context("my-trace-id"):
    current_id = get_correlation_id()  # Returns "my-trace-id"
    logger.info("Processing")  # Logs include correlation_id

# Manual set/get
set_correlation_id("manual-id")
current_id = get_correlation_id()
```

### Client Usage

```bash
# Send request with correlation ID
curl -H "X-Correlation-ID: my-trace-123" \
  http://localhost:8000/api/v1/query

# Response includes correlation ID
HTTP/1.1 200 OK
X-Correlation-ID: my-trace-123
```

## Health Checks

### Endpoints

```bash
# Comprehensive health (all services)
GET /health

# Kubernetes readiness probe
GET /health/ready

# Kubernetes liveness probe
GET /health/live

# Kubernetes startup probe
GET /health/startup
```

### Response Format

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "production",
  "uptime_seconds": 3600.5,
  "services": {
    "database": {"status": "healthy", "latency_ms": 2.45},
    "redis": {"status": "healthy", "latency_ms": 0.87}
  }
}
```

## Common Patterns

### Pattern 1: Track Complete Query Processing

```python
import time
from text2x.utils.observability import (
    async_log_context,
    record_query_success,
    record_query_failure,
    record_query_latency,
    record_validation_result,
    record_tokens_used,
    record_cost,
)

async def process_query(request: QueryRequest):
    start_time = time.time()
    provider_type = extract_provider_type(request.provider_id)

    # Add context for logging
    async with async_log_context(
        provider_id=request.provider_id,
        conversation_id=str(conversation_id),
    ):
        try:
            logger.info("Starting query processing")

            # Process query
            result = await orchestrator.process(request)

            # Record success metrics
            duration = time.time() - start_time
            record_query_success(provider_type)
            record_query_latency(provider_type, duration)
            record_validation_result(provider_type, result.is_valid)

            # Record costs
            if result.trace:
                record_tokens_used("input", result.trace.tokens_in, provider_type)
                record_tokens_used("output", result.trace.tokens_out, provider_type)
                record_cost(provider_type, result.trace.cost)

            logger.info("Query processing completed")
            return result

        except Exception as e:
            logger.error(f"Query processing failed: {e}", exc_info=True)
            record_query_failure(provider_type, type(e).__name__)
            raise
```

### Pattern 2: Track Agent Execution

```python
import time
from text2x.utils.observability import (
    record_agent_latency,
    record_tokens_by_agent,
)

async def run_agent(agent_type: str, prompt: str):
    start_time = time.time()

    try:
        logger.info(f"Running {agent_type} agent")

        # Execute agent
        result = await llm_client.complete(prompt)

        # Record metrics
        duration = time.time() - start_time
        record_agent_latency(agent_type, duration)
        record_tokens_by_agent(agent_type, "input", result.tokens_in)
        record_tokens_by_agent(agent_type, "output", result.tokens_out)

        logger.info(f"{agent_type} agent completed in {duration:.2f}s")
        return result

    except Exception as e:
        logger.error(f"{agent_type} agent failed: {e}", exc_info=True)
        raise
```

### Pattern 3: Track Review Queue

```python
from text2x.utils.observability import (
    set_review_queue_size,
    record_review_completion_time,
)

async def update_review_queue_metrics():
    """Update review queue size metrics."""
    # Count by reason
    counts = await db.count_pending_reviews_by_reason()

    for reason, count in counts.items():
        set_review_queue_size(reason, count)

async def complete_review(item_id: UUID, approved: bool):
    """Complete a review and record metrics."""
    item = await db.get_review_item(item_id)

    # Calculate duration
    duration = (datetime.utcnow() - item.created_at).total_seconds()

    # Update item
    await db.update_review_status(item_id, approved)

    # Record metrics
    record_review_completion_time(approved, duration)

    # Update queue size
    await update_review_queue_metrics()
```

### Pattern 4: Add Custom Metrics

```python
from prometheus_client import Counter, Histogram
from text2x.utils.observability import REGISTRY

# Define custom metrics
custom_counter = Counter(
    'text2dsl_custom_events_total',
    'Total custom events',
    ['event_type'],
    registry=REGISTRY,
)

custom_histogram = Histogram(
    'text2dsl_custom_duration_seconds',
    'Custom operation duration',
    ['operation'],
    registry=REGISTRY,
)

# Use in code
def process_custom_event(event_type: str):
    custom_counter.labels(event_type=event_type).inc()

    with custom_histogram.labels(operation='processing').time():
        # Your code here
        do_something()
```

## Quick Commands

### View Metrics
```bash
curl http://localhost:8000/metrics
```

### Check Health
```bash
# Detailed health
curl http://localhost:8000/health | jq .

# Readiness
curl http://localhost:8000/health/ready

# Liveness
curl http://localhost:8000/health/live
```

### Parse JSON Logs
```bash
# Tail logs and format JSON
tail -f logs/app.log | jq .

# Filter by correlation ID
tail -f logs/app.log | jq 'select(.correlation_id == "abc-123")'

# Filter errors
tail -f logs/app.log | jq 'select(.level == "ERROR")'

# Show only message and level
tail -f logs/app.log | jq '{level, message}'
```

### Test Correlation ID
```bash
# Send request with correlation ID
curl -v -H "X-Correlation-ID: test-trace-123" \
  -H "Content-Type: application/json" \
  -d '{"provider_id":"postgres-main","query":"show users"}' \
  http://localhost:8000/api/v1/query

# Check response header for X-Correlation-ID
```

## Prometheus Query Examples

```promql
# Query success rate
rate(text2dsl_query_success_total[5m]) /
(rate(text2dsl_query_success_total[5m]) + rate(text2dsl_query_failure_total[5m]))

# Average query latency
rate(text2dsl_query_latency_seconds_sum[5m]) /
rate(text2dsl_query_latency_seconds_count[5m])

# P95 latency
histogram_quantile(0.95, rate(text2dsl_query_latency_seconds_bucket[5m]))

# Hourly cost
rate(text2dsl_cost_usd_total[1h]) * 3600

# Review queue size
sum(text2dsl_review_queue_size)

# HTTP error rate
rate(text2dsl_http_requests_total{status_code=~"5.."}[5m])
```

## Troubleshooting

### Metrics Not Showing
1. Check `ENABLE_METRICS=true`
2. Verify metrics endpoint: `curl localhost:8000/metrics`
3. Check Prometheus scrape config

### No Correlation IDs in Logs
1. Check `ENABLE_TRACING=true`
2. Verify middleware is registered in `app.py`
3. Check LOG_FORMAT is set correctly

### JSON Logs Not Working
1. Set `LOG_FORMAT=json`
2. Restart application
3. Check log output format

### Health Checks Failing
1. Check service connectivity (DB, Redis, OpenSearch)
2. Review logs for connection errors
3. Verify configuration settings

## Best Practices

1. **Always use log context** for request processing
2. **Record metrics at key points** (start, success, failure)
3. **Use correlation IDs** for distributed tracing
4. **Monitor costs** in production to avoid surprises
5. **Set up alerts** for critical metrics
6. **Use structured logging** for better searchability
7. **Sanitize sensitive data** before logging
8. **Keep metric labels low cardinality**

## Additional Resources

- Full documentation: `/docs/OBSERVABILITY.md`
- Prometheus config: `/docs/prometheus-example.yml`
- Alert rules: `/docs/text2dsl_alerts.yml`
- Implementation details: `/OBSERVABILITY_IMPLEMENTATION.md`
