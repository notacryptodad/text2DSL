"""Configuration management for Text2DSL system."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Text2DSL API"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, validation_alias="DEBUG")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")

    # API
    api_host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(default=8000, validation_alias="API_PORT")
    api_prefix: str = Field(default="/api/v1", validation_alias="API_PREFIX")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"],
        validation_alias="CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(default=True, validation_alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: list[str] = Field(default=["*"], validation_alias="CORS_ALLOW_METHODS")
    cors_allow_headers: list[str] = Field(default=["*"], validation_alias="CORS_ALLOW_HEADERS")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/text2dsl",
        validation_alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=10, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, validation_alias="DATABASE_MAX_OVERFLOW")
    database_echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )
    redis_schema_cache_ttl: int = Field(
        default=3600, validation_alias="REDIS_SCHEMA_CACHE_TTL"
    )  # 1 hour

    # OpenSearch / Vector Store
    opensearch_url: str = Field(
        default="http://localhost:9200",
        validation_alias="OPENSEARCH_URL",
    )
    opensearch_host: str = Field(
        default="localhost",
        validation_alias="OPENSEARCH_HOST",
    )
    opensearch_port: int = Field(
        default=443,
        validation_alias="OPENSEARCH_PORT",
    )
    opensearch_username: Optional[str] = Field(default=None, validation_alias="OPENSEARCH_USERNAME")
    opensearch_password: Optional[str] = Field(default=None, validation_alias="OPENSEARCH_PASSWORD")
    opensearch_index: str = Field(
        default="rag_examples",
        validation_alias="OPENSEARCH_INDEX",
    )
    opensearch_index_examples: str = Field(
        default="text2dsl_examples",
        validation_alias="OPENSEARCH_INDEX_EXAMPLES",
    )
    opensearch_use_ssl: bool = Field(
        default=True,
        validation_alias="OPENSEARCH_USE_SSL",
    )
    opensearch_verify_certs: bool = Field(
        default=False,
        validation_alias="OPENSEARCH_VERIFY_CERTS",
    )

    # LLM Configuration
    llm_provider: str = Field(default="bedrock", validation_alias="LLM_PROVIDER")
    llm_model: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        validation_alias="LLM_MODEL",
    )
    llm_api_base: Optional[str] = Field(default=None, validation_alias="LLM_API_BASE")
    llm_api_key: Optional[str] = Field(default=None, validation_alias="LLM_API_KEY")
    llm_temperature: float = Field(default=0.0, validation_alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=4096, validation_alias="LLM_MAX_TOKENS")
    llm_timeout: int = Field(default=120, validation_alias="LLM_TIMEOUT")  # seconds

    # AWS Configuration (for Bedrock)
    aws_region: str = Field(default="us-east-1", validation_alias="AWS_REGION")
    aws_access_key_id: Optional[str] = Field(default=None, validation_alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(
        default=None, validation_alias="AWS_SECRET_ACCESS_KEY"
    )

    # Bedrock Embedding Configuration
    bedrock_region: str = Field(default="us-east-1", validation_alias="BEDROCK_REGION")
    bedrock_embedding_model: str = Field(
        default="amazon.titan-embed-text-v2:0", validation_alias="BEDROCK_EMBEDDING_MODEL"
    )
    bedrock_embedding_batch_size: int = Field(
        default=25, validation_alias="BEDROCK_EMBEDDING_BATCH_SIZE"
    )

    # Agent Configuration
    max_iterations: int = Field(default=3, validation_alias="MAX_ITERATIONS")
    confidence_threshold: float = Field(default=0.8, validation_alias="CONFIDENCE_THRESHOLD")
    rag_top_k: int = Field(default=5, validation_alias="RAG_TOP_K")

    # Query Processing
    query_timeout: int = Field(default=300, validation_alias="QUERY_TIMEOUT")
    enable_execution: bool = Field(default=False, validation_alias="ENABLE_EXECUTION")

    # Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="json", validation_alias="LOG_FORMAT")  # json or text

    # Observability - Metrics
    enable_metrics: bool = Field(default=True, validation_alias="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, validation_alias="METRICS_PORT")

    # Observability - Tracing
    enable_tracing: bool = Field(default=True, validation_alias="ENABLE_TRACING")
    correlation_id_header: str = Field(
        default="X-Correlation-ID", validation_alias="CORRELATION_ID_HEADER"
    )

    # Expert Review
    review_queue_enabled: bool = Field(default=True, validation_alias="REVIEW_QUEUE_ENABLED")
    auto_queue_low_confidence: bool = Field(
        default=True, validation_alias="AUTO_QUEUE_LOW_CONFIDENCE"
    )
    low_confidence_threshold: float = Field(
        default=0.6, validation_alias="LOW_CONFIDENCE_THRESHOLD"
    )

    # Authentication
    enable_auth: bool = Field(default=True, validation_alias="ENABLE_AUTH")
    jwt_secret_key: str = Field(
        default="your-secret-key-change-this-in-production", validation_alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, validation_alias="JWT_EXPIRE_MINUTES")
    jwt_refresh_expire_days: int = Field(default=7, validation_alias="JWT_REFRESH_EXPIRE_DAYS")
    api_key_header: str = Field(default="X-API-Key", validation_alias="API_KEY_HEADER")
    allow_self_registration: bool = Field(default=False, validation_alias="ALLOW_SELF_REGISTRATION")

    # AgentCore Configuration
    agentcore_mode: str = Field(
        default="local",
        validation_alias="AGENTCORE_MODE",
        description="AgentCore mode: 'local' (in-process) or 'remote' (HTTP calls)"
    )
    agentcore_url: Optional[str] = Field(
        default=None,
        validation_alias="AGENTCORE_URL",
        description="Base URL for remote AgentCore service"
    )
    agentcore_api_key: Optional[str] = Field(
        default=None,
        validation_alias="AGENTCORE_API_KEY",
        description="API key for remote AgentCore authentication"
    )
    agentcore_timeout: int = Field(
        default=120,
        validation_alias="AGENTCORE_TIMEOUT",
        description="Timeout in seconds for AgentCore requests"
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience function for getting settings
settings = get_settings()
