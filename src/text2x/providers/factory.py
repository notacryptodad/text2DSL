"""Provider factory for creating provider instances from database models."""
from typing import TYPE_CHECKING

from text2x.providers.sql_provider import SQLProvider, SQLConnectionConfig
from text2x.models.workspace import ProviderType

if TYPE_CHECKING:
    from text2x.providers.base import QueryProvider


async def get_provider_instance(provider_model) -> "QueryProvider":
    """Create a QueryProvider instance from a provider database model.
    
    Args:
        provider_model: Provider model from database with associated connection
        
    Returns:
        QueryProvider instance ready for queries
        
    Raises:
        ValueError: If provider type is not supported
    """
    provider_type = provider_model.type
    
    # Get connection details from the provider's connections (one-to-many)
    connections = provider_model.connections
    if not connections:
        raise ValueError(f"Provider {provider_model.id} has no associated connections")
    
    # Use the first connection
    connection = connections[0]
    
    credentials = connection.credentials or {}
    username = credentials.get("username", "")
    password = credentials.get("password", "")
    
    if provider_type == ProviderType.POSTGRESQL:
        dialect = "postgresql"
    elif provider_type == ProviderType.MYSQL:
        dialect = "mysql"
    elif provider_type == ProviderType.SQLITE:
        dialect = "sqlite"
    else:
        raise ValueError(f"Unsupported provider type: {provider_type}")
    
    config = SQLConnectionConfig(
        host=connection.host or "localhost",
        port=connection.port or 5432,
        database=connection.database,
        username=username,
        password=password,
        dialect=dialect,
        extra_params=connection.connection_options or {}
    )
    
    return SQLProvider(config)
