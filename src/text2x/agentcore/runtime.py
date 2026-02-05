"""AgentCore runtime - manages agent lifecycle with Strands SDK.

Uses Strands SDK for all agent implementations.
"""
import logging
from typing import Dict, Any, Optional

from text2x.agentcore.config import AgentCoreConfig
from text2x.agentcore.llm.strands_provider import create_litellm_model

logger = logging.getLogger(__name__)


class AgentCore:
    """AgentCore runtime for managing Strands SDK agents.

    Responsibilities:
    - Initialize and manage Strands model provider
    - Load Strands agents
    - Provide lifecycle management (start/stop)
    - Serve as dependency injection container for agents
    """

    def __init__(self, config: Optional[AgentCoreConfig] = None):
        """Initialize AgentCore runtime.

        Args:
            config: AgentCore configuration (defaults to from_env)
        """
        self.config = config or AgentCoreConfig.from_env()
        self.strands_model = None
        self.agents: Dict[str, Any] = {}
        self._started = False

        logger.info("AgentCore runtime initialized")

    async def start(self) -> None:
        """Start the runtime.

        - Initializes Strands model provider
        - Loads Strands agents
        """
        if self._started:
            logger.warning("AgentCore already started")
            return

        logger.info("Starting AgentCore runtime...")

        # Initialize Strands model provider
        self.strands_model = create_litellm_model(self.config)
        logger.info("Strands LiteLLM model provider initialized")

        # Load Strands agents
        self._load_strands_agents()

        self._started = True
        logger.info(f"AgentCore runtime started with {len(self.agents)} agents")

    def _load_strands_agents(self) -> None:
        """Load Strands SDK agents."""
        from text2x.agentcore.agents.auto_annotation.strands_agent import AutoAnnotationAgent
        from text2x.agentcore.agents.annotation_assistant.strands_agent import AnnotationAssistantAgent
        from text2x.agentcore.agents.query.strands_agent import QueryAgent

        # Create Strands agents (they only need model, not config)
        self.agents["auto_annotation"] = AutoAnnotationAgent(
            model=self.strands_model,
        )
        self.agents["annotation_assistant"] = AnnotationAssistantAgent(
            model=self.strands_model,
        )
        self.agents["query"] = QueryAgent(
            model=self.strands_model,
        )

        logger.info(f"Loaded {len(self.agents)} Strands agents")

    def get_agent(self, name: str) -> Optional[Any]:
        """Get an agent by name.

        Args:
            name: Agent name

        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(name)

    def list_agents(self) -> list[str]:
        """List all registered agent names.

        Returns:
            List of agent names
        """
        return list(self.agents.keys())

    async def stop(self) -> None:
        """Stop the runtime and cleanup resources."""
        if not self._started:
            logger.warning("AgentCore not started")
            return

        logger.info("Stopping AgentCore runtime...")

        # Cleanup agents
        self.agents.clear()
        self.strands_model = None

        self._started = False
        logger.info("AgentCore runtime stopped")

    def is_started(self) -> bool:
        """Check if runtime is started.

        Returns:
            True if started, False otherwise
        """
        return self._started


def create_agentcore(config: Optional[AgentCoreConfig] = None) -> AgentCore:
    """Create an AgentCore runtime instance.

    Args:
        config: Optional configuration override

    Returns:
        AgentCore runtime instance
    """
    return AgentCore(config=config)
