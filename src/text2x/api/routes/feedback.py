"""User feedback endpoints."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict

from text2x.api.models import ErrorResponse
from text2x.models.feedback import FeedbackCategory, FeedbackRating
from text2x.services.feedback_service import FeedbackService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


# Request/Response Models
class SubmitFeedbackRequest(BaseModel):
    """Request model for submitting feedback."""

    model_config = ConfigDict(extra="forbid")

    rating: str = Field(
        ...,
        description="User rating: 'up' for thumbs up, 'down' for thumbs down",
        pattern="^(up|down)$",
    )
    category: str = Field(
        ...,
        description="Feedback category",
    )
    feedback_text: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional detailed feedback text",
    )
    user_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User ID providing feedback",
    )


class FeedbackResponse(BaseModel):
    """Response model for feedback."""

    model_config = ConfigDict(extra="allow")

    id: str
    turn_id: str
    conversation_id: str
    rating: str
    category: str
    feedback_text: Optional[str]
    user_id: str
    created_at: str


class FeedbackStatsResponse(BaseModel):
    """Response model for feedback statistics."""

    model_config = ConfigDict(extra="allow")

    total_feedback: int
    thumbs_up: int
    thumbs_down: int
    by_category: dict[str, int]
    approval_rate: float
    avg_confidence_thumbs_up: float
    avg_confidence_thumbs_down: float


class RecentFeedbackItem(BaseModel):
    """Response model for recent feedback items."""

    model_config = ConfigDict(extra="allow")

    id: str
    turn_id: str
    rating: str
    category: str
    feedback_text: Optional[str]
    user_id: str
    created_at: str


@router.get(
    "/stats",
    response_model=FeedbackStatsResponse,
    summary="Get feedback statistics",
    description="Get aggregated statistics about user feedback",
)
async def get_feedback_stats(
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Number of days to look back for statistics",
    ),
) -> FeedbackStatsResponse:
    """
    Get feedback statistics.

    Returns aggregated metrics including:
    - Total feedback count
    - Thumbs up vs thumbs down counts
    - Breakdown by category
    - Approval rate
    - Average confidence scores by rating

    Args:
        days: Number of days to look back (default 30, max 365)

    Returns:
        Aggregated feedback statistics

    Raises:
        HTTPException: If stats fetch fails (500)
    """
    try:
        logger.info(f"Fetching feedback stats for last {days} days")

        service = FeedbackService()
        stats = await service.get_stats(days=days)

        response = FeedbackStatsResponse(
            total_feedback=stats.total_feedback,
            thumbs_up=stats.thumbs_up,
            thumbs_down=stats.thumbs_down,
            by_category=stats.by_category,
            approval_rate=stats.approval_rate,
            avg_confidence_thumbs_up=stats.avg_confidence_thumbs_up,
            avg_confidence_thumbs_down=stats.avg_confidence_thumbs_down,
        )

        logger.info(
            f"Fetched feedback stats: {stats.total_feedback} total, "
            f"approval_rate={stats.approval_rate:.2%}"
        )
        return response

    except Exception as e:
        logger.error(f"Error fetching feedback stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch feedback statistics",
            ).model_dump(),
        )


class FeedbackListItem(BaseModel):
    """Response model for feedback list items."""

    model_config = ConfigDict(extra="allow")

    id: str
    turn_id: str
    conversation_id: Optional[str] = None
    rating: str
    category: str
    feedback_text: Optional[str]
    user_id: str
    created_at: str


class FeedbackListResponse(BaseModel):
    """Response model for paginated feedback list."""

    items: list[FeedbackListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get(
    "",
    response_model=list[dict],
    summary="Get paginated feedback list",
    description="Get a paginated list of feedback items with optional filters",
)
async def list_feedback(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    date_range: Optional[str] = Query(
        None,
        description="Date range filter (e.g., '7d', '30d', '90d')",
    ),
    rating: Optional[str] = Query(
        None,
        description="Filter by rating ('up' or 'down')",
        pattern="^(up|down)$",
    ),
    workspace_id: Optional[str] = Query(
        None,
        description="Filter by workspace ID",
    ),
) -> list[dict]:
    """
    Get a paginated list of feedback items.

    Supports filtering by date range, rating, and workspace.

    Args:
        page: Page number (default 1)
        page_size: Items per page (default 20, max 100)
        date_range: Optional date range filter (e.g., '7d', '30d', '90d')
        rating: Optional rating filter ('up' or 'down')
        workspace_id: Optional workspace ID filter

    Returns:
        Paginated list of feedback items

    Raises:
        HTTPException: If fetch fails (500)
    """
    try:
        # Parse date range to days
        days = None
        if date_range:
            try:
                days = int(date_range.rstrip("d"))
            except ValueError:
                pass

        # Convert rating filter if provided
        rating_filter = None
        if rating:
            try:
                rating_filter = FeedbackRating(rating)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error="invalid_rating",
                        message=f"Invalid rating filter: {rating}",
                    ).model_dump(),
                )

        service = FeedbackService()
        items, total = await service.get_feedback_list(
            page=page,
            page_size=page_size,
            days=days,
            rating_filter=rating_filter,
            workspace_id=workspace_id,
        )

        # Build response matching frontend expectations
        response = [
            {
                "id": str(item.id),
                "turn_id": str(item.turn_id),
                "conversation_id": str(item.turn_id),  # Use turn_id as conversation proxy
                "helpful": item.rating == FeedbackRating.UP,
                "rating": item.rating.value if hasattr(item.rating, "value") else str(item.rating),
                "category": item.feedback_category.value if item.feedback_category else "",
                "feedback_text": item.feedback_text,
                "comment": item.feedback_text,
                "query": None,
                "user_id": item.user_id,
                "created_at": item.created_at.isoformat() if item.created_at else "",
            }
            for item in items
        ]

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching feedback list: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch feedback list",
            ).model_dump(),
        )


@router.get(
    "/recent",
    response_model=list[RecentFeedbackItem],
    summary="Get recent feedback",
    description="Get recent feedback items across all conversations",
)
async def get_recent_feedback(
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum number of items to return",
    ),
    rating: Optional[str] = Query(
        None,
        description="Optional filter by rating ('up' or 'down')",
        pattern="^(up|down)$",
    ),
) -> list[RecentFeedbackItem]:
    """
    Get recent feedback items.

    Returns a list of recent feedback submissions, optionally filtered by rating.
    Useful for monitoring user sentiment and identifying problematic queries.

    Args:
        limit: Maximum number of items to return (default 50, max 200)
        rating: Optional filter by 'up' or 'down'

    Returns:
        List of recent feedback items

    Raises:
        HTTPException: If fetch fails (500)
    """
    try:
        logger.info(f"Fetching recent feedback: limit={limit}, rating={rating}")

        # Convert rating filter if provided
        rating_filter = None
        if rating:
            try:
                rating_filter = FeedbackRating(rating)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error="invalid_rating",
                        message=f"Invalid rating filter: {rating}",
                    ).model_dump(),
                )

        service = FeedbackService()
        feedback_items = await service.get_recent_feedback(
            limit=limit,
            rating_filter=rating_filter,
        )

        response = [
            RecentFeedbackItem(
                id=str(item.id),
                turn_id=str(item.turn_id),
                rating=item.rating.value,
                category=item.feedback_category.value,
                feedback_text=item.feedback_text,
                user_id=item.user_id,
                created_at=item.created_at.isoformat() if item.created_at else "",
            )
            for item in feedback_items
        ]

        logger.info(f"Fetched {len(response)} recent feedback items")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching recent feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch recent feedback",
            ).model_dump(),
        )
