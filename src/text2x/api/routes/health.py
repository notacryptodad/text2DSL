"""Enhanced health check endpoints for Kubernetes probes and monitoring."""
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Response, status

from text2x.api.state import app_state
from text2x.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

# Track application start time for uptime calculation
_app_start_time = time.time()


def get_uptime_seconds() -> float:
    """Get application uptime in seconds."""
    return time.time() - _app_start_time


async def check_database_health() -> Dict[str, Any]:
    """Check database connectivity and health."""
    try:
        if not app_state.db_engine:
            return {
                "status": "not_initialized",
                "message": "Database engine not initialized",
            }

        # Execute a simple query with timeout
        async with app_state.db_engine.connect() as conn:
            start_time = time.time()
            result = await conn.execute("SELECT 1")
            latency_ms = (time.time() - start_time) * 1000

            return {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
            }

    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__,
        }


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis connectivity and health."""
    try:
        if not app_state.redis_client:
            return {
                "status": "not_initialized",
                "message": "Redis client not initialized",
            }

        # Ping Redis with timeout
        start_time = time.time()
        await app_state.redis_client.ping()
        latency_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
        }

    except Exception as e:
        logger.error(f"Redis health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__,
        }


async def check_opensearch_health() -> Dict[str, Any]:
    """Check OpenSearch connectivity and health."""
    try:
        if not app_state.opensearch_client:
            return {
                "status": "not_initialized",
                "message": "OpenSearch client not initialized",
            }

        # Ping OpenSearch
        start_time = time.time()
        is_alive = await app_state.opensearch_client.ping()
        latency_ms = (time.time() - start_time) * 1000

        if not is_alive:
            return {
                "status": "unhealthy",
                "error": "OpenSearch ping returned False",
            }

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
        }

    except Exception as e:
        logger.error(f"OpenSearch health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__,
        }


@router.get(
    "",
    summary="Health check",
    description="Comprehensive health check including all dependencies",
)
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.

    Returns detailed status of all services and dependencies.
    Use this for monitoring and alerting.

    Returns:
        status: Overall health status (healthy, degraded, unhealthy)
        version: Application version
        environment: Deployment environment
        uptime_seconds: Application uptime
        services: Status of each service dependency
    """
    services = {}

    # Check database
    services["database"] = await check_database_health()

    # Check Redis
    services["redis"] = await check_redis_health()

    # Check OpenSearch
    services["opensearch"] = await check_opensearch_health()

    # Determine overall status
    overall_status = "healthy"
    unhealthy_count = 0
    degraded_count = 0

    for service_name, service_info in services.items():
        service_status = service_info.get("status", "unknown")
        if service_status == "unhealthy":
            unhealthy_count += 1
        elif service_status in ["not_initialized", "degraded"]:
            degraded_count += 1

    # Set overall status based on service health
    if unhealthy_count > 0:
        overall_status = "unhealthy"
    elif degraded_count > 0:
        overall_status = "degraded"

    uptime_seconds = get_uptime_seconds()

    return {
        "status": overall_status,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": round(uptime_seconds, 2),
        "uptime_human": str(timedelta(seconds=int(uptime_seconds))),
        "services": services,
    }


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Kubernetes readiness probe - checks if app can serve traffic",
    status_code=status.HTTP_200_OK,
)
async def readiness_check(response: Response) -> Dict[str, Any]:
    """
    Readiness probe for Kubernetes.

    Checks if the application is ready to serve traffic by verifying
    that all critical dependencies are healthy.

    Returns:
        200 OK if ready to serve traffic
        503 Service Unavailable if not ready
    """
    services = {}

    # Check critical services only
    services["database"] = await check_database_health()
    services["redis"] = await check_redis_health()

    # Determine if ready (all critical services must be healthy)
    is_ready = True
    for service_name, service_info in services.items():
        service_status = service_info.get("status", "unknown")
        if service_status in ["unhealthy", "not_initialized"]:
            is_ready = False
            logger.warning(
                f"Readiness check failed: {service_name} is {service_status}"
            )
            break

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "ready": False,
            "message": "Application is not ready to serve traffic",
            "services": services,
        }

    return {
        "ready": True,
        "message": "Application is ready to serve traffic",
        "services": services,
    }


@router.get(
    "/live",
    summary="Liveness probe",
    description="Kubernetes liveness probe - checks if app is alive",
    status_code=status.HTTP_200_OK,
)
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness probe for Kubernetes.

    A simple check to verify the application is running and responsive.
    This should not check external dependencies to avoid cascading failures.

    Returns:
        200 OK if application is alive
    """
    uptime_seconds = get_uptime_seconds()

    return {
        "alive": True,
        "message": "Application is alive and responsive",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": round(uptime_seconds, 2),
        "version": settings.app_version,
    }


@router.get(
    "/startup",
    summary="Startup probe",
    description="Kubernetes startup probe - checks if app has started successfully",
    status_code=status.HTTP_200_OK,
)
async def startup_check(response: Response) -> Dict[str, Any]:
    """
    Startup probe for Kubernetes.

    Checks if the application has completed its startup sequence.
    This is used to give slow-starting applications more time before
    liveness checks begin.

    Returns:
        200 OK if startup complete
        503 Service Unavailable if still starting
    """
    # Check if critical services are initialized
    db_initialized = app_state.db_engine is not None
    redis_initialized = app_state.redis_client is not None

    startup_complete = db_initialized and redis_initialized

    if not startup_complete:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "started": False,
            "message": "Application is still starting",
            "initialization": {
                "database": db_initialized,
                "redis": redis_initialized,
            },
        }

    return {
        "started": True,
        "message": "Application startup complete",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": round(get_uptime_seconds(), 2),
    }
