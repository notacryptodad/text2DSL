"""Base agent class for AgentCore."""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)


class AgentCoreBaseAgent(ABC):
    """Base class for all AgentCore agents.

    Provides:
    - LLM invocation via runtime's LLM client
    - Tool registration and execution
    - Conversation history management
    - Abstract methods for agent-specific logic
    """

    def __init__(self, runtime: "AgentCore", name: str):
        """Initialize base agent.

        Args:
            runtime: AgentCore runtime instance
            name: Agent name
        """
        self.runtime = runtime
        self.name = name
        self.tools: Dict[str, Callable] = {}
        self.conversation_history: List[Dict[str, str]] = []

        logger.info(f"Initialized agent: {name}")

    def register_tool(self, name: str, func: Callable) -> None:
        """Register a tool for this agent.

        Args:
            name: Tool name
            func: Tool function (must be async)
        """
        self.tools[name] = func
        logger.debug(f"Agent '{self.name}' registered tool: {name}")

    async def invoke_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Invoke LLM with exponential backoff retry.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            max_retries: Maximum retry attempts

        Returns:
            LLM response dict

        Raises:
            RuntimeError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                return await self.runtime.llm_client.invoke(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"LLM invocation failed after {max_retries} attempts")
                    raise

                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"LLM invocation attempt {attempt + 1} failed, "
                    f"retrying in {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)

        raise RuntimeError(f"Max retries ({max_retries}) exceeded")

    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history.

        Args:
            role: Message role (system, user, assistant)
            content: Message content
        """
        self.conversation_history.append({
            "role": role,
            "content": content,
        })

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
        logger.debug(f"Agent '{self.name}' cleared conversation history")

    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history.

        Returns:
            List of message dicts
        """
        return self.conversation_history.copy()

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return output.

        Args:
            input_data: Input data dict

        Returns:
            Output data dict

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get system prompt for this agent.

        Returns:
            System prompt string

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        pass
