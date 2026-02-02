"""RAG (Retrieval-Augmented Generation) endpoints."""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict

from text2x.api.auth import User, get_current_user
from text2x.api.models import ErrorResponse
from text2x.services.rag_service import RAGService
from text2x.api.state import app_state
from text2x.services.opensearch_service import OpenSearchService
from text2x.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


class RAGSearchRequest(BaseModel):
    """Request model for RAG similarity search."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Natural language query to search for similar examples",
    )
    provider_id: Optional[str] = Field(
        default=None,
        description="Provider ID to filter results (optional)",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of results to return",
    )
    query_intent: Optional[str] = Field(
        default=None,
        description="Optional query intent filter (e.g., 'aggregation', 'filter')",
    )
    min_similarity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold",
    )


class RAGSearchResult(BaseModel):
    """Single RAG search result."""

    model_config = ConfigDict(extra="allow")

    id: Optional[UUID] = Field(
        default=None,
        description="Example ID (null for sample queries)",
    )
    question: str = Field(
        ...,
        description="Natural language question",
    )
    sql: str = Field(
        ...,
        description="Generated SQL query",
    )
    score: float = Field(
        ...,
        description="Similarity score (0.0 to 1.0)",
    )
    provider_id: Optional[str] = Field(
        default=None,
        description="Provider ID",
    )
    involved_tables: List[str] = Field(
        default_factory=list,
        description="Tables involved in the query",
    )
    query_intent: Optional[str] = Field(
        default=None,
        description="Query intent (e.g., 'aggregation', 'filter')",
    )
    complexity_level: Optional[str] = Field(
        default=None,
        description="Complexity level (e.g., 'simple', 'medium', 'complex')",
    )
    is_good_example: bool = Field(
        default=True,
        description="Whether this is a positive example",
    )


@router.post(
    "/search",
    response_model=List[RAGSearchResult],
    status_code=status.HTTP_200_OK,
    summary="Search for similar query examples",
    description="Search the RAG index for similar query examples using vector similarity search",
)
async def search_similar_queries(
    request: RAGSearchRequest,
    current_user: Optional[User] = Depends(get_current_user),
) -> List[RAGSearchResult]:
    """
    Search for similar query examples in the RAG index.

    This endpoint searches both:
    1. User-generated examples (approved good examples)
    2. Sample queries from the reference index

    Results are ranked by semantic similarity using vector embeddings.

    Args:
        request: Search request with query and filters
        current_user: Current authenticated user (optional)

    Returns:
        List of similar query examples with similarity scores

    Raises:
        HTTPException: For various error conditions
    """
    try:
        logger.info(
            f"RAG search request: query='{request.query[:50]}...', "
            f"provider={request.provider_id}, limit={request.limit}"
        )

        # Initialize RAG service with OpenSearch
        opensearch_service = None
        if app_state.opensearch_client:
            settings = get_settings()
            opensearch_service = OpenSearchService(
                settings=settings,
                opensearch_client=app_state.opensearch_client
            )

        rag_service = RAGService(opensearch_service=opensearch_service)

        # If no provider_id specified, use a default or search across all
        provider_id = request.provider_id or "default"

        # Search for similar examples
        examples = await rag_service.search_examples(
            query=request.query,
            provider_id=provider_id,
            limit=request.limit,
            query_intent=request.query_intent,
            min_similarity=request.min_similarity,
            include_sample_queries=True,
        )

        # Convert to response format
        results = []
        for example in examples:
            # Get the query to return (prefer expert-corrected if available)
            query_text = example.get_query_for_rag() if hasattr(example, 'get_query_for_rag') else example.generated_query

            result = RAGSearchResult(
                id=example.id if example.id else None,
                question=example.natural_language_query,
                sql=query_text,
                score=getattr(example, 'similarity_score', 0.0),
                provider_id=example.provider_id,
                involved_tables=example.involved_tables or [],
                query_intent=example.query_intent,
                complexity_level=example.complexity_level,
                is_good_example=example.is_good_example,
            )
            results.append(result)

        logger.info(f"Found {len(results)} similar examples")
        return results

    except ValueError as e:
        logger.warning(f"Invalid RAG search request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="invalid_request",
                message=str(e),
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"Error searching RAG examples: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="search_error",
                message="Failed to search RAG examples",
                details={"error": str(e)},
            ).model_dump(),
        )
