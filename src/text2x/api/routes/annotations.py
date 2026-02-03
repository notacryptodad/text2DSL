"""Annotation chat endpoints for schema annotation assistance."""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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


# In-memory storage for conversation context (in production, use Redis or similar)
# Maps conversation_id -> dict with context
_conversation_context: Dict[UUID, Dict[str, Any]] = {}


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
                f"conversation_id={conversation_id} (using AgentCore)"
            )

            # Get AgentCore annotation_assistant agent
            agentcore = app_state.agentcore
            if not agentcore or not agentcore.is_started:
                raise RuntimeError("AgentCore not initialized")

            # Get or create annotation_assistant agent
            from text2x.agentcore.agents.annotation_assistant import AnnotationAssistantAgent
            from text2x.providers.factory import get_provider_by_connection_id

            agent_name = f"annotation_assistant_{request.provider_id}"

            # Check if agent already exists
            if agent_name not in agentcore.agents:
                # Create agent instance
                agent = AnnotationAssistantAgent(agentcore, agent_name)

                # Register agent with runtime
                agentcore.agents[agent_name] = agent
                logger.info(f"Created AnnotationAssistantAgent instance: {agent_name}")
            else:
                agent = agentcore.agents[agent_name]

            # Set provider for database access (needed for tools)
            # Try to get workspace_id from existing conversation context
            context = _conversation_context.get(conversation_id, {})
            workspace_id = context.get("workspace_id")
            
            if workspace_id:
                try:
                    provider = await get_provider_by_connection_id(
                        UUID(request.provider_id), 
                        UUID(workspace_id)
                    )
                    agent.set_provider(provider)
                except Exception as e:
                    logger.warning(f"Failed to set provider: {e}")

            # Get or initialize conversation context
            if conversation_id not in _conversation_context:
                _conversation_context[conversation_id] = {
                    "conversation_history": [],
                    "provider_id": request.provider_id
                }

            context = _conversation_context[conversation_id]

            # Reset conversation if requested
            if request.reset_conversation:
                context["conversation_history"] = []
                logger.info(f"Reset conversation {conversation_id}")

            # Add user message to history
            context["conversation_history"].append({
                "role": "user",
                "content": request.user_message
            })

            # Process user message through AgentCore agent
            agent_result = await agent.process({
                "message": request.user_message,
                "provider_id": request.provider_id,
                "user_id": request.user_id,
                "conversation_history": context["conversation_history"],
            })

            # Extract response and add to history
            assistant_response = agent_result.get("response", "")
            context["conversation_history"].append({
                "role": "assistant",
                "content": assistant_response
            })

            # Build response
            response = AnnotationChatResponse(
                conversation_id=conversation_id,
                response=assistant_response,
                tool_calls=[ToolCall(**tc) for tc in agent_result.get("tool_calls", [])],
                conversation_history=[
                    ConversationMessage(**msg)
                    for msg in context["conversation_history"]
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

        if conversation_id in _conversation_context:
            del _conversation_context[conversation_id]
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
        if conversation_id not in _conversation_context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error="not_found",
                    message="Conversation not found",
                ).model_dump(),
            )

        context = _conversation_context[conversation_id]
        history = context.get("conversation_history", [])

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


class AnnotationRequest(BaseModel):
    """Request model for saving a table annotation."""

    table_name: str = Field(..., description="Table name")
    description: Optional[str] = Field(None, description="Table description")
    business_terms: Optional[List[str]] = Field(None, description="Business terms")
    relationships: Optional[List[Any]] = Field(None, description="Relationships")
    columns: Optional[List[Dict[str, Any]]] = Field(None, description="Column annotations")

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


@router.get(
    "/workspaces/{workspace_id}/connections/{connection_id}/schema/annotations",
    status_code=status.HTTP_200_OK,
    summary="Get all annotations for a connection",
)
async def get_annotations(
    workspace_id: UUID,
    connection_id: UUID,
):
    """Get all saved annotations for a connection."""
    repo = SchemaAnnotationRepository()
    annotations = await repo.list_by_provider(str(connection_id))
    
    # Group by table, nest column annotations
    result = {}
    for ann in annotations:
        if ann.table_name and not ann.column_name:
            # Table-level annotation
            result[ann.table_name] = ann.to_dict()
            result[ann.table_name]['columns'] = []
    
    # Add column annotations to their tables
    for ann in annotations:
        if ann.column_name and '.' in ann.column_name:
            table_name = ann.column_name.split('.')[0]
            col_name = ann.column_name.split('.')[1]
            if table_name in result:
                result[table_name]['columns'].append({
                    'name': col_name,
                    'description': ann.description,
                    'sample_values': ann.examples[0] if ann.examples else ''
                })
    
    return result


@router.post(
    "/workspaces/{workspace_id}/connections/{connection_id}/schema/annotations",
    status_code=status.HTTP_200_OK,
    summary="Save annotation for a table",
)
async def save_annotation(
    workspace_id: UUID,
    connection_id: UUID,
    request: AnnotationRequest,
):
    """Save or update annotation for a table."""
    repo = SchemaAnnotationRepository()
    
    # Check if table annotation exists
    existing = await repo.list_by_provider(str(connection_id))
    existing_ann = next((a for a in existing if a.table_name == request.table_name and not a.column_name), None)
    
    if existing_ann:
        # Update existing table annotation
        updated = await repo.update(
            annotation_id=existing_ann.id,
            description=request.description,
            business_terms=request.business_terms,
            relationships=[str(r) for r in request.relationships] if request.relationships else None,
        )
        result = updated.to_dict()
    else:
        # Create new table annotation
        annotation = await repo.create(
            provider_id=str(connection_id),
            table_name=request.table_name,
            description=request.description or "",
            created_by="system",
            business_terms=request.business_terms,
            relationships=[str(r) for r in request.relationships] if request.relationships else None,
        )
        result = annotation.to_dict()
    
    # Save column annotations
    if request.columns:
        for col in request.columns:
            col_name = f"{request.table_name}.{col.get('name')}"
            existing_col = next((a for a in existing if a.column_name == col_name), None)
            
            if existing_col:
                await repo.update(
                    annotation_id=existing_col.id,
                    description=col.get('description', ''),
                    examples=[col.get('sample_values')] if col.get('sample_values') else None,
                )
            elif col.get('description'):
                await repo.create(
                    provider_id=str(connection_id),
                    column_name=col_name,
                    description=col.get('description', ''),
                    created_by="system",
                    examples=[col.get('sample_values')] if col.get('sample_values') else None,
                )
    
    result['columns'] = request.columns or []
    return result


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

        # Get AgentCore annotation_assistant agent
        agentcore = app_state.agentcore
        if not agentcore or not agentcore.is_started:
            raise RuntimeError("AgentCore not initialized")

        # Get the connection and create a provider for database access
        from text2x.providers.factory import get_provider_by_connection_id
        provider = await get_provider_by_connection_id(connection_id, workspace_id)

        # Get or create annotation_assistant agent
        from text2x.agentcore.agents.annotation_assistant import AnnotationAssistantAgent

        agent_name = f"annotation_assistant_{connection_id}"

        # Check if agent already exists
        if agent_name not in agentcore.agents:
            # Create agent instance with provider
            agent = AnnotationAssistantAgent(agentcore, agent_name, provider=provider)

            # Register agent with runtime
            agentcore.agents[agent_name] = agent
            logger.info(f"Created AnnotationAssistantAgent instance: {agent_name}")
        else:
            agent = agentcore.agents[agent_name]
            # Update provider in case connection changed
            agent.set_provider(provider)

        # Build rich context for the LLM
        from text2x.api.routes.annotation_context import (
            build_annotation_context, 
            format_context_as_prompt
        )
        
        context = await build_annotation_context(
            provider=provider,
            table_name=request.table_name,
            connection_id=str(connection_id),
            annotation_repo=agent.annotation_repo
        )
        context_prompt = format_context_as_prompt(context)

        # Build prompt with rich context (no tool instructions for auto-annotate)
        prompt = f"""You are an expert database annotator. Analyze this table and generate annotations.

{context_prompt}

## Your Task
Generate annotations for ALL columns in this table based on the information above.

## Response Format
Return ONLY valid JSON (no markdown code blocks, no explanation text):

{{
  "table_description": "Clear description of what this table represents and its purpose",
  "columns": [
    {{
      "name": "column_name",
      "description": "Clear description of what this column stores",
      "sensitive": false,
      "business_terms": ["alternative", "names", "users might search"]
    }}
  ]
}}

## Guidelines
1. Include ALL columns from the schema above
2. Mark sensitive=true for: passwords, emails, PII, tokens, secrets
3. Add business_terms for columns with common alternative names
4. For FK columns, mention the relationship (e.g., "References users table")
5. Be specific - use the sample data to understand actual content

JSON OUTPUT:"""

        # Process the request
        result = await agent.process({
            "message": prompt,
            "provider_id": str(connection_id),
            "user_id": "system",
            "conversation_history": [],
        })

        # Extract suggestions from response
        # Parse JSON from the LLM response

        llm_response = result["response"]
        suggestions = {
            "table_name": request.table_name,
            "table_description": "",
            "columns": [],
        }

        # Try to extract JSON from code blocks first
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(1))
                if "table_description" in parsed_json or "columns" in parsed_json:
                    suggestions["table_description"] = parsed_json.get("table_description", "")
                    suggestions["columns"] = parsed_json.get("columns", [])
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from code block")
        
        # If no table_description found, try to find JSON without code blocks
        if not suggestions["table_description"] and not suggestions["columns"]:
            try:
                # Find JSON that contains table_description or columns (our target structure)
                # Use a more robust approach - find balanced braces
                def find_json_objects(text):
                    """Find all balanced JSON objects in text."""
                    objects = []
                    i = 0
                    while i < len(text):
                        if text[i] == '{':
                            depth = 1
                            start = i
                            i += 1
                            while i < len(text) and depth > 0:
                                if text[i] == '{':
                                    depth += 1
                                elif text[i] == '}':
                                    depth -= 1
                                i += 1
                            if depth == 0:
                                objects.append(text[start:i])
                        else:
                            i += 1
                    return objects
                
                json_objects = find_json_objects(llm_response)
                
                # Find the JSON with table_description (not tool calls)
                for json_str in json_objects:
                    try:
                        parsed_json = json.loads(json_str)
                        if "table_description" in parsed_json and "columns" in parsed_json:
                            suggestions["table_description"] = parsed_json.get("table_description", "")
                            suggestions["columns"] = parsed_json.get("columns", [])
                            logger.info(f"Extracted annotations: {len(suggestions['columns'])} columns")
                            break
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                logger.warning(f"Failed to extract JSON from response: {e}")

        # Populate sample_values from context data
        sample_data = context.get("sample_data", {})
        logger.info(f"Sample data for {request.table_name}: columns={sample_data.get('columns')}, rows_count={len(sample_data.get('rows', []))}")
        if sample_data.get("columns") and sample_data.get("rows"):
            col_names = sample_data["columns"]
            rows = sample_data["rows"]
            
            # Build column -> sample values mapping
            col_samples = {}
            for col_name in col_names:
                values = set()
                for row in rows[:5]:  # Use up to 5 rows
                    # row can be a dict or tuple
                    if isinstance(row, dict):
                        val = row.get(col_name)
                    else:
                        col_idx = col_names.index(col_name)
                        val = row[col_idx] if col_idx < len(row) else None
                    
                    if val is not None:
                        val_str = str(val)
                        if len(val_str) <= 50:  # Skip very long values
                            values.add(val_str[:30])  # Truncate individual values
                
                if values:
                    col_samples[col_name] = ", ".join(list(values)[:3])  # Top 3 unique values
            
            logger.info(f"Sample values mapping: {col_samples}")
            
            # Add sample_values to each column annotation
            for col in suggestions.get("columns", []):
                col_name = col.get("name", "")
                if col_name in col_samples:
                    col["sample_values"] = col_samples[col_name]
        else:
            logger.warning(f"No sample data available for {request.table_name}")

        # Include full response for debugging
        suggestions["llm_response"] = llm_response
        suggestions["tool_calls"] = result.get("tool_calls", [])

        # Store conversation context so chat endpoint can continue it
        _conversation_context[conversation_id] = {
            "conversation_history": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": llm_response}
            ],
            "provider_id": str(connection_id),
            "workspace_id": str(workspace_id),  # Needed for chat to get provider
            "table_name": request.table_name,
            "suggestions": suggestions,  # Store initial suggestions for reference
        }

        response = AutoAnnotateResponse(
            conversation_id=conversation_id,
            table_name=request.table_name,
            suggestions=suggestions,
            message=(
                f"Auto-annotation completed for table '{request.table_name}'. "
                f"You can continue chatting to refine the annotations, then ask me to save them."
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
