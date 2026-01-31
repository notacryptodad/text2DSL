"""Prometheus metrics endpoint."""
import logging

from fastapi import APIRouter, Response

from text2x.utils.observability import get_metrics, get_metrics_content_type

logger = logging.getLogger(__name__)

router = APIRouter(tags=["metrics"])


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Expose Prometheus metrics for monitoring and alerting",
)
async def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint.

    Exposes all application metrics in Prometheus text format for scraping.

    Metrics categories:
    - Accuracy: query success/failure rates, validation pass rates, user satisfaction
    - Performance: query latency, iterations per query, agent latencies
    - Cost: token usage, USD costs by provider and agent
    - RAG: retrieval counts, example usage rates
    - Review: queue sizes, completion times
    - HTTP: request counts, durations by endpoint

    Returns:
        Prometheus metrics in text format
    """
    metrics_data = get_metrics()
    return Response(
        content=metrics_data,
        media_type=get_metrics_content_type(),
    )
