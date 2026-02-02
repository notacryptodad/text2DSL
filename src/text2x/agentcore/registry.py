"""Agent registry for AgentCore runtime."""
from typing import Dict, Type, List
import logging

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Singleton registry for managing agent classes.

    The registry maintains a mapping of agent names to agent classes.
    Agents must be registered before they can be instantiated by the runtime.
    """

    _instance = None
    _agents: Dict[str, Type] = {}

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, name: str, agent_class: Type) -> None:
        """Register an agent class.

        Args:
            name: Unique name for the agent
            agent_class: Agent class (must inherit from AgentCoreBaseAgent)

        Raises:
            ValueError: If agent name already registered
        """
        if name in self._agents:
            logger.warning(f"Agent '{name}' already registered, overwriting")

        self._agents[name] = agent_class
        logger.info(f"Registered agent: {name} -> {agent_class.__name__}")

    def get(self, name: str) -> Type:
        """Get an agent class by name.

        Args:
            name: Agent name

        Returns:
            Agent class

        Raises:
            KeyError: If agent not found
        """
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not found in registry")

        return self._agents[name]

    def list(self) -> List[str]:
        """List all registered agent names.

        Returns:
            List of agent names
        """
        return list(self._agents.keys())

    def clear(self) -> None:
        """Clear all registered agents (mainly for testing)."""
        self._agents.clear()
        logger.info("Agent registry cleared")


# Module-level singleton instance
def get_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    return AgentRegistry()
