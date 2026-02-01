"""FastAPI application setup and configuration."""
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from text2x.api.models import ErrorResponse, HealthCheckResponse
from text2x.config import settings
from text2x.utils.observability import setup_json_logging, get_correlation_id

# Configure logging based on settings
if settings.log_format == "json":
    setup_json_logging(settings.log_level)
else:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

logger = logging.getLogger(__name__)


# Global state for database and other resources
class AppState:
    """Application state container."""

    def __init__(self) -> None:
        self.db_engine = None
        self.redis_client = None
        self.opensearch_client = None
        self.start_time = time.time()


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting Text2DSL API...")

    try:
        # Initialize database
        await initialize_database()
        logger.info("Database initialized successfully")

        # Initialize Redis
        await initialize_redis()
        logger.info("Redis initialized successfully")

        # Initialize OpenSearch
        await initialize_opensearch()
        logger.info("OpenSearch initialized successfully")

        logger.info(
            f"Text2DSL API started successfully on {settings.api_host}:{settings.api_port}"
        )

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("Shutting down Text2DSL API...")

    try:
        # Close database connections
        if app_state.db_engine:
            await app_state.db_engine.dispose()
            logger.info("Database connections closed")

        # Close Redis connection
        if app_state.redis_client:
            await app_state.redis_client.close()
            logger.info("Redis connection closed")

        # Close OpenSearch connection
        if app_state.opensearch_client:
            await app_state.opensearch_client.close()
            logger.info("OpenSearch connection closed")

        logger.info("Text2DSL API shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


async def initialize_database() -> None:
    """Initialize database connection pool."""
    from sqlalchemy.ext.asyncio import create_async_engine

    try:
        app_state.db_engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            echo=settings.database_echo,
            pool_pre_ping=True,  # Verify connections before using
        )

        # Test connection
        async with app_state.db_engine.connect() as conn:
            await conn.execute("SELECT 1")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def initialize_redis() -> None:
    """Initialize Redis connection."""
    from redis.asyncio import from_url

    try:
        app_state.redis_client = await from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

        # Test connection
        await app_state.redis_client.ping()

    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise


async def initialize_opensearch() -> None:
    """Initialize OpenSearch connection."""
    from opensearchpy import AsyncOpenSearch

    try:
        auth = None
        if settings.opensearch_username and settings.opensearch_password:
            auth = (settings.opensearch_username, settings.opensearch_password)

        app_state.opensearch_client = AsyncOpenSearch(
            hosts=[settings.opensearch_url],
            http_auth=auth,
            use_ssl=settings.opensearch_url.startswith("https"),
            verify_certs=False if settings.environment == "development" else True,
        )

        # Test connection
        await app_state.opensearch_client.ping()

    except Exception as e:
        logger.error(f"Failed to initialize OpenSearch: {e}")
        raise


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent system for converting natural language to executable queries",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Add observability middleware
if settings.enable_metrics:
    from text2x.api.middleware import RequestTracingMiddleware

    app.add_middleware(RequestTracingMiddleware)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors."""
    correlation_id = get_correlation_id()
    logger.warning(
        f"Validation error for {request.url.path}: {exc.errors()}",
        extra={"correlation_id": correlation_id} if correlation_id else {},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="validation_error",
            message="Request validation failed",
            details={"errors": exc.errors()},
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    correlation_id = get_correlation_id()
    logger.error(
        f"Unhandled exception for {request.url.path}: {exc}",
        exc_info=True,
        extra={"correlation_id": correlation_id} if correlation_id else {},
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="internal_error",
            message="An internal error occurred" if not settings.debug else str(exc),
        ).model_dump(),
    )


# Note: Health check endpoints are now in health.py router


# Root endpoint
@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "unavailable",
    }


# Include API routers
from text2x.api.routes import conversations, providers, query, review, health, metrics, workspaces

app.include_router(query.router, prefix=settings.api_prefix)
app.include_router(workspaces.router, prefix=settings.api_prefix)  # Workspaces with nested providers/connections
app.include_router(providers.router, prefix=settings.api_prefix)  # Legacy flat provider endpoints
app.include_router(conversations.router, prefix=settings.api_prefix)
app.include_router(review.router, prefix=settings.api_prefix)
app.include_router(health.router)  # No prefix for health checks
app.include_router(metrics.router)  # No prefix for metrics


# WebSocket endpoint for streaming query processing
@app.websocket("/ws/query")
async def query_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for streaming query processing.

    This endpoint accepts WebSocket connections and streams query processing
    events in real-time, including:
    - Progress updates as agents work
    - Clarification requests if needed
    - Final query results
    - Error notifications

    The client should send a JSON message with the query request:
    {
        "provider_id": "postgres-main",
        "query": "Show me all users",
        "conversation_id": "optional-uuid",
        "options": {
            "trace_level": "none" | "summary" | "full",
            "max_iterations": 3,
            "confidence_threshold": 0.8,
            "enable_execution": false
        }
    }

    The server will respond with a stream of events:
    {
        "type": "progress" | "clarification" | "result" | "error",
        "data": {...},
        "trace": {...}  // if trace_level != "none"
    }
    """
    await websocket.accept()
    logger.info(f"WebSocket connection accepted from {websocket.client}")

    try:
        # Wait for query request from client
        async for message in websocket.iter_json():
            try:
                # Import here to avoid circular dependency
                from text2x.api.websocket import (
                    WebSocketQueryRequest,
                    handle_websocket_query,
                )

                # Parse and validate request
                request = WebSocketQueryRequest(**message)

                # Process query and stream events
                await handle_websocket_query(websocket, request)

            except ValidationError as e:
                logger.warning(f"Invalid WebSocket message: {e}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "data": {
                            "error": "validation_error",
                            "message": "Invalid request format",
                            "details": {"errors": e.errors()},
                        },
                    }
                )
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}", exc_info=True)
                await websocket.send_json(
                    {
                        "type": "error",
                        "data": {
                            "error": "processing_error",
                            "message": "Failed to process query",
                            "details": {"error": str(e)} if settings.debug else {},
                        },
                    }
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from {websocket.client}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        # Ensure connection is closed
        try:
            await websocket.close()
        except Exception:
            pass


def get_app() -> FastAPI:
    """Get the FastAPI application instance."""
    return app
