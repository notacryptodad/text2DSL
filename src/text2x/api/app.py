"""FastAPI application setup and configuration."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from text2x.api.models import ErrorResponse, HealthCheckResponse
from text2x.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if settings.log_format == "text"
    else "%(message)s",
)
logger = logging.getLogger(__name__)


# Global state for database and other resources
class AppState:
    """Application state container."""

    def __init__(self) -> None:
        self.db_engine = None
        self.redis_client = None
        self.opensearch_client = None


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


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors."""
    logger.warning(f"Validation error for {request.url.path}: {exc.errors()}")

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
    logger.error(
        f"Unhandled exception for {request.url.path}: {exc}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="internal_error",
            message="An internal error occurred" if not settings.debug else str(exc),
        ).model_dump(),
    )


# Health check endpoint
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["health"],
    summary="Health check",
)
async def health_check() -> HealthCheckResponse:
    """Check the health status of the API and its dependencies."""
    services = {}

    # Check database
    try:
        if app_state.db_engine:
            async with app_state.db_engine.connect() as conn:
                await conn.execute("SELECT 1")
            services["database"] = {"status": "healthy"}
        else:
            services["database"] = {"status": "not_initialized"}
    except Exception as e:
        services["database"] = {"status": "unhealthy", "error": str(e)}

    # Check Redis
    try:
        if app_state.redis_client:
            await app_state.redis_client.ping()
            services["redis"] = {"status": "healthy"}
        else:
            services["redis"] = {"status": "not_initialized"}
    except Exception as e:
        services["redis"] = {"status": "unhealthy", "error": str(e)}

    # Check OpenSearch
    try:
        if app_state.opensearch_client:
            await app_state.opensearch_client.ping()
            services["opensearch"] = {"status": "healthy"}
        else:
            services["opensearch"] = {"status": "not_initialized"}
    except Exception as e:
        services["opensearch"] = {"status": "unhealthy", "error": str(e)}

    # Determine overall status
    overall_status = "healthy"
    for service in services.values():
        if service["status"] == "unhealthy":
            overall_status = "unhealthy"
            break
        elif service["status"] == "not_initialized":
            overall_status = "degraded"

    return HealthCheckResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        services=services,
    )


# Root endpoint
@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "unavailable",
    }


def get_app() -> FastAPI:
    """Get the FastAPI application instance."""
    return app
