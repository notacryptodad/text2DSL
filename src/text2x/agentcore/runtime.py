"""AgentCore runtime - manages agent lifecycle and LLM client."""
import logging
from typing import Dict, Any, Optional

from text2x.agentcore.config import AgentCoreConfig
from text2x.agentcore.llm.client import LLMClient
from text2x.agentcore.registry import get_registry
from text2x.agentcore.agents.base import AgentCoreBaseAgent

logger = logging.getLogger(__name__)


class AgentCore:
    """AgentCore runtime for managing agents and LLM client.

    Responsibilities:
    - Initialize and manage LLM client
    - Load agents from registry
    - Provide lifecycle management (start/stop)
    - Serve as dependency injection container for agents
    """

    def __init__(self, config: Optional[AgentCoreConfig] = None):
        """Initialize AgentCore runtime.

        Args:
            config: AgentCore configuration (defaults to from_env)
        """
        self.config = config or AgentCoreConfig.from_env()
        self.llm_client: Optional[LLMClient] = None
        self.agents: Dict[str, AgentCoreBaseAgent] = {}
        self._started = False

        logger.info("AgentCore runtime initialized")

    async def start(self) -> None:
        """Start the runtime.

        - Initializes LLM client
        - Loads registered agents
        """
        if self._started:
            logger.warning("AgentCore already started")
            return

        logger.info("Starting AgentCore runtime...")

        # Initialize LLM client
        self.llm_client = LLMClient(self.config)
        logger.info("LLM client initialized")

        # Load agents from registry
        registry = get_registry()
        agent_names = registry.list()

        for agent_name in agent_names:
            try:
                agent_class = registry.get(agent_name)
                agent_instance = agent_class(runtime=self, name=agent_name)
                self.agents[agent_name] = agent_instance
                logger.info(f"Loaded agent: {agent_name}")
            except Exception as e:
                logger.error(f"Failed to load agent '{agent_name}': {e}", exc_info=True)

        self._started = True
        logger.info(f"AgentCore runtime started with {len(self.agents)} agents")

    async def stop(self) -> None:
        """Stop the runtime.

        - Cleans up agents
        - Closes LLM client resources
        """
        if not self._started:
            logger.warning("AgentCore not started")
            return

        logger.info("Stopping AgentCore runtime...")

        # Clear agents
        self.agents.clear()

        # No explicit cleanup needed for LiteLLM client
        self.llm_client = None

        self._started = False
        logger.info("AgentCore runtime stopped")

    def get_agent(self, name: str) -> AgentCoreBaseAgent:
        """Get an agent by name.

        Args:
            name: Agent name

        Returns:
            Agent instance

        Raises:
            RuntimeError: If runtime not started
            KeyError: If agent not found
        """
        if not self._started:
            raise RuntimeError("AgentCore runtime not started")

        if name not in self.agents:
            raise KeyError(f"Agent '{name}' not found. Available: {list(self.agents.keys())}")

        return self.agents[name]

    def list_agents(self) -> list[str]:
        """List all loaded agent names.

        Returns:
            List of agent names
        """
        return list(self.agents.keys())

    @property
    def is_started(self) -> bool:
        """Check if runtime is started.

        Returns:
            True if started, False otherwise
        """
        return self._started
