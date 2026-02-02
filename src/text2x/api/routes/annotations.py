"""Annotation chat endpoints for schema annotation assistance."""
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from text2x.agents.annotation_agent import AnnotationAgent
from text2x.agents.base import LLMConfig
from text2x.api.models import ErrorResponse, TableInfo
from text2x.api.state import app_state
from text2x.config import settings
from text2x.models.workspace import Connection, ProviderType
from text2x.providers.sql_provider import SQLConnectionConfig, SQLProvider
from text2x.repositories.annotation import SchemaAnnotationRepository
from text2x.services.schema_service import SchemaService
from text2x.utils.observability import async_log_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/annotations", tags=["annotations"])


async def get_session() -> AsyncSession:
    """Get database session from app state."""
    session_maker = async_sessionmaker(
        app_state.db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return session_maker()


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


async def _get_or_create_agent(
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

        # Load actual provider from database using connection_id
        try:
            connection_id = UUID(provider_id)
        except ValueError:
            raise ValueError(f"Invalid connection ID format: {provider_id}")

        async with await get_session() as session:
            # Query connection from database with eagerly loaded provider
            from sqlalchemy.orm import selectinload
            conn_stmt = select(Connection).options(selectinload(Connection.provider)).where(Connection.id == connection_id)
            conn_result = await session.execute(conn_stmt)
            connection = conn_result.scalar_one_or_none()

            if not connection:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Connection {provider_id} not found",
                    ).model_dump(),
                )

            # Get provider type (now eagerly loaded)
            provider_type = connection.provider.type

            # Create appropriate provider based on type
            if provider_type in [
                ProviderType.POSTGRESQL,
                ProviderType.MYSQL,
                ProviderType.REDSHIFT,
            ]:
                # Create SQL provider
                credentials = connection.credentials or {}
                username = credentials.get("username", "")
                password = credentials.get("password", "")

                # Map provider type to dialect
                dialect_map = {
                    ProviderType.POSTGRESQL: "postgresql",
                    ProviderType.MYSQL: "mysql",
                    ProviderType.REDSHIFT: "postgresql",
                }
                dialect = dialect_map.get(provider_type, "postgresql")

                sql_config = SQLConnectionConfig(
                    host=connection.host,
                    port=connection.port or 5432,
                    database=connection.database,
                    username=username,
                    password=password,
                    dialect=dialect,
                    extra_params=connection.connection_options or {}
                )

                provider = SQLProvider(sql_config)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error="unsupported_provider",
                        message=f"Provider type {provider_type.value} not supported for annotations",
                    ).model_dump(),
                )

        # Create annotation repository
        annotation_repo = SchemaAnnotationRepository()

        # Create agent
        agent = AnnotationAgent(
            llm_config=llm_config,
            provider=provider,
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
            agent = await _get_or_create_agent(conversation_id, request.provider_id)

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


# Schema endpoints for Scenario 2
class SchemaResponse(BaseModel):
    """Response model for schema endpoint."""

    model_config = ConfigDict(extra="forbid")

    connection_id: UUID = Field(..., description="Connection ID")
    provider_type: str = Field(..., description="Provider type (e.g., postgresql)")
    tables: List[TableInfo] = Field(default_factory=list, description="List of tables")
    table_count: int = Field(..., ge=0, description="Number of tables")
    last_refreshed: Optional[str] = Field(None, description="Last refresh timestamp")


class AutoAnnotateRequest(BaseModel):
    """Request model for auto-annotation endpoint."""

    model_config = ConfigDict(extra="forbid")

    table_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the table to auto-annotate"
    )
    include_columns: bool = Field(
        default=True,
        description="Whether to generate annotations for columns"
    )


class AutoAnnotateResponse(BaseModel):
    """Response model for auto-annotation endpoint."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID = Field(..., description="Conversation ID for follow-up")
    table_name: str = Field(..., description="Table that was annotated")
    suggestions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Suggested annotations"
    )
    message: str = Field(..., description="Status message")


class AnnotationResponse(BaseModel):
    """Response model for annotation."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID = Field(..., description="Annotation ID")
    provider_id: str = Field(..., description="Provider ID")
    table_name: Optional[str] = Field(None, description="Table name")
    column_name: Optional[str] = Field(None, description="Column name")
    description: str = Field(..., description="Description")
    business_terms: Optional[List[str]] = Field(None, description="Business terms")
    examples: Optional[List[str]] = Field(None, description="Examples")
    relationships: Optional[List[str]] = Field(None, description="Relationships")
    date_format: Optional[str] = Field(None, description="Date format")
    enum_values: Optional[List[str]] = Field(None, description="Enum values")
    sensitive: bool = Field(..., description="Whether data is sensitive")
    created_by: str = Field(..., description="User who created the annotation")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class AnnotationUpdate(BaseModel):
    """Request model for updating an annotation."""

    model_config = ConfigDict(extra="forbid")

    description: Optional[str] = Field(None, min_length=1, description="Description")
    business_terms: Optional[List[str]] = Field(None, description="Business terms")
    examples: Optional[List[str]] = Field(None, description="Examples")
    relationships: Optional[List[str]] = Field(None, description="Relationships")
    date_format: Optional[str] = Field(None, description="Date format")
    enum_values: Optional[List[str]] = Field(None, description="Enum values")
    sensitive: Optional[bool] = Field(None, description="Whether data is sensitive")


@router.get(
    "/workspaces/{workspace_id}/connections/{connection_id}/schema",
    response_model=SchemaResponse,
    status_code=status.HTTP_200_OK,
    summary="Get connection schema",
    description="Retrieve the full database schema for a connection",
)
async def get_connection_schema(
    workspace_id: UUID,
    connection_id: UUID
) -> SchemaResponse:
    """
    Get the complete database schema for a connection.

    This endpoint retrieves the schema from cache if available,
    or introspects the database if needed.

    Args:
        workspace_id: UUID of the workspace
        connection_id: UUID of the connection

    Returns:
        Schema information including tables, columns, and relationships

    Raises:
        HTTPException: If connection not found or schema retrieval fails
    """
    try:
        logger.info(
            f"Fetching schema for connection {connection_id} "
            f"in workspace {workspace_id}"
        )

        # Create schema service
        schema_service = SchemaService()

        # Get schema
        schema = await schema_service.get_schema(connection_id)

        if not schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error="not_found",
                    message=f"Connection {connection_id} not found or schema unavailable",
                ).model_dump(),
            )

        # Convert to response format
        tables = [
            TableInfo(
                name=table.name,
                schema=table.schema,
                columns=[
                    {
                        "name": col.name,
                        "type": col.type,
                        "nullable": col.nullable,
                        "primary_key": col.primary_key,
                        "unique": col.unique,
                    }
                    for col in table.columns
                ],
                primary_keys=[col.name for col in table.columns if col.primary_key],
                foreign_keys=[
                    {
                        "column": ",".join(fk.constrained_columns),
                        "references_table": fk.referred_table,
                        "references_column": ",".join(fk.referred_columns),
                    }
                    for fk in table.foreign_keys
                ],
                row_count=table.row_count,
                description=table.comment,
            )
            for table in schema.tables
        ]

        response = SchemaResponse(
            connection_id=connection_id,
            provider_type=schema.metadata.get("provider_type", "unknown"),
            tables=tables,
            table_count=len(tables),
            last_refreshed=schema.metadata.get("last_refreshed"),
        )

        logger.info(
            f"Retrieved schema for connection {connection_id}: "
            f"{response.table_count} tables"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching schema: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch connection schema",
                details={"error": str(e)} if settings.debug else None,
            ).model_dump(),
        )


@router.post(
    "/workspaces/{workspace_id}/connections/{connection_id}/schema/auto-annotate",
    response_model=AutoAnnotateResponse,
    status_code=status.HTTP_200_OK,
    summary="Auto-annotate table schema",
    description="Use LLM to automatically generate schema annotations for a table",
)
async def auto_annotate_table(
    workspace_id: UUID,
    connection_id: UUID,
    request: AutoAnnotateRequest
) -> AutoAnnotateResponse:
    """
    Automatically generate schema annotations for a table using LLM.

    This endpoint:
    1. Retrieves the table schema
    2. Samples data from the table
    3. Uses LLM to suggest annotations
    4. Returns suggestions in a conversation context for expert review

    Args:
        workspace_id: UUID of the workspace
        connection_id: UUID of the connection
        request: Auto-annotation request with table name

    Returns:
        Suggested annotations and conversation ID for follow-up

    Raises:
        HTTPException: If table not found or annotation fails
    """
    try:
        logger.info(
            f"Auto-annotating table {request.table_name} for connection {connection_id}"
        )

        # Create conversation ID for this annotation session
        conversation_id = uuid4()

        # Get or create agent for this conversation
        agent = await _get_or_create_agent(conversation_id, str(connection_id))

        # Build prompt for auto-annotation
        prompt = f"""I need help annotating the table '{request.table_name}'.

Please:
1. Sample some data from this table to understand its structure
2. Analyze the columns and their data types
3. Suggest meaningful annotations including:
   - Table description
   - Column descriptions
   - Business terms (alternative names)
   - Any patterns or relationships you notice

Let's start by sampling data from the table."""

        # Process the request
        result = await agent.process({
            "user_message": prompt,
            "provider_id": str(connection_id),
            "user_id": "system",
            "reset_conversation": True,
        })

        # Extract suggestions from response
        # In a real implementation, we'd parse the LLM response more carefully
        suggestions = {
            "table_name": request.table_name,
            "llm_response": result["response"],
            "tool_calls": result.get("tool_calls", []),
        }

        response = AutoAnnotateResponse(
            conversation_id=conversation_id,
            table_name=request.table_name,
            suggestions=suggestions,
            message=(
                f"Auto-annotation started for table '{request.table_name}'. "
                f"Continue the conversation using conversation_id {conversation_id} "
                "to review and refine the suggestions."
            ),
        )

        logger.info(
            f"Auto-annotation completed for table {request.table_name}: "
            f"conversation_id={conversation_id}"
        )

        return response

    except Exception as e:
        logger.error(f"Error in auto-annotation: {e}", exc_info=True)
        
        # Provide more helpful error message
        error_msg = str(e)
        if "missing an 'http://' or 'https://' protocol" in error_msg:
            error_msg = "LLM not configured. Please set LLM_API_BASE environment variable or configure Bedrock."
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="annotation_error",
                message=f"Failed to auto-annotate table: {error_msg}",
                details={"error": str(e)} if settings.debug else None,
            ).model_dump(),
        )


@router.get(
    "/{annotation_id}",
    response_model=AnnotationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get annotation by ID",
    description="Retrieve a single annotation by its ID",
)
async def get_annotation(annotation_id: UUID) -> AnnotationResponse:
    """
    Get a single annotation by ID.

    Args:
        annotation_id: UUID of the annotation

    Returns:
        Annotation details

    Raises:
        HTTPException: If annotation not found
    """
    try:
        logger.info(f"Fetching annotation: {annotation_id}")

        repo = SchemaAnnotationRepository()
        annotation = await repo.get_by_id(annotation_id)

        if not annotation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error="not_found",
                    message=f"Annotation {annotation_id} not found",
                ).model_dump(),
            )

        return AnnotationResponse(
            id=annotation.id,
            provider_id=annotation.provider_id,
            table_name=annotation.table_name,
            column_name=annotation.column_name,
            description=annotation.description,
            business_terms=annotation.business_terms,
            examples=annotation.examples,
            relationships=annotation.relationships,
            date_format=annotation.date_format,
            enum_values=annotation.enum_values,
            sensitive=annotation.sensitive,
            created_by=annotation.created_by,
            created_at=annotation.created_at.isoformat() if annotation.created_at else None,
            updated_at=annotation.updated_at.isoformat() if annotation.updated_at else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching annotation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch annotation",
                details={"error": str(e)} if settings.debug else None,
            ).model_dump(),
        )


@router.put(
    "/{annotation_id}",
    response_model=AnnotationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update annotation",
    description="Update an existing annotation",
)
async def update_annotation(
    annotation_id: UUID,
    update: AnnotationUpdate
) -> AnnotationResponse:
    """
    Update an existing annotation.

    Args:
        annotation_id: UUID of the annotation
        update: Fields to update

    Returns:
        Updated annotation

    Raises:
        HTTPException: If annotation not found or update fails
    """
    try:
        logger.info(f"Updating annotation: {annotation_id}")

        repo = SchemaAnnotationRepository()

        # Build update kwargs from request, excluding unset fields
        update_data = update.model_dump(exclude_unset=True)

        annotation = await repo.update(annotation_id, **update_data)

        if not annotation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error="not_found",
                    message=f"Annotation {annotation_id} not found",
                ).model_dump(),
            )

        return AnnotationResponse(
            id=annotation.id,
            provider_id=annotation.provider_id,
            table_name=annotation.table_name,
            column_name=annotation.column_name,
            description=annotation.description,
            business_terms=annotation.business_terms,
            examples=annotation.examples,
            relationships=annotation.relationships,
            date_format=annotation.date_format,
            enum_values=annotation.enum_values,
            sensitive=annotation.sensitive,
            created_by=annotation.created_by,
            created_at=annotation.created_at.isoformat() if annotation.created_at else None,
            updated_at=annotation.updated_at.isoformat() if annotation.updated_at else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating annotation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="update_error",
                message="Failed to update annotation",
                details={"error": str(e)} if settings.debug else None,
            ).model_dump(),
        )


@router.delete(
    "/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete annotation",
    description="Delete an annotation by ID",
)
async def delete_annotation(annotation_id: UUID) -> None:
    """
    Delete an annotation.

    Args:
        annotation_id: UUID of the annotation

    Raises:
        HTTPException: If annotation not found or delete fails
    """
    try:
        logger.info(f"Deleting annotation: {annotation_id}")

        repo = SchemaAnnotationRepository()
        success = await repo.delete(annotation_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error="not_found",
                    message=f"Annotation {annotation_id} not found",
                ).model_dump(),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting annotation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="delete_error",
                message="Failed to delete annotation",
                details={"error": str(e)} if settings.debug else None,
            ).model_dump(),
        )
