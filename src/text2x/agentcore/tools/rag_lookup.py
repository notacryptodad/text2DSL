"""RAG lookup tool for dynamic example retrieval during query generation."""

import logging
from typing import Any, Optional

from strands.tools import tool

logger = logging.getLogger(__name__)

# Global services - injected via init_rag_tool()
_opensearch_service: Optional[Any] = None
_rag_service: Optional[Any] = None
_main_loop: Optional[Any] = None


def init_rag_tool(opensearch_service: Any, rag_service: Any, main_loop: Any = None) -> None:
    """Initialize RAG tool by injecting required services.

    Must be called before the tool can be used.

    Args:
        opensearch_service: OpenSearchService instance
        rag_service: RAGService instance
        main_loop: Optional main event loop for async execution
    """
    global _opensearch_service, _rag_service, _main_loop
    _opensearch_service = opensearch_service
    _rag_service = rag_service
    _main_loop = main_loop
    logger.info("RAG tool initialized with services")


def _run_async(coro, timeout=120):
    """Run an async coroutine from a sync context."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    # If we're in the main event loop thread
    if loop and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=timeout)

    # We're in a worker thread — schedule on the captured main loop
    if _main_loop and _main_loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, _main_loop)
        return future.result(timeout=timeout)

    # Fallback: no main loop captured
    logger.warning("[_run_async] No main event loop available, falling back to asyncio.run()")
    return asyncio.run(coro)


@tool
def search_similar_queries(
    keywords: str,
    limit: int = 3,
    provider_id: str = "",
) -> dict:
    """Search for similar example queries to help generate the current query.

    Use this tool when you need examples of how similar queries were structured:
    - For complex queries (joins, aggregations, subqueries, multiple conditions)
    - When you need examples of specific syntax patterns for the database
    - When the user's question is ambiguous or could benefit from seeing similar examples

    Don't use this for simple queries or basic schema lookups.

    Args:
        keywords: Search keywords describing the query intent and structure.
                 Examples: "join users orders", "group by date aggregate count",
                 "subquery filter nested", "window function partition by"
        limit: Maximum number of examples to return (1-5, default 3).
               Use 2-3 for most queries, 4-5 for very complex queries.
        provider_id: Optional provider ID to filter examples (leave empty to search all).

    Returns:
        Dictionary with the following structure:
        {
            "success": True/False,
            "examples": [
                {
                    "natural_language_query": "user's original question",
                    "generated_query": "the generated database query",
                    "similarity_score": 0.85,  # 0.0-1.0
                    "query_intent": "aggregation|filter|join|...",
                    "complexity_level": "simple|medium|complex"
                },
                ...
            ],
            "count": number of examples returned,
            "search_keywords": keywords that were searched,
            "error": "error message if success=False"
        }

    Examples:
        search_similar_queries("join users orders", limit=3)
        search_similar_queries("aggregate sales by month", limit=2)
        search_similar_queries("nested subquery filter", limit=4)
    """
    # Validate services are initialized
    if not _rag_service:
        return {
            "success": False,
            "examples": [],
            "count": 0,
            "error": "RAG service not initialized. Call init_rag_tool() first.",
            "search_keywords": keywords,
        }

    # Validate inputs
    if not keywords or not keywords.strip():
        return {
            "success": False,
            "examples": [],
            "count": 0,
            "error": "keywords parameter is required and cannot be empty",
            "search_keywords": keywords,
        }

    # Clamp limit to valid range
    limit = max(1, min(5, limit))

    try:
        logger.info(
            f"[search_similar_queries] Searching with keywords='{keywords}', "
            f"provider={provider_id or 'all'}, limit={limit}"
        )

        # Run async search
        async def search_async():
            return await _rag_service.search_examples(
                query=keywords,
                provider_id=provider_id,
                limit=limit,
                min_similarity=0.6,  # Use reasonable threshold
                include_sample_queries=True,
            )

        raw_examples = _run_async(search_async())

        # Filter for approved good examples
        try:
            from text2x.models.rag import ExampleStatus
            filtered_examples = [
                ex for ex in raw_examples
                if ex.is_good_example and ex.status == ExampleStatus.APPROVED
            ]
        except ImportError:
            # Fallback if models not available
            filtered_examples = [
                ex for ex in raw_examples
                if getattr(ex, 'is_good_example', True)
            ]

        # Format for tool response
        examples = []
        for ex in filtered_examples[:limit]:
            # Get the query - prefer expert-corrected version
            generated_query = (
                ex.get_query_for_rag()
                if hasattr(ex, "get_query_for_rag")
                else getattr(ex, "generated_query", "")
            )

            examples.append({
                "natural_language_query": getattr(ex, "natural_language_query", ""),
                "generated_query": generated_query,
                "similarity_score": getattr(ex, "similarity_score", 0.0),
                "query_intent": getattr(ex, "query_intent", "unknown"),
                "complexity_level": getattr(ex, "complexity_level", "medium"),
            })

        logger.info(
            f"[search_similar_queries] Found {len(examples)} examples "
            f"(filtered from {len(raw_examples)} results)"
        )

        return {
            "success": True,
            "examples": examples,
            "count": len(examples),
            "search_keywords": keywords,
        }

    except Exception as e:
        logger.error(f"[search_similar_queries] Error: {e}", exc_info=True)
        return {
            "success": False,
            "examples": [],
            "count": 0,
            "error": f"Search failed: {str(e)}",
            "search_keywords": keywords,
        }
