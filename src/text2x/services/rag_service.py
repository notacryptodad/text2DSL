"""
RAG (Retrieval-Augmented Generation) service for managing query examples.

This service provides:
- Adding/removing examples to the RAG index
- Searching for similar examples
- Integration with OpenSearch for vector embeddings
- Managing approved examples for query generation
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from text2x.models.rag import ExampleStatus, RAGExample
from text2x.repositories.rag import RAGExampleRepository
from text2x.services.opensearch_service import OpenSearchService

logger = logging.getLogger(__name__)


class RAGService:
    """Service for managing RAG examples and retrieval."""

    def __init__(
        self,
        rag_repo: Optional[RAGExampleRepository] = None,
        opensearch_service: Optional[OpenSearchService] = None,
    ):
        """
        Initialize RAG service.

        Args:
            rag_repo: RAG example repository
            opensearch_service: OpenSearch service for vector search (optional)
        """
        self.rag_repo = rag_repo or RAGExampleRepository()
        self.opensearch_service = opensearch_service

    async def add_example(
        self,
        nl_query: str,
        generated_query: str,
        is_good: bool,
        provider_id: str,
        involved_tables: Optional[List[str]] = None,
        query_intent: str = "unknown",
        complexity_level: str = "medium",
        auto_approve: bool = False,
        metadata: Optional[dict] = None,
    ) -> RAGExample:
        """
        Add a new example to the RAG system.

        This creates a RAG example and optionally indexes it in OpenSearch
        for vector-based retrieval. Examples can be:
        - Good examples: Successful queries to learn from
        - Bad examples: Failed queries to avoid

        Args:
            nl_query: Natural language query
            generated_query: Generated DSL query
            is_good: Whether this is a good example (vs. bad example to avoid)
            provider_id: Provider ID for filtering
            involved_tables: List of table names involved in query
            query_intent: Query intent (aggregation, filter, join, etc.)
            complexity_level: Complexity level (simple, medium, complex)
            auto_approve: Whether to auto-approve (skip review queue)
            metadata: Additional metadata

        Returns:
            The created RAG example

        Raises:
            ValueError: If required fields are invalid
        """
        logger.info(
            f"Adding RAG example: is_good={is_good}, provider={provider_id}, "
            f"auto_approve={auto_approve}"
        )

        # Validate inputs
        if not nl_query or not generated_query:
            raise ValueError("nl_query and generated_query are required")

        if not provider_id:
            raise ValueError("provider_id is required")

        # Create the example
        example = await self.rag_repo.create(
            provider_id=provider_id,
            natural_language_query=nl_query,
            generated_query=generated_query,
            involved_tables=involved_tables or ["unknown"],
            query_intent=query_intent,
            complexity_level=complexity_level,
            is_good_example=is_good,
            metadata=metadata,
        )

        # Auto-approve if requested
        if auto_approve:
            logger.info(f"Auto-approving RAG example {example.id}")
            await self.rag_repo.mark_reviewed(
                example_id=example.id,
                reviewer="system",
                approved=True,
            )

            # Index in OpenSearch if available
            if self.opensearch_service:
                await self._index_in_opensearch(example)

        logger.info(
            f"Created RAG example {example.id} "
            f"(status: {'approved' if auto_approve else 'pending_review'})"
        )
        return example

    async def remove_example(self, example_id: UUID) -> bool:
        """
        Remove an example from the RAG system.

        This deletes the example from both the database and OpenSearch index.

        Args:
            example_id: The example UUID to remove

        Returns:
            True if removed, False if not found

        Raises:
            Exception: If deletion fails
        """
        logger.info(f"Removing RAG example {example_id}")

        # Remove from OpenSearch first
        if self.opensearch_service:
            try:
                await self._remove_from_opensearch(example_id)
            except Exception as e:
                logger.warning(
                    f"Failed to remove example {example_id} from OpenSearch: {e}"
                )
                # Continue with database deletion even if OpenSearch fails

        # Remove from database
        deleted = await self.rag_repo.delete(example_id)

        if deleted:
            logger.info(f"Successfully removed RAG example {example_id}")
        else:
            logger.warning(f"RAG example {example_id} not found")

        return deleted

    async def search_examples(
        self,
        query: str,
        provider_id: str,
        limit: int = 5,
        query_intent: Optional[str] = None,
        min_similarity: float = 0.7,
    ) -> List[RAGExample]:
        """
        Search for similar examples using hybrid retrieval.

        This performs a hybrid search combining:
        1. Keyword-based search (PostgreSQL full-text search)
        2. Vector similarity search (OpenSearch embeddings) if available

        Only approved good examples are returned for use in query generation.

        Args:
            query: Natural language query to search for
            provider_id: Provider ID to filter by
            limit: Maximum number of examples to return
            query_intent: Optional intent filter (aggregation, filter, etc.)
            min_similarity: Minimum similarity threshold (0.0 to 1.0)

        Returns:
            List of similar RAG examples, ranked by relevance

        Raises:
            ValueError: If inputs are invalid
        """
        logger.info(
            f"Searching RAG examples: query='{query[:50]}...', "
            f"provider={provider_id}, limit={limit}, intent={query_intent}"
        )

        if not query or not provider_id:
            raise ValueError("query and provider_id are required")

        # Use OpenSearch hybrid search if available
        if self.opensearch_service:
            try:
                examples = await self._search_opensearch(
                    query=query,
                    provider_id=provider_id,
                    query_intent=query_intent,
                    min_similarity=min_similarity,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(f"OpenSearch search failed: {e}, falling back to database")
                # Fall back to database search
                examples = await self._search_database(
                    query=query,
                    provider_id=provider_id,
                    query_intent=query_intent,
                    limit=limit,
                )
        else:
            # Fall back to database-only search
            examples = await self._search_database(
                query=query,
                provider_id=provider_id,
                query_intent=query_intent,
                limit=limit,
            )

        logger.info(f"Found {len(examples)} similar RAG examples")
        return examples

    async def _search_opensearch(
        self,
        query: str,
        provider_id: str,
        query_intent: Optional[str],
        min_similarity: float,
        limit: int,
    ) -> List[RAGExample]:
        """
        Search examples using OpenSearch hybrid search.

        Combines vector similarity and keyword matching for best results.

        Args:
            query: Natural language query
            provider_id: Provider ID filter
            query_intent: Optional intent filter
            min_similarity: Minimum similarity threshold
            limit: Maximum results

        Returns:
            List of RAG examples from OpenSearch
        """
        logger.debug(f"Searching OpenSearch with query: '{query[:50]}...'")

        # Search OpenSearch with hybrid search
        search_results = await self.opensearch_service.search_similar(
            query_text=query,
            k=limit,
            provider_id=provider_id,
            query_intent=query_intent,
            min_score=min_similarity,
            hybrid=True,
        )

        # Convert search results to RAGExample objects
        examples = []
        for result in search_results:
            try:
                # Fetch full example from database to get all fields
                example_id = UUID(result["id"])
                example = await self.rag_repo.get_by_id(example_id)

                if example:
                    # Add similarity score as a dynamic attribute
                    example.similarity_score = result["score"]
                    examples.append(example)
                else:
                    logger.warning(
                        f"Example {example_id} found in OpenSearch but not in database"
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch example {result.get('id')}: {e}")
                continue

        logger.debug(f"Found {len(examples)} examples from OpenSearch")
        return examples

    async def _search_database(
        self,
        query: str,
        provider_id: str,
        query_intent: Optional[str],
        limit: int,
    ) -> List[RAGExample]:
        """
        Search database for approved examples.

        This is a simple keyword-based search using the repository.
        Future: Add full-text search capabilities.

        Args:
            query: Natural language query
            provider_id: Provider ID filter
            query_intent: Optional intent filter
            limit: Maximum results

        Returns:
            List of approved RAG examples
        """
        # Get approved examples filtered by provider and intent
        examples = await self.rag_repo.list_approved(
            provider_id=provider_id,
            query_intent=query_intent,
            limit=limit * 2,  # Get more to filter/rank
        )

        # Improved keyword matching with TF-IDF-like scoring
        query_lower = query.lower()
        query_words = set(word for word in query_lower.split() if len(word) > 2)

        scored_examples = []

        for example in examples:
            nl_query_lower = example.natural_language_query.lower()
            example_words = set(word for word in nl_query_lower.split() if len(word) > 2)

            # Keyword overlap score
            overlap = len(query_words & example_words)
            overlap_score = overlap / max(len(query_words), 1) if query_words else 0

            # Substring matching score (for partial matches)
            substring_score = 0
            for qword in query_words:
                if any(qword in eword or eword in qword for eword in example_words):
                    substring_score += 0.5

            substring_score = min(1.0, substring_score / max(len(query_words), 1))

            # Combined score (weighted)
            score = 0.7 * overlap_score + 0.3 * substring_score

            # Boost score for good examples
            if example.is_good_example:
                score *= 1.1

            scored_examples.append((score, example))

        # Sort by score descending
        scored_examples.sort(key=lambda x: x[0], reverse=True)

        # Return top results
        return [example for _, example in scored_examples[:limit]]

    async def _index_in_opensearch(self, example: RAGExample) -> None:
        """
        Index a RAG example in OpenSearch for vector search.

        This generates embeddings for the natural language query and
        stores them in OpenSearch for similarity search.

        Args:
            example: The RAG example to index

        Raises:
            Exception: If indexing fails
        """
        if not self.opensearch_service:
            logger.debug("OpenSearch service not available, skipping indexing")
            return

        logger.info(f"Indexing RAG example {example.id} in OpenSearch")

        try:
            # Prepare metadata
            metadata = {
                "nl_query": example.natural_language_query,
                "generated_query": example.get_query_for_rag(),
                "provider_id": example.provider_id,
                "status": example.status.value,
                "is_good_example": example.is_good_example,
                "involved_tables": example.involved_tables,
                "query_intent": example.query_intent,
                "complexity_level": example.complexity_level,
                "reviewed_by": example.reviewed_by,
                "reviewed_at": example.reviewed_at.isoformat() if example.reviewed_at else None,
                "expert_corrected_query": example.expert_corrected_query,
                "metadata": example.extra_metadata,
                "created_at": example.created_at.isoformat() if hasattr(example, "created_at") and example.created_at else datetime.utcnow().isoformat(),
                "updated_at": example.updated_at.isoformat() if hasattr(example, "updated_at") and example.updated_at else datetime.utcnow().isoformat(),
            }

            # Index document (embedding will be generated automatically)
            await self.opensearch_service.index_document(
                doc_id=str(example.id),
                vector=None,  # Will be generated from nl_query
                metadata=metadata,
            )

            # Update example to mark embeddings as generated
            example.embeddings_generated = True
            await self.rag_repo.update(example)

            logger.info(f"Successfully indexed RAG example {example.id}")

        except Exception as e:
            logger.error(f"Failed to index example {example.id}: {e}")
            raise

    async def _remove_from_opensearch(self, example_id: UUID) -> None:
        """
        Remove a RAG example from OpenSearch index.

        Args:
            example_id: The example UUID to remove

        Raises:
            Exception: If removal fails
        """
        if not self.opensearch_service:
            logger.debug("OpenSearch service not available, skipping removal")
            return

        logger.info(f"Removing RAG example {example_id} from OpenSearch")

        try:
            # Delete document from OpenSearch
            deleted = await self.opensearch_service.delete_document(str(example_id))

            if deleted:
                logger.info(f"Successfully removed example {example_id} from OpenSearch")
            else:
                logger.warning(f"Example {example_id} not found in OpenSearch")

        except Exception as e:
            logger.error(f"Failed to remove example {example_id} from OpenSearch: {e}")
            raise

    async def _enhance_with_vector_search(
        self,
        query: str,
        examples: List[RAGExample],
        min_similarity: float,
        limit: int,
    ) -> List[RAGExample]:
        """
        Enhance search results with vector similarity scores.

        This uses OpenSearch to compute semantic similarity between
        the query and retrieved examples, re-ranking them by relevance.

        Note: This method is deprecated in favor of direct OpenSearch hybrid search.
        It's kept for backward compatibility and fallback scenarios.

        Args:
            query: Natural language query
            examples: Initial examples from database search
            min_similarity: Minimum similarity threshold
            limit: Maximum results to return

        Returns:
            Re-ranked list of examples
        """
        if not self.opensearch_service:
            logger.debug("OpenSearch service not available for enhancement")
            return examples[:limit]

        try:
            # Get example IDs
            example_ids = {str(ex.id) for ex in examples}

            # Search OpenSearch for vector similarity
            search_results = await self.opensearch_service.search_similar(
                query_text=query,
                k=len(examples),  # Search within our candidate set
                min_score=min_similarity,
                hybrid=False,  # Pure vector search for enhancement
            )

            # Build score map
            score_map = {
                result["id"]: result["score"]
                for result in search_results
                if result["id"] in example_ids
            }

            # Add scores to examples
            for example in examples:
                example_id = str(example.id)
                example.similarity_score = score_map.get(example_id, 0.0)

            # Filter by minimum similarity
            filtered = [ex for ex in examples if ex.similarity_score >= min_similarity]

            # Re-rank by similarity score
            filtered.sort(key=lambda ex: ex.similarity_score, reverse=True)

            logger.debug(
                f"Enhanced {len(examples)} examples, "
                f"{len(filtered)} passed min_similarity threshold"
            )

            return filtered[:limit]

        except Exception as e:
            logger.warning(f"Vector enhancement failed: {e}")
            # Return original examples as fallback
            return examples[:limit]

    async def get_statistics(self, provider_id: Optional[str] = None) -> dict:
        """
        Get RAG system statistics.

        Args:
            provider_id: Optional provider filter

        Returns:
            Dictionary with statistics
        """
        logger.info(f"Getting RAG statistics for provider={provider_id}")

        # Get counts by status
        pending = await self.rag_repo.list_pending_review(
            provider_id=provider_id,
            limit=1000,  # Just for counting
        )

        approved = await self.rag_repo.list_by_provider(
            provider_id=provider_id or "",
            status=ExampleStatus.APPROVED,
            limit=1000,
        ) if provider_id else []

        rejected = await self.rag_repo.list_by_provider(
            provider_id=provider_id or "",
            status=ExampleStatus.REJECTED,
            limit=1000,
        ) if provider_id else []

        return {
            "pending_review": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "total": len(pending) + len(approved) + len(rejected),
            "provider_id": provider_id,
        }
