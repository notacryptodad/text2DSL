"""
Review service for managing expert review queue and RAG feedback loop.

This service handles:
- Auto-queueing items for expert review based on triggers
- Processing expert review decisions (approve/reject/correct)
- Updating the RAG index with approved examples
"""

import logging
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import UUID

from text2x.models.rag import ExampleStatus
from text2x.repositories.conversation import ConversationTurnRepository
from text2x.repositories.rag import RAGExampleRepository

logger = logging.getLogger(__name__)


class ReviewTrigger(str, PyEnum):
    """Triggers that auto-queue items for expert review."""

    LOW_CONFIDENCE = "low_confidence"
    VALIDATION_FAILURE = "validation_failure"
    NEGATIVE_FEEDBACK = "negative_feedback"
    MULTIPLE_CLARIFICATIONS = "multiple_clarifications"


class ReviewDecision(str, PyEnum):
    """Expert review decisions."""

    APPROVE = "approve"
    REJECT = "reject"
    CORRECT = "correct"


class ReviewService:
    """Service for managing expert review queue."""

    def __init__(
        self,
        rag_repo: Optional[RAGExampleRepository] = None,
        turn_repo: Optional[ConversationTurnRepository] = None,
    ):
        """
        Initialize review service.

        Args:
            rag_repo: RAG example repository
            turn_repo: Conversation turn repository
        """
        self.rag_repo = rag_repo or RAGExampleRepository()
        self.turn_repo = turn_repo or ConversationTurnRepository()

    async def auto_queue_for_review(
        self,
        turn_id: UUID,
        trigger: ReviewTrigger,
        provider_id: str,
    ) -> Optional[UUID]:
        """
        Automatically queue a conversation turn for expert review.

        This method creates a RAG example from a conversation turn and marks it
        as pending review. Items are queued based on triggers such as:
        - Low confidence scores (< 0.7)
        - Validation failures
        - Negative user feedback

        Args:
            turn_id: The conversation turn UUID
            trigger: The trigger that caused this to be queued
            provider_id: The provider ID for filtering

        Returns:
            The UUID of the created RAG example, or None if turn not found

        Raises:
            ValueError: If turn data is invalid
        """
        logger.info(f"Auto-queueing turn {turn_id} for review (trigger: {trigger})")

        # Fetch the conversation turn
        turn = await self.turn_repo.get_by_id(turn_id)
        if not turn:
            logger.warning(f"Turn {turn_id} not found, cannot queue for review")
            return None

        # Determine if this is a good or bad example based on trigger
        is_good_example = trigger != ReviewTrigger.VALIDATION_FAILURE

        # Extract metadata for RAG example
        involved_tables = []
        query_intent = "unknown"
        complexity_level = "medium"

        if turn.schema_context:
            # Extract involved tables from schema context
            relevant_tables = turn.schema_context.get("relevant_tables", [])
            involved_tables = [
                t.get("name", t)
                if isinstance(t, dict)
                else t
                for t in relevant_tables
            ]

        if turn.reasoning_trace:
            # Extract query intent from reasoning trace
            query_construction = turn.reasoning_trace.get("query_construction", {})
            query_intent = query_construction.get("intent", "unknown")
            complexity_level = query_construction.get("complexity", "medium")

        # Build metadata
        metadata = {
            "original_confidence": turn.confidence_score,
            "trigger": trigger.value,
            "turn_id": str(turn_id),
            "validation_result": turn.validation_result,
            "execution_result": turn.execution_result,
        }

        # Create RAG example
        try:
            example = await self.rag_repo.create(
                provider_id=provider_id,
                natural_language_query=turn.user_input,
                generated_query=turn.generated_query,
                involved_tables=involved_tables or ["unknown"],
                query_intent=query_intent,
                complexity_level=complexity_level,
                is_good_example=is_good_example,
                source_conversation_id=turn.conversation_id,
                metadata=metadata,
            )

            logger.info(
                f"Created RAG example {example.id} from turn {turn_id} "
                f"(trigger: {trigger}, is_good: {is_good_example})"
            )
            return example.id

        except Exception as e:
            logger.error(f"Failed to create RAG example from turn {turn_id}: {e}")
            raise

    async def process_review_decision(
        self,
        item_id: UUID,
        decision: ReviewDecision,
        reviewer: str,
        corrected_query: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Process an expert's review decision.

        This method:
        1. Updates the RAG example with the review decision
        2. For APPROVE: Marks as approved (ready for RAG)
        3. For REJECT: Marks as rejected (bad example to avoid)
        4. For CORRECT: Updates with corrected query and approves

        Args:
            item_id: The RAG example UUID
            decision: The review decision
            reviewer: Username/ID of the reviewer
            corrected_query: Expert-corrected query (for CORRECT decision)
            notes: Optional review notes

        Returns:
            Dictionary with review result details, or None if item not found

        Raises:
            ValueError: If decision is invalid or corrected_query missing for CORRECT
        """
        logger.info(
            f"Processing review decision for item {item_id}: "
            f"decision={decision}, reviewer={reviewer}"
        )

        # Validate inputs
        if decision == ReviewDecision.CORRECT and not corrected_query:
            raise ValueError(
                "corrected_query is required when decision is CORRECT"
            )

        # Determine approval status
        approved = decision in (ReviewDecision.APPROVE, ReviewDecision.CORRECT)

        # For CORRECT decision, use the corrected query
        query_to_use = corrected_query if decision == ReviewDecision.CORRECT else None

        # Update the RAG example
        example = await self.rag_repo.mark_reviewed(
            example_id=item_id,
            reviewer=reviewer,
            approved=approved,
            corrected_query=query_to_use,
            notes=notes,
        )

        if not example:
            logger.warning(f"RAG example {item_id} not found")
            return None

        # Build result
        result = {
            "id": example.id,
            "status": example.status.value,
            "approved": approved,
            "reviewed_by": example.reviewed_by,
            "reviewed_at": example.reviewed_at,
            "query_used": example.get_query_for_rag(),
            "is_good_example": example.is_good_example,
        }

        if approved:
            logger.info(
                f"Item {item_id} approved - ready for RAG indexing "
                f"(corrected: {corrected_query is not None})"
            )
        else:
            logger.info(f"Item {item_id} rejected - marked as bad example")

        return result

    async def should_queue_for_review(
        self,
        confidence_score: float,
        validation_passed: bool,
        has_negative_feedback: bool,
        clarification_count: int = 0,
    ) -> tuple[bool, Optional[ReviewTrigger]]:
        """
        Determine if a query result should be queued for review.

        Args:
            confidence_score: Query confidence score (0.0 to 1.0)
            validation_passed: Whether validation passed
            has_negative_feedback: Whether user gave negative feedback
            clarification_count: Number of clarifications requested

        Returns:
            Tuple of (should_queue, trigger) where trigger is the reason
        """
        # Check triggers in priority order
        if not validation_passed:
            return True, ReviewTrigger.VALIDATION_FAILURE

        if has_negative_feedback:
            return True, ReviewTrigger.NEGATIVE_FEEDBACK

        if confidence_score < 0.7:
            return True, ReviewTrigger.LOW_CONFIDENCE

        if clarification_count >= 3:
            return True, ReviewTrigger.MULTIPLE_CLARIFICATIONS

        return False, None

    async def get_review_priority(
        self,
        trigger: ReviewTrigger,
        confidence_score: float = 0.0,
    ) -> int:
        """
        Calculate review priority score.

        Priority scoring:
        - Validation failures: 100 (highest)
        - User feedback: 50
        - Low confidence: 20-40 based on score
        - Multiple clarifications: 10

        Args:
            trigger: Review trigger
            confidence_score: Query confidence score (for LOW_CONFIDENCE trigger)

        Returns:
            Priority score (higher = more urgent)
        """
        priority_map = {
            ReviewTrigger.VALIDATION_FAILURE: 100,
            ReviewTrigger.NEGATIVE_FEEDBACK: 50,
            ReviewTrigger.MULTIPLE_CLARIFICATIONS: 10,
        }

        if trigger in priority_map:
            return priority_map[trigger]

        # For low confidence, priority scales with how low the score is
        if trigger == ReviewTrigger.LOW_CONFIDENCE:
            # confidence 0.0 = priority 40, confidence 0.69 = priority 20
            return int((0.7 - confidence_score) * 100)

        return 0
