"""FastAPI router for AgentCore."""
import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from text2x.agentcore.runtime import AgentCore

logger = logging.getLogger(__name__)

# Global runtime instance (will be initialized by main app)
_runtime: Optional[AgentCore] = None

router = APIRouter(
    prefix="/agentcore",
    tags=["agentcore"],
)


def set_runtime(runtime: AgentCore) -> None:
    """Set the global AgentCore runtime instance.

    Args:
        runtime: AgentCore runtime instance
    """
    global _runtime
    _runtime = runtime
    logger.info("AgentCore runtime set for API router")


def get_runtime() -> AgentCore:
    """Get the global AgentCore runtime instance.

    Returns:
        AgentCore runtime instance

    Raises:
        HTTPException: If runtime not initialized
    """
    if _runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AgentCore runtime not initialized",
        )
    return _runtime


# Request/Response models
class AgentInvokeRequest(BaseModel):
    """Request to invoke an agent."""

    input_data: Dict[str, Any] = Field(
        ...,
        description="Input data for the agent",
    )


class AgentInvokeResponse(BaseModel):
    """Response from agent invocation."""

    agent_name: str = Field(..., description="Name of the agent")
    output_data: Dict[str, Any] = Field(..., description="Output data from the agent")


class AgentInfo(BaseModel):
    """Information about an agent."""

    name: str = Field(..., description="Agent name")
    status: str = Field(..., description="Agent status (active, inactive)")


class AgentListResponse(BaseModel):
    """List of available agents."""

    agents: List[AgentInfo] = Field(..., description="List of agents")


class AgentStatusResponse(BaseModel):
    """Agent status information."""

    agent_name: str = Field(..., description="Agent name")
    status: str = Field(..., description="Agent status")
    conversation_history_length: int = Field(
        ...,
        description="Number of messages in conversation history",
    )


class ChatRequest(BaseModel):
    """Request for chat endpoint."""

    message: str = Field(..., description="User's message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for multi-turn")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context (e.g., selected_table)")


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    response: str = Field(..., description="Agent's response")
    conversation_id: str = Field(..., description="Conversation ID")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls made (if any)")


# Endpoints
@router.get("/", response_model=AgentListResponse)
async def list_agents() -> AgentListResponse:
    """List all available agents.

    Returns:
        List of agent names and their status
    """
    runtime = get_runtime()

    agent_names = runtime.list_agents()
    agents = [
        AgentInfo(
            name=name,
            status="active" if runtime.is_started else "inactive",
        )
        for name in agent_names
    ]

    return AgentListResponse(agents=agents)


@router.post("/{agent_name}/invoke", response_model=AgentInvokeResponse)
async def invoke_agent(
    agent_name: str,
    request: AgentInvokeRequest,
) -> AgentInvokeResponse:
    """Invoke an agent with input data.

    Args:
        agent_name: Name of the agent to invoke
        request: Request containing input data

    Returns:
        Agent output data

    Raises:
        HTTPException: If agent not found or invocation fails
    """
    runtime = get_runtime()

    try:
        agent = runtime.get_agent(agent_name)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_name}' not found",
        ) from e

    try:
        output_data = await agent.process(request.input_data)
        return AgentInvokeResponse(
            agent_name=agent_name,
            output_data=output_data,
        )
    except Exception as e:
        logger.error(f"Agent invocation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent invocation failed: {str(e)}",
        ) from e


@router.get("/{agent_name}/status", response_model=AgentStatusResponse)
async def get_agent_status(agent_name: str) -> AgentStatusResponse:
    """Get agent status.

    Args:
        agent_name: Name of the agent

    Returns:
        Agent status information

    Raises:
        HTTPException: If agent not found
    """
    runtime = get_runtime()

    try:
        agent = runtime.get_agent(agent_name)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_name}' not found",
        ) from e

    return AgentStatusResponse(
        agent_name=agent_name,
        status="active" if runtime.is_started else "inactive",
        conversation_history_length=len(agent.get_history()),
    )


@router.post("/{agent_name}/chat", response_model=ChatResponse)
async def chat_with_agent(
    agent_name: str,
    request: ChatRequest,
) -> ChatResponse:
    """Chat with an agent (multi-turn conversation support).

    Args:
        agent_name: Name of the agent to chat with
        request: Chat request containing message and optional conversation_id

    Returns:
        Agent response with conversation_id and optional tool_calls

    Raises:
        HTTPException: If agent not found or chat fails
    """
    runtime = get_runtime()

    try:
        agent = runtime.get_agent(agent_name)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_name}' not found",
        ) from e

    try:
        # Build input data for agent
        context = request.context or {}
        input_data = {
            "message": request.message,
            "conversation_id": request.conversation_id,
            "context": context,
            # Extract provider_id and user_id from context if present
            "provider_id": context.get("provider_id", ""),
            "user_id": context.get("user_id", "system"),
        }

        # Process message
        output_data = await agent.process(input_data)

        return ChatResponse(
            response=output_data.get("response", ""),
            conversation_id=output_data.get("conversation_id", ""),
            tool_calls=output_data.get("tool_calls"),
        )
    except Exception as e:
        logger.error(f"Chat with agent failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat with agent failed: {str(e)}",
        ) from e
