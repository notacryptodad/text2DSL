# Text2DSL Observability Guide

This document provides comprehensive information about the observability features implemented in the Text2DSL API, including metrics, logging, tracing, and health checks.

## Table of Contents

- [Overview](#overview)
- [Prometheus Metrics](#prometheus-metrics)
- [Structured Logging](#structured-logging)
- [Request Tracing](#request-tracing)
- [Health Check Endpoints](#health-check-endpoints)
- [Configuration](#configuration)
- [Integration Examples](#integration-examples)

## Overview

The Text2DSL API includes production-ready observability features:

- **Prometheus Metrics**: Comprehensive metrics for accuracy, performance, cost, RAG, and review operations
- **Structured JSON Logging**: Machine-readable logs with correlation IDs and context enrichment
- **Request Tracing**: Automatic correlation ID generation and propagation for distributed tracing
- **Enhanced Health Checks**: Multiple health endpoints for Kubernetes probes and monitoring

## Prometheus Metrics

### Metrics Endpoint

Access Prometheus metrics at:
```
GET /metrics
```

The endpoint returns metrics in Prometheus text format, suitable for scraping.

### Metric Categories

#### 1. Accuracy Metrics

Track the quality and correctness of query generation:

- **`text2dsl_query_success_total`** (Counter)
  - Total number of successful query generations
  - Labels: `provider_type`

- **`text2dsl_query_failure_total`** (Counter)
  - Total number of failed query generations
  - Labels: `provider_type`, `error_type`

- **`text2dsl_validation_pass_total`** (Counter)
  - Total number of queries that passed validation
  - Labels: `provider_type`

- **`text2dsl_validation_fail_total`** (Counter)
  - Total number of queries that failed validation
  - Labels: `provider_type`

- **`text2dsl_user_satisfaction_total`** (Counter)
  - Total user satisfaction ratings
  - Labels: `rating` (1-5), `is_correct` (true/false)

#### 2. Performance Metrics

Track latency and processing time:

- **`text2dsl_query_latency_seconds`** (Histogram)
  - Query processing latency distribution
  - Labels: `provider_type`
  - Buckets: 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0 seconds

- **`text2dsl_iterations_per_query`** (Histogram)
  - Number of refinement iterations per query
  - Labels: `provider_type`
  - Buckets: 1-10

- **`text2dsl_agent_latency_seconds`** (Histogram)
  - Agent processing latency by agent type
  - Labels: `agent_type` (schema, rag, query_builder, validator)
  - Buckets: 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0 seconds

#### 3. Cost Metrics

Track token usage and costs:

- **`text2dsl_tokens_used_total`** (Counter)
  - Total number of tokens used
  - Labels: `token_type` (input, output), `provider_type`

- **`text2dsl_cost_usd_total`** (Counter)
  - Total cost in USD
  - Labels: `provider_type`

- **`text2dsl_tokens_by_agent_total`** (Counter)
  - Total tokens used by agent type
  - Labels: `agent_type`, `token_type`

#### 4. RAG Metrics

Track RAG system performance:

- **`text2dsl_rag_retrieval_total`** (Counter)
  - Total number of RAG retrievals
  - Labels: `provider_type`

- **`text2dsl_rag_example_usage_rate`** (Gauge)
  - Rate of RAG example usage in queries
  - Labels: `provider_type`

- **`text2dsl_rag_examples_total`** (Gauge)
  - Total number of RAG examples stored
  - Labels: `provider_type`, `status`

#### 5. Review Metrics

Track expert review queue:

- **`text2dsl_review_queue_size`** (Gauge)
  - Number of items in review queue
  - Labels: `reason` (low_confidence, validation_failed, user_reported)

- **`text2dsl_review_completion_time_seconds`** (Histogram)
  - Time to complete expert review
  - Labels: `approved` (true/false)
  - Buckets: 60, 300, 900, 1800, 3600, 7200, 14400, 28800 seconds

#### 6. HTTP Request Metrics

Track API usage:

- **`text2dsl_http_requests_total`** (Counter)
  - Total HTTP requests
  - Labels: `method`, `endpoint`, `status_code`

- **`text2dsl_http_request_duration_seconds`** (Histogram)
  - HTTP request duration distribution
  - Labels: `method`, `endpoint`
  - Buckets: 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0 seconds

### Example Prometheus Queries

```promql
# Average query latency by provider
rate(text2dsl_query_latency_seconds_sum[5m]) / rate(text2dsl_query_latency_seconds_count[5m])

# Query success rate
rate(text2dsl_query_success_total[5m]) / (rate(text2dsl_query_success_total[5m]) + rate(text2dsl_query_failure_total[5m]))

# P95 query latency
histogram_quantile(0.95, rate(text2dsl_query_latency_seconds_bucket[5m]))

# Total cost per hour
rate(text2dsl_cost_usd_total[1h]) * 3600

# Review queue backlog
text2dsl_review_queue_size
```

## Structured Logging

### JSON Log Format

Enable JSON logging by setting:
```bash
LOG_FORMAT=json
```

Each log entry includes:
- `timestamp`: ISO 8601 timestamp
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `logger`: Logger name
- `message`: Log message
- `module`: Source module
- `function`: Source function
- `line`: Line number
- `correlation_id`: Request correlation ID
- Custom context fields (user_id, provider_id, conversation_id, turn_id)

### Example Log Entry

```json
{
  "timestamp": "2024-01-31T10:30:45.123456Z",
  "level": "INFO",
  "logger": "text2x.api.routes.query",
  "message": "Processing query for provider postgres-main",
  "module": "query",
  "function": "process_query",
  "line": 52,
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "provider_id": "postgres-main",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "turn_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```

### Log Enrichment

Use the `async_log_context` context manager to enrich logs:

```python
from text2x.utils.observability import async_log_context

async with async_log_context(
    user_id=user.id,
    provider_id=provider.id,
    conversation_id=str(conversation_id),
):
    # All logs within this context will include these fields
    logger.info("Processing request")
```

## Request Tracing

### Correlation IDs

Every request automatically receives a unique correlation ID that:
- Is generated if not provided in the request
- Is propagated through all logs
- Is returned in the response header `X-Correlation-ID`
- Can be provided by clients via the `X-Correlation-ID` header

### Using Correlation IDs

**Client sends correlation ID:**
```bash
curl -H "X-Correlation-ID: my-trace-id-123" \
  https://api.example.com/api/v1/query
```

**Server returns correlation ID:**
```
HTTP/1.1 200 OK
X-Correlation-ID: my-trace-id-123
```

### Tracing Across Services

1. Client initiates request with correlation ID
2. API Gateway forwards correlation ID
3. Text2DSL API:
   - Extracts or generates correlation ID
   - Adds to all logs
   - Returns in response header
4. Client uses correlation ID to trace request through logs

### Middleware

The `RequestTracingMiddleware` automatically:
- Generates/extracts correlation IDs
- Logs request start/end
- Records metrics
- Adds correlation ID to response headers
- Handles errors gracefully

## Health Check Endpoints

### Comprehensive Health Check

**Endpoint:** `GET /health`

Returns detailed status of all services:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "production",
  "timestamp": "2024-01-31T10:30:45.123456Z",
  "uptime_seconds": 86400.50,
  "uptime_human": "1 day, 0:00:00",
  "services": {
    "database": {
      "status": "healthy",
      "latency_ms": 2.45
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 0.87
    },
    "opensearch": {
      "status": "healthy",
      "latency_ms": 15.23
    }
  }
}
```

**Status Values:**
- `healthy`: All services operational
- `degraded`: Some services unavailable but core functionality works
- `unhealthy`: Critical services unavailable

### Kubernetes Readiness Probe

**Endpoint:** `GET /health/ready`

Checks if the application can serve traffic. Returns:
- `200 OK` if ready
- `503 Service Unavailable` if not ready

```json
{
  "ready": true,
  "message": "Application is ready to serve traffic",
  "services": {
    "database": {"status": "healthy", "latency_ms": 2.45},
    "redis": {"status": "healthy", "latency_ms": 0.87}
  }
}
```

**Kubernetes Configuration:**
```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

### Kubernetes Liveness Probe

**Endpoint:** `GET /health/live`

Simple check to verify the application is alive and responsive.

```json
{
  "alive": true,
  "message": "Application is alive and responsive",
  "timestamp": "2024-01-31T10:30:45.123456Z",
  "uptime_seconds": 86400.50,
  "version": "0.1.0"
}
```

**Kubernetes Configuration:**
```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### Kubernetes Startup Probe

**Endpoint:** `GET /health/startup`

Checks if the application has completed its startup sequence.

```json
{
  "started": true,
  "message": "Application startup complete",
  "timestamp": "2024-01-31T10:30:45.123456Z",
  "uptime_seconds": 86400.50
}
```

**Kubernetes Configuration:**
```yaml
startupProbe:
  httpGet:
    path: /health/startup
    port: 8000
  initialDelaySeconds: 0
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 30  # Allow up to 150s for startup
```

## Configuration

### Environment Variables

```bash
# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json                   # json or text

# Metrics
ENABLE_METRICS=true               # Enable Prometheus metrics
METRICS_PORT=9090                 # Metrics endpoint port (if separate)

# Tracing
ENABLE_TRACING=true               # Enable request tracing
CORRELATION_ID_HEADER=X-Correlation-ID  # Correlation ID header name
```

### Disabling Features

**Disable metrics collection:**
```bash
ENABLE_METRICS=false
```

**Use text logging instead of JSON:**
```bash
LOG_FORMAT=text
```

**Disable tracing middleware:**
```bash
ENABLE_TRACING=false
```

## Integration Examples

### Prometheus Configuration

**prometheus.yml:**
```yaml
scrape_configs:
  - job_name: 'text2dsl'
    scrape_interval: 15s
    static_configs:
      - targets: ['text2dsl-api:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Import the provided Grafana dashboard or create custom panels:

**Query Success Rate:**
```promql
sum(rate(text2dsl_query_success_total[5m])) /
sum(rate(text2dsl_query_success_total[5m]) + rate(text2dsl_query_failure_total[5m]))
```

**Average Query Latency:**
```promql
rate(text2dsl_query_latency_seconds_sum[5m]) /
rate(text2dsl_query_latency_seconds_count[5m])
```

**Cost per Hour:**
```promql
sum(rate(text2dsl_cost_usd_total[1h])) * 3600
```

### ELK Stack Integration

**Filebeat configuration:**
```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/text2dsl/*.log
    json.keys_under_root: true
    json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "text2dsl-logs-%{+yyyy.MM.dd}"
```

**Kibana index pattern:** `text2dsl-logs-*`

**Useful queries:**
- All logs for a correlation ID: `correlation_id:"a1b2c3d4-e5f6-7890-abcd-ef1234567890"`
- Errors in last hour: `level:ERROR AND @timestamp:[now-1h TO now]`
- Queries for a provider: `provider_id:"postgres-main" AND message:"Processing query"`

### Docker Compose Example

```yaml
version: '3.8'

services:
  text2dsl-api:
    image: text2dsl:latest
    environment:
      - LOG_FORMAT=json
      - LOG_LEVEL=INFO
      - ENABLE_METRICS=true
    ports:
      - "8000:8000"

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

## Best Practices

1. **Correlation IDs**: Always propagate correlation IDs across service boundaries
2. **Log Sampling**: In high-traffic scenarios, consider log sampling for DEBUG logs
3. **Metric Cardinality**: Avoid high-cardinality labels (e.g., user IDs, raw queries)
4. **Health Checks**: Use different timeouts for liveness, readiness, and startup probes
5. **Alerting**: Set up alerts for:
   - Query success rate < 95%
   - P95 latency > 5 seconds
   - Review queue size > 100
   - Service unhealthy for > 2 minutes
6. **Cost Monitoring**: Track `text2dsl_cost_usd_total` to monitor LLM API costs
7. **Log Retention**: Configure appropriate retention policies based on compliance needs

## Troubleshooting

### Metrics Not Appearing

1. Check if metrics are enabled: `ENABLE_METRICS=true`
2. Verify Prometheus is scraping: Check Prometheus targets page
3. Check firewall rules for metrics endpoint

### Missing Correlation IDs

1. Ensure middleware is added: Check `app.py` includes `RequestTracingMiddleware`
2. Verify `ENABLE_TRACING=true`
3. Check if client is sending `X-Correlation-ID` header

### Health Checks Failing

1. Check service connectivity (database, Redis, OpenSearch)
2. Verify connection strings in configuration
3. Check service logs for initialization errors
4. Increase startup probe `failureThreshold` for slow-starting apps

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Kubernetes Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [ELK Stack](https://www.elastic.co/what-is/elk-stack)
