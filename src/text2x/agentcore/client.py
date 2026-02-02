"""AgentCore client wrapper for easy switching between local and remote modes.

Usage:
    # Local mode (in-process, default)
    client = AgentCoreClient(mode="local")
    
    # Remote mode (HTTP calls to AgentCore service)
    client = AgentCoreClient(mode="remote", base_url="https://agentcore.example.com")
    
    # Invoke an agent
    result = await client.invoke("query", {"user_message": "Show me all users"})
"""
import logging
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AgentCoreMode(str, Enum):
    """AgentCore client mode."""
    LOCAL = "local"
    REMOTE = "remote"


class AgentInfo(BaseModel):
    """Agent information."""
    name: str
    status: str


class AgentCoreClient:
    """Unified client for AgentCore - supports both local and remote modes.
    
    In local mode, directly calls the in-process AgentCore runtime.
    In remote mode, makes HTTP calls to a separate AgentCore service.
    
    This abstraction allows easy switching between deployment modes
    without changing application code.
    """
    
    def __init__(
        self,
        mode: AgentCoreMode | str = AgentCoreMode.LOCAL,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        api_key: Optional[str] = None,
    ):
        """Initialize the AgentCore client.
        
        Args:
            mode: "local" for in-process, "remote" for HTTP calls
            base_url: Base URL for remote mode (e.g., "https://agentcore.example.com/api/v1/agentcore")
            timeout: Request timeout in seconds (for remote mode)
            api_key: API key for authentication (for remote mode)
        """
        self.mode = AgentCoreMode(mode) if isinstance(mode, str) else mode
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout = timeout
        self.api_key = api_key
        self._http_client: Optional[httpx.AsyncClient] = None
        self._local_runtime = None
        
        if self.mode == AgentCoreMode.REMOTE and not self.base_url:
            raise ValueError("base_url is required for remote mode")
        
        logger.info(f"AgentCoreClient initialized in {self.mode.value} mode")
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for remote mode."""
        if self._http_client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._http_client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=headers,
            )
        return self._http_client
    
    def _get_local_runtime(self):
        """Get the local AgentCore runtime from app state."""
        if self._local_runtime is None:
            from text2x.api.state import app_state
            if not app_state.agentcore:
                raise RuntimeError("AgentCore runtime not initialized")
            self._local_runtime = app_state.agentcore
        return self._local_runtime
    
    async def list_agents(self) -> List[AgentInfo]:
        """List all available agents.
        
        Returns:
            List of AgentInfo with name and status
        """
        if self.mode == AgentCoreMode.LOCAL:
            runtime = self._get_local_runtime()
            return [
                AgentInfo(name=name, status="active")
                for name in runtime.list_agents()
            ]
        else:
            client = await self._get_http_client()
            response = await client.get(f"{self.base_url}/")
            response.raise_for_status()
            data = response.json()
            return [AgentInfo(**agent) for agent in data.get("agents", [])]
    
    async def invoke(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Invoke an agent with input data.
        
        Args:
            agent_name: Name of the agent to invoke
            input_data: Input data for the agent
            
        Returns:
            Agent output data
        """
        if self.mode == AgentCoreMode.LOCAL:
            return await self._invoke_local(agent_name, input_data)
        else:
            return await self._invoke_remote(agent_name, input_data)
    
    async def _invoke_local(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Invoke agent locally (in-process)."""
        runtime = self._get_local_runtime()
        agent = runtime.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found")
        
        logger.debug(f"Invoking agent '{agent_name}' locally")
        result = await agent.process(input_data)
        return result
    
    async def _invoke_remote(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Invoke agent remotely via HTTP."""
        client = await self._get_http_client()
        url = f"{self.base_url}/{agent_name}/invoke"
        
        logger.debug(f"Invoking agent '{agent_name}' remotely at {url}")
        response = await client.post(url, json={"input_data": input_data})
        response.raise_for_status()
        
        data = response.json()
        return data.get("output_data", data)
    
    async def chat(
        self,
        agent_name: str,
        message: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a chat message to an agent.
        
        Args:
            agent_name: Name of the agent
            message: User message
            conversation_id: Optional conversation ID for multi-turn
            context: Optional additional context
            
        Returns:
            Agent response with conversation_id
        """
        input_data = {
            "message": message,
            "user_message": message,  # Some agents expect this
        }
        if conversation_id:
            input_data["conversation_id"] = conversation_id
        if context:
            input_data["context"] = context
        
        if self.mode == AgentCoreMode.LOCAL:
            return await self._invoke_local(agent_name, input_data)
        else:
            # Use chat endpoint if available, fallback to invoke
            client = await self._get_http_client()
            url = f"{self.base_url}/{agent_name}/chat"
            
            try:
                response = await client.post(url, json={
                    "message": message,
                    "conversation_id": conversation_id,
                    "context": context,
                })
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Fallback to invoke
                    return await self._invoke_remote(agent_name, input_data)
                raise
    
    async def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """Get status of a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent status information
        """
        if self.mode == AgentCoreMode.LOCAL:
            runtime = self._get_local_runtime()
            agent = runtime.get_agent(agent_name)
            if not agent:
                raise ValueError(f"Agent '{agent_name}' not found")
            return {
                "name": agent_name,
                "status": "active",
                "mode": "local",
            }
        else:
            client = await self._get_http_client()
            response = await client.get(f"{self.base_url}/{agent_name}/status")
            response.raise_for_status()
            return response.json()
    
    async def close(self):
        """Close the client and release resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        logger.info("AgentCoreClient closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Factory function for easy creation from config
def create_agentcore_client(
    mode: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> AgentCoreClient:
    """Create an AgentCore client from environment/config.
    
    Environment variables:
        AGENTCORE_MODE: "local" or "remote" (default: "local")
        AGENTCORE_URL: Base URL for remote mode
        AGENTCORE_API_KEY: API key for authentication
        
    Args:
        mode: Override mode (or use AGENTCORE_MODE env var)
        base_url: Override base URL (or use AGENTCORE_URL env var)
        api_key: Override API key (or use AGENTCORE_API_KEY env var)
        
    Returns:
        Configured AgentCoreClient
    """
    import os
    
    final_mode = mode or os.environ.get("AGENTCORE_MODE", "local")
    final_url = base_url or os.environ.get("AGENTCORE_URL")
    final_key = api_key or os.environ.get("AGENTCORE_API_KEY")
    
    return AgentCoreClient(
        mode=final_mode,
        base_url=final_url,
        api_key=final_key,
    )


# Singleton instance for convenience
_default_client: Optional[AgentCoreClient] = None


def get_agentcore_client() -> AgentCoreClient:
    """Get the default AgentCore client singleton.
    
    Creates client on first call using environment configuration.
    
    Returns:
        Default AgentCoreClient instance
    """
    global _default_client
    if _default_client is None:
        _default_client = create_agentcore_client()
    return _default_client


async def reset_agentcore_client():
    """Reset the default client (for testing or reconfiguration)."""
    global _default_client
    if _default_client:
        await _default_client.close()
        _default_client = None
