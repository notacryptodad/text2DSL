"""FastAPI middleware for observability and request tracking."""
import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from text2x.utils.observability import (
    correlation_context,
    generate_correlation_id,
    record_http_duration,
    record_http_request,
    sanitize_endpoint,
    set_correlation_id,
)

logger = logging.getLogger(__name__)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request tracing and observability.

    Features:
    - Generates correlation IDs for each request
    - Logs request start/end with latency
    - Tracks request metadata (method, path, status_code, user_agent)
    - Adds correlation ID to response headers
    - Records Prometheus metrics for HTTP requests
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add observability."""
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = generate_correlation_id()

        # Set correlation ID in context
        with correlation_context(correlation_id):
            set_correlation_id(correlation_id)

            # Track request start time
            start_time = time.time()

            # Extract request metadata
            method = request.method
            path = request.url.path
            user_agent = request.headers.get("User-Agent", "unknown")
            client_host = request.client.host if request.client else "unknown"

            # Log request start
            logger.info(
                "Request started",
                extra={
                    "correlation_id": correlation_id,
                    "method": method,
                    "path": path,
                    "user_agent": user_agent,
                    "client_host": client_host,
                },
            )

            try:
                # Process request
                response = await call_next(request)

                # Calculate duration
                duration = time.time() - start_time

                # Sanitize endpoint for metrics (replace IDs with placeholders)
                sanitized_endpoint = sanitize_endpoint(path)

                # Record metrics
                record_http_request(method, sanitized_endpoint, response.status_code)
                record_http_duration(method, sanitized_endpoint, duration)

                # Log request completion
                logger.info(
                    "Request completed",
                    extra={
                        "correlation_id": correlation_id,
                        "method": method,
                        "path": path,
                        "status_code": response.status_code,
                        "duration_ms": round(duration * 1000, 2),
                    },
                )

                # Add correlation ID to response headers
                response.headers["X-Correlation-ID"] = correlation_id

                return response

            except Exception as exc:
                # Calculate duration even for errors
                duration = time.time() - start_time

                # Sanitize endpoint for metrics
                sanitized_endpoint = sanitize_endpoint(path)

                # Record error metrics (status 500)
                record_http_request(method, sanitized_endpoint, 500)
                record_http_duration(method, sanitized_endpoint, duration)

                # Log error
                logger.error(
                    "Request failed",
                    extra={
                        "correlation_id": correlation_id,
                        "method": method,
                        "path": path,
                        "duration_ms": round(duration * 1000, 2),
                        "error": str(exc),
                    },
                    exc_info=True,
                )

                # Re-raise the exception to be handled by FastAPI exception handlers
                raise


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detailed request/response logging.

    This is a lighter alternative if you don't need full tracing.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        start_time = time.time()

        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", generate_correlation_id())
        set_correlation_id(correlation_id)

        logger.debug(
            f"Incoming request: {request.method} {request.url.path}",
            extra={"correlation_id": correlation_id},
        )

        response = await call_next(request)
        duration = time.time() - start_time

        logger.debug(
            f"Response: {response.status_code} ({duration*1000:.2f}ms)",
            extra={"correlation_id": correlation_id},
        )

        response.headers["X-Correlation-ID"] = correlation_id
        return response
