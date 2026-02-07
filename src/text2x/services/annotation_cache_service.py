"""Annotation Cache Service for caching schema annotations.

This service handles caching for schema annotations including:
- Table annotations (descriptions, business terms, relationships)
- Column annotations (descriptions, sensitive flags, search hints)
- Cache invalidation on save/update/delete
"""

import json
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

import redis.asyncio as redis
from redis.asyncio import Redis

from text2x.config import settings

logger = logging.getLogger(__name__)


class AnnotationCacheService:
    """
    Service for caching and retrieving schema annotations.

    This service:
    - Caches annotations in Redis with configurable TTL
    - Supports table-level and column-level annotations
    - Invalidates cache when annotations are modified
    - Falls back to database when cache misses
    """

    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        cache_ttl: Optional[int] = None,
    ):
        """
        Initialize annotation cache service.

        Args:
            redis_client: Redis client for caching (optional)
            cache_ttl: Cache TTL in seconds (optional, defaults to settings)
        """
        self._redis_client = redis_client
        self.cache_ttl = cache_ttl or settings.redis_annotation_cache_ttl

    async def _get_redis_client(self) -> Redis:
        """Get or create Redis client."""
        if self._redis_client is None:
            self._redis_client = await redis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis_client

    def _make_table_key(self, connection_id: UUID, table_name: str) -> str:
        """Generate cache key for table annotations."""
        return f"annotations:{connection_id}:table:{table_name}"

    def _make_column_key(self, connection_id: UUID, table_name: str, column_name: str) -> str:
        """Generate cache key for column annotations."""
        return f"annotations:{connection_id}:column:{table_name}:{column_name}"

    def _make_connection_key(self, connection_id: UUID) -> str:
        """Generate cache key for all annotations in a connection."""
        return f"annotations:{connection_id}:all"

    async def get_table_annotation(
        self,
        connection_id: UUID,
        table_name: str,
        fallback_fn: Optional[callable] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached table annotation.

        Args:
            connection_id: UUID of the connection
            table_name: Name of the table
            fallback_fn: Optional async function to call on cache miss

        Returns:
            Cached annotation dict or None if not found
        """
        cache_key = self._make_table_key(connection_id, table_name)
        try:
            redis_client = await self._get_redis_client()
            cached = await redis_client.get(cache_key)

            if cached:
                logger.debug(f"Annotation cache HIT for table {table_name}")
                return json.loads(cached)

            logger.debug(f"Annotation cache MISS for table {table_name}")

            if fallback_fn:
                result = await fallback_fn()
                if result:
                    await self.cache_table_annotation(connection_id, table_name, result)
                return result

            return None

        except Exception as e:
            logger.warning(f"Failed to get annotation from cache: {e}")
            if fallback_fn:
                return await fallback_fn()
            return None

    async def get_column_annotation(
        self,
        connection_id: UUID,
        table_name: str,
        column_name: str,
        fallback_fn: Optional[callable] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached column annotation.

        Args:
            connection_id: UUID of the connection
            table_name: Name of the table
            column_name: Name of the column
            fallback_fn: Optional async function to call on cache miss

        Returns:
            Cached annotation dict or None if not found
        """
        cache_key = self._make_column_key(connection_id, table_name, column_name)
        try:
            redis_client = await self._get_redis_client()
            cached = await redis_client.get(cache_key)

            if cached:
                logger.debug(f"Annotation cache HIT for column {table_name}.{column_name}")
                return json.loads(cached)

            logger.debug(f"Annotation cache MISS for column {table_name}.{column_name}")

            if fallback_fn:
                result = await fallback_fn()
                if result:
                    await self.cache_column_annotation(
                        connection_id, table_name, column_name, result
                    )
                return result

            return None

        except Exception as e:
            logger.warning(f"Failed to get column annotation from cache: {e}")
            if fallback_fn:
                return await fallback_fn()
            return None

    async def cache_table_annotation(
        self,
        connection_id: UUID,
        table_name: str,
        annotation: Dict[str, Any],
    ) -> str:
        """
        Cache table annotation.

        Args:
            connection_id: UUID of the connection
            table_name: Name of the table
            annotation: Annotation dict to cache

        Returns:
            Cache key used
        """
        cache_key = self._make_table_key(connection_id, table_name)
        try:
            redis_client = await self._get_redis_client()
            await redis_client.setex(cache_key, self.cache_ttl, json.dumps(annotation))
            logger.debug(f"Cached table annotation for {table_name}")
            return cache_key
        except Exception as e:
            logger.error(f"Failed to cache table annotation: {e}")
            raise

    async def cache_column_annotation(
        self,
        connection_id: UUID,
        table_name: str,
        column_name: str,
        annotation: Dict[str, Any],
    ) -> str:
        """
        Cache column annotation.

        Args:
            connection_id: UUID of the connection
            table_name: Name of the table
            column_name: Name of the column
            annotation: Annotation dict to cache

        Returns:
            Cache key used
        """
        cache_key = self._make_column_key(connection_id, table_name, column_name)
        try:
            redis_client = await self._get_redis_client()
            await redis_client.setex(cache_key, self.cache_ttl, json.dumps(annotation))
            logger.debug(f"Cached column annotation for {table_name}.{column_name}")
            return cache_key
        except Exception as e:
            logger.error(f"Failed to cache column annotation: {e}")
            raise

    async def invalidate_table_annotation(
        self,
        connection_id: UUID,
        table_name: str,
    ) -> bool:
        """
        Invalidate cached table annotation.

        Args:
            connection_id: UUID of the connection
            table_name: Name of the table

        Returns:
            True if cache was invalidated
        """
        cache_key = self._make_table_key(connection_id, table_name)
        try:
            redis_client = await self._get_redis_client()
            result = await redis_client.delete(cache_key)
            logger.info(f"Invalidated table annotation cache for {table_name}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to invalidate table annotation cache: {e}")
            return False

    async def invalidate_column_annotation(
        self,
        connection_id: UUID,
        table_name: str,
        column_name: str,
    ) -> bool:
        """
        Invalidate cached column annotation.

        Args:
            connection_id: UUID of the connection
            table_name: Name of the table
            column_name: Name of the column

        Returns:
            True if cache was invalidated
        """
        cache_key = self._make_column_key(connection_id, table_name, column_name)
        try:
            redis_client = await self._get_redis_client()
            result = await redis_client.delete(cache_key)
            logger.info(f"Invalidated column annotation cache for {table_name}.{column_name}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to invalidate column annotation cache: {e}")
            return False

    async def invalidate_all_for_connection(self, connection_id: UUID) -> int:
        """
        Invalidate all cached annotations for a connection.

        Args:
            connection_id: UUID of the connection

        Returns:
            Number of keys invalidated
        """
        pattern = f"annotations:{connection_id}:*"
        try:
            redis_client = await self._get_redis_client()
            keys = await redis_client.keys(pattern)
            if keys:
                result = await redis_client.delete(*keys)
                logger.info(
                    f"Invalidated {result} annotation cache keys for connection {connection_id}"
                )
                return result
            return 0
        except Exception as e:
            logger.error(f"Failed to invalidate annotation cache for connection: {e}")
            return 0

    async def get_all_annotations_for_connection(
        self,
        connection_id: UUID,
        fallback_fn: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Get all cached annotations for a connection.

        Args:
            connection_id: UUID of the connection
            fallback_fn: Optional async function to call on cache miss

        Returns:
            Dict with 'tables' and 'columns' keys
        """
        cache_key = self._make_connection_key(connection_id)
        try:
            redis_client = await self._get_redis_client()
            cached = await redis_client.get(cache_key)

            if cached:
                logger.debug(f"Annotation cache HIT for connection {connection_id}")
                return json.loads(cached)

            logger.debug(f"Annotation cache MISS for connection {connection_id}")

            if fallback_fn:
                result = await fallback_fn()
                if result:
                    await self.cache_all_annotations(connection_id, result)
                return result

            return {"tables": [], "columns": []}

        except Exception as e:
            logger.warning(f"Failed to get all annotations from cache: {e}")
            if fallback_fn:
                return await fallback_fn()
            return {"tables": [], "columns": []}

    async def cache_all_annotations(
        self,
        connection_id: UUID,
        annotations: Dict[str, Any],
    ) -> str:
        """
        Cache all annotations for a connection.

        Args:
            connection_id: UUID of the connection
            annotations: Dict with 'tables' and 'columns' keys

        Returns:
            Cache key used
        """
        cache_key = self._make_connection_key(connection_id)
        try:
            redis_client = await self._get_redis_client()
            await redis_client.setex(cache_key, self.cache_ttl, json.dumps(annotations))
            logger.debug(f"Cached all annotations for connection {connection_id}")
            return cache_key
        except Exception as e:
            logger.error(f"Failed to cache all annotations: {e}")
            raise

    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
