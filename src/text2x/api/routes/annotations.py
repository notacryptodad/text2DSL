"""Annotation chat endpoints for schema annotation assistance."""
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict

from text2x.agents.annotation_agent import AnnotationAgent
from text2x.agents.base import LLMConfig
from text2x.api.models import ErrorResponse
from text2x.config import settings
from text2x.repositories.annotation import SchemaAnnotationRepository
from text2x.utils.observability import async_log_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/annotations", tags=["annotations"])


# Request/Response Models
class AnnotationChatRequest(BaseModel):
    """Request model for annotation chat endpoint."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="ID of the database provider/connection"
    )
    user_message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User's message or question"
    )
    conversation_id: Optional[UUID] = Field(
        default=None,
        description="Conversation ID for multi-turn chat (optional, will be created if not provided)"
    )
    user_id: Optional[str] = Field(
        default="system",
        description="User ID for saving annotations"
    )
    reset_conversation: bool = Field(
        default=False,
        description="Reset conversation history and start fresh"
    )


class ToolCall(BaseModel):
    """Information about a tool call made by the agent."""

    model_config = ConfigDict(extra="forbid")

    tool: str = Field(..., description="Name of the tool called")
    parameters: Dict[str, Any] = Field(..., description="Parameters passed to the tool")
    result: Dict[str, Any] = Field(..., description="Result returned by the tool")


class ConversationMessage(BaseModel):
    """A single message in the conversation."""

    model_config = ConfigDict(extra="forbid")

    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")


class AnnotationChatResponse(BaseModel):
    """Response model for annotation chat endpoint."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID = Field(..., description="Conversation ID for multi-turn chat")
    response: str = Field(..., description="Agent's response message")
    tool_calls: List[ToolCall] = Field(
        default_factory=list,
        description="Tools called during this turn"
    )
    conversation_history: List[ConversationMessage] = Field(
        default_factory=list,
        description="Full conversation history"
    )


# In-memory storage for conversation agents (in production, use Redis or similar)
# Maps conversation_id -> AnnotationAgent
_conversation_agents: Dict[UUID, AnnotationAgent] = {}


def _get_or_create_agent(
    conversation_id: UUID,
    provider_id: str
) -> AnnotationAgent:
    """
    Get or create an annotation agent for a conversation.

    In production, this should:
    1. Store agents in Redis with TTL
    2. Load provider from database
    3. Handle proper cleanup
    """
    if conversation_id not in _conversation_agents:
        # Create LLM config
        llm_config = LLMConfig(
            model=settings.llm_model,
            api_base=settings.llm_api_base,
            api_key=os.getenv("OPENAI_API_KEY") or settings.llm_api_key,
            temperature=0.3,
            max_tokens=2048,
            timeout=60.0
        )

        # TODO: Load actual provider from database
        # For now, we create a mock provider that needs to be replaced
        # with actual provider lookup based on provider_id
        from text2x.providers.base import QueryProvider, ProviderCapability

        class MockProvider(QueryProvider):
            def get_provider_id(self) -> str:
                return provider_id

            def get_query_language(self) -> str:
                return "SQL"

            def get_capabilities(self) -> List[ProviderCapability]:
                return [
                    ProviderCapability.SCHEMA_INTROSPECTION,
                    ProviderCapability.QUERY_EXECUTION,
                ]

            async def get_schema(self):
                return None

            async def validate_syntax(self, query: str):
                return None

        mock_provider = MockProvider()

        # Create annotation repository
        annotation_repo = SchemaAnnotationRepository()

        # Create agent
        agent = AnnotationAgent(
            llm_config=llm_config,
            provider=mock_provider,
            annotation_repo=annotation_repo
        )

        _conversation_agents[conversation_id] = agent

    return _conversation_agents[conversation_id]


@router.post(
    "/chat",
    response_model=AnnotationChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with annotation assistant",
    description="Multi-turn chat endpoint for schema annotation assistance with tool support",
)
async def annotation_chat(request: AnnotationChatRequest) -> AnnotationChatResponse:
    """
    Chat with the annotation assistant for schema annotation help.

    The agent can:
    1. Sample data from tables to understand content
    2. Get statistics about columns
    3. Save annotations to the database
    4. Answer questions about schema annotation best practices

    This endpoint supports multi-turn conversations. Provide the same conversation_id
    for follow-up messages to maintain context.

    Args:
        request: Chat request with user message and conversation context

    Returns:
        Agent response with any tool calls made

    Raises:
        HTTPException: For various error conditions
    """
    # Generate or use existing conversation ID
    conversation_id = request.conversation_id or uuid4()

    try:
        async with async_log_context(
            conversation_id=str(conversation_id),
            provider_id=request.provider_id,
        ):
            logger.info(
                f"Processing annotation chat for provider {request.provider_id}, "
                f"conversation_id={conversation_id}"
            )

            # Get or create agent for this conversation
            agent = _get_or_create_agent(conversation_id, request.provider_id)

            # Reset conversation if requested
            if request.reset_conversation:
                agent.reset_conversation()
                logger.info(f"Reset conversation {conversation_id}")

            # Process user message
            result = await agent.process({
                "user_message": request.user_message,
                "provider_id": request.provider_id,
                "user_id": request.user_id,
                "reset_conversation": False,  # Already handled above
            })

            # Build response
            response = AnnotationChatResponse(
                conversation_id=conversation_id,
                response=result["response"],
                tool_calls=[ToolCall(**tc) for tc in result.get("tool_calls", [])],
                conversation_history=[
                    ConversationMessage(**msg)
                    for msg in result.get("conversation_history", [])
                ]
            )

            logger.info(
                f"Annotation chat processed successfully: conversation_id={conversation_id}, "
                f"tool_calls={len(response.tool_calls)}"
            )

            return response

    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="invalid_request",
                message=str(e),
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"Error processing annotation chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="processing_error",
                message="Failed to process annotation chat",
                details={"error": str(e)} if settings.debug else None,
            ).model_dump(),
        )


@router.delete(
    "/chat/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="End annotation conversation",
    description="End and cleanup an annotation conversation",
)
async def end_conversation(conversation_id: UUID) -> None:
    """
    End an annotation conversation and cleanup resources.

    Args:
        conversation_id: Conversation to end

    Raises:
        HTTPException: If conversation not found or cleanup fails
    """
    try:
        logger.info(f"Ending annotation conversation {conversation_id}")

        if conversation_id in _conversation_agents:
            agent = _conversation_agents[conversation_id]
            # Cleanup agent resources
            await agent.cleanup()
            del _conversation_agents[conversation_id]
            logger.info(f"Conversation {conversation_id} ended and cleaned up")
        else:
            logger.warning(f"Conversation {conversation_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error="not_found",
                    message="Conversation not found",
                ).model_dump(),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="cleanup_error",
                message="Failed to end conversation",
            ).model_dump(),
        )


@router.get(
    "/chat/{conversation_id}/history",
    response_model=List[ConversationMessage],
    summary="Get conversation history",
    description="Retrieve the full conversation history for an annotation conversation",
)
async def get_conversation_history(conversation_id: UUID) -> List[ConversationMessage]:
    """
    Get the conversation history for an annotation conversation.

    Args:
        conversation_id: Conversation ID

    Returns:
        List of conversation messages

    Raises:
        HTTPException: If conversation not found
    """
    try:
        if conversation_id not in _conversation_agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error="not_found",
                    message="Conversation not found",
                ).model_dump(),
            )

        agent = _conversation_agents[conversation_id]
        history = agent.get_conversation_history()

        return [ConversationMessage(**msg) for msg in history]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch conversation history",
            ).model_dump(),
        )
