"""Observability utilities for metrics, logging, and tracing."""
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Dict, Optional

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from pythonjsonlogger import jsonlogger

# ============================================================================
# Prometheus Metrics
# ============================================================================

# Global registry for metrics
REGISTRY = CollectorRegistry()

# Accuracy Metrics
query_success_counter = Counter(
    "text2dsl_query_success_total",
    "Total number of successful query generations",
    ["provider_type"],
    registry=REGISTRY,
)

query_failure_counter = Counter(
    "text2dsl_query_failure_total",
    "Total number of failed query generations",
    ["provider_type", "error_type"],
    registry=REGISTRY,
)

validation_pass_counter = Counter(
    "text2dsl_validation_pass_total",
    "Total number of queries that passed validation",
    ["provider_type"],
    registry=REGISTRY,
)

validation_fail_counter = Counter(
    "text2dsl_validation_fail_total",
    "Total number of queries that failed validation",
    ["provider_type"],
    registry=REGISTRY,
)

user_satisfaction_counter = Counter(
    "text2dsl_user_satisfaction_total",
    "Total user satisfaction ratings",
    ["rating", "is_correct"],
    registry=REGISTRY,
)

# Performance Metrics
query_latency_histogram = Histogram(
    "text2dsl_query_latency_seconds",
    "Query processing latency in seconds",
    ["provider_type"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    registry=REGISTRY,
)

iterations_histogram = Histogram(
    "text2dsl_iterations_per_query",
    "Number of refinement iterations per query",
    ["provider_type"],
    buckets=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
    registry=REGISTRY,
)

agent_latency_histogram = Histogram(
    "text2dsl_agent_latency_seconds",
    "Agent processing latency in seconds by agent type",
    ["agent_type"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
    registry=REGISTRY,
)

# Cost Metrics
tokens_used_counter = Counter(
    "text2dsl_tokens_used_total",
    "Total number of tokens used",
    ["token_type", "provider_type"],  # token_type: input, output
    registry=REGISTRY,
)

cost_usd_counter = Counter(
    "text2dsl_cost_usd_total",
    "Total cost in USD",
    ["provider_type"],
    registry=REGISTRY,
)

tokens_by_agent_counter = Counter(
    "text2dsl_tokens_by_agent_total",
    "Total tokens used by agent type",
    ["agent_type", "token_type"],
    registry=REGISTRY,
)

# RAG Metrics
rag_retrieval_counter = Counter(
    "text2dsl_rag_retrieval_total",
    "Total number of RAG retrievals",
    ["provider_type"],
    registry=REGISTRY,
)

rag_example_usage_gauge = Gauge(
    "text2dsl_rag_example_usage_rate",
    "Rate of RAG example usage in queries",
    ["provider_type"],
    registry=REGISTRY,
)

rag_examples_total_gauge = Gauge(
    "text2dsl_rag_examples_total",
    "Total number of RAG examples stored",
    ["provider_type", "status"],
    registry=REGISTRY,
)

# Review Queue Metrics
review_queue_size_gauge = Gauge(
    "text2dsl_review_queue_size",
    "Number of items in review queue",
    ["reason"],
    registry=REGISTRY,
)

review_completion_time_histogram = Histogram(
    "text2dsl_review_completion_time_seconds",
    "Time to complete expert review in seconds",
    ["approved"],
    buckets=(60, 300, 900, 1800, 3600, 7200, 14400, 28800),
    registry=REGISTRY,
)

# API Request Metrics
http_requests_total = Counter(
    "text2dsl_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

http_request_duration_histogram = Histogram(
    "text2dsl_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)


# ============================================================================
# Metrics Helper Functions
# ============================================================================


def record_query_success(provider_type: str) -> None:
    """Record a successful query generation."""
    query_success_counter.labels(provider_type=provider_type).inc()


def record_query_failure(provider_type: str, error_type: str) -> None:
    """Record a failed query generation."""
    query_failure_counter.labels(provider_type=provider_type, error_type=error_type).inc()


def record_validation_result(provider_type: str, passed: bool) -> None:
    """Record query validation result."""
    if passed:
        validation_pass_counter.labels(provider_type=provider_type).inc()
    else:
        validation_fail_counter.labels(provider_type=provider_type).inc()


def record_user_satisfaction(rating: int, is_correct: bool) -> None:
    """Record user satisfaction feedback."""
    user_satisfaction_counter.labels(
        rating=str(rating), is_correct=str(is_correct)
    ).inc()


def record_query_latency(provider_type: str, latency_seconds: float) -> None:
    """Record query processing latency."""
    query_latency_histogram.labels(provider_type=provider_type).observe(latency_seconds)


def record_iterations(provider_type: str, iterations: int) -> None:
    """Record number of refinement iterations."""
    iterations_histogram.labels(provider_type=provider_type).observe(iterations)


def record_agent_latency(agent_type: str, latency_seconds: float) -> None:
    """Record agent processing latency."""
    agent_latency_histogram.labels(agent_type=agent_type).observe(latency_seconds)


def record_tokens_used(
    token_type: str, count: int, provider_type: str = "unknown"
) -> None:
    """Record tokens used."""
    tokens_used_counter.labels(token_type=token_type, provider_type=provider_type).inc(
        count
    )


def record_cost(provider_type: str, cost_usd: float) -> None:
    """Record cost in USD."""
    cost_usd_counter.labels(provider_type=provider_type).inc(cost_usd)


def record_tokens_by_agent(agent_type: str, token_type: str, count: int) -> None:
    """Record tokens used by specific agent."""
    tokens_by_agent_counter.labels(agent_type=agent_type, token_type=token_type).inc(
        count
    )


def record_rag_retrieval(provider_type: str) -> None:
    """Record RAG retrieval event."""
    rag_retrieval_counter.labels(provider_type=provider_type).inc()


def set_rag_example_usage_rate(provider_type: str, rate: float) -> None:
    """Set RAG example usage rate."""
    rag_example_usage_gauge.labels(provider_type=provider_type).set(rate)


def set_rag_examples_total(provider_type: str, status: str, count: int) -> None:
    """Set total number of RAG examples."""
    rag_examples_total_gauge.labels(provider_type=provider_type, status=status).set(count)


def set_review_queue_size(reason: str, size: int) -> None:
    """Set review queue size."""
    review_queue_size_gauge.labels(reason=reason).set(size)


def record_review_completion_time(approved: bool, duration_seconds: float) -> None:
    """Record review completion time."""
    review_completion_time_histogram.labels(approved=str(approved)).observe(
        duration_seconds
    )


def record_http_request(method: str, endpoint: str, status_code: int) -> None:
    """Record HTTP request."""
    http_requests_total.labels(
        method=method, endpoint=endpoint, status_code=str(status_code)
    ).inc()


def record_http_duration(method: str, endpoint: str, duration_seconds: float) -> None:
    """Record HTTP request duration."""
    http_request_duration_histogram.labels(method=method, endpoint=endpoint).observe(
        duration_seconds
    )


def get_metrics() -> bytes:
    """Get Prometheus metrics in text format."""
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """Get the content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST


# ============================================================================
# Structured Logging
# ============================================================================


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = get_correlation_id()
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with standard fields."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Add correlation ID if present
        if hasattr(record, "correlation_id"):
            log_record["correlation_id"] = record.correlation_id

        # Add custom context fields if present
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id
        if hasattr(record, "provider_id"):
            log_record["provider_id"] = record.provider_id
        if hasattr(record, "conversation_id"):
            log_record["conversation_id"] = record.conversation_id
        if hasattr(record, "turn_id"):
            log_record["turn_id"] = record.turn_id


def setup_json_logging(log_level: str = "INFO") -> None:
    """Setup JSON logging configuration."""
    formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S.%fZ",
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))


# ============================================================================
# Correlation ID Management
# ============================================================================

# Thread-local storage for correlation ID
import contextvars

_correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context."""
    _correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID from current context."""
    return _correlation_id_var.get()


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


@contextmanager
def correlation_context(correlation_id: Optional[str] = None):
    """Context manager for correlation ID."""
    if correlation_id is None:
        correlation_id = generate_correlation_id()

    token = _correlation_id_var.set(correlation_id)
    try:
        yield correlation_id
    finally:
        _correlation_id_var.reset(token)


# ============================================================================
# Log Enrichment
# ============================================================================


class LogContext:
    """Context manager for enriching logs with additional fields."""

    def __init__(self, **kwargs: Any):
        self.context = kwargs
        self.old_factory = None

    def __enter__(self):
        old_factory = logging.getLogRecordFactory()
        self.old_factory = old_factory

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


@asynccontextmanager
async def async_log_context(**kwargs: Any) -> AsyncGenerator[None, None]:
    """Async context manager for enriching logs."""
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **record_kwargs):
        record = old_factory(*args, **record_kwargs)
        for key, value in kwargs.items():
            setattr(record, key, value)
        return record

    logging.setLogRecordFactory(record_factory)
    try:
        yield
    finally:
        logging.setLogRecordFactory(old_factory)


# ============================================================================
# Helper Functions
# ============================================================================


def sanitize_endpoint(path: str) -> str:
    """
    Sanitize endpoint path for metrics.

    Replaces dynamic path parameters with placeholders to avoid
    high cardinality in metrics.
    """
    import re

    # Replace UUIDs with placeholder
    path = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "{id}",
        path,
        flags=re.IGNORECASE,
    )

    # Replace numeric IDs
    path = re.sub(r"/\d+(/|$)", r"/{id}\1", path)

    return path


def get_structured_logger(name: str, **default_context: Any) -> logging.Logger:
    """
    Get a logger with default context.

    Args:
        name: Logger name
        **default_context: Default context fields to include in all logs

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    if default_context:
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            for key, value in default_context.items():
                if not hasattr(record, key):
                    setattr(record, key, value)
            return record

        # Note: This modifies the global factory, which may not be ideal
        # In production, consider using a custom logger class
        logging.setLogRecordFactory(record_factory)

    return logger
