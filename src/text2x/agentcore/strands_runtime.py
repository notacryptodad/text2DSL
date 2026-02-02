"""AgentCore runtime - manages agent lifecycle and LLM client.

Updated to support both legacy agents and new Strands SDK agents.
"""
import logging
from typing import Dict, Any, Optional, Union

from text2x.agentcore.config import AgentCoreConfig
from text2x.agentcore.llm.client import LLMClient
from text2x.agentcore.llm.strands_provider import create_litellm_model
from text2x.agentcore.registry import get_registry
from text2x.agentcore.agents.base import AgentCoreBaseAgent

logger = logging.getLogger(__name__)


class AgentCore:
    """AgentCore runtime for managing agents and LLM client.

    Responsibilities:
    - Initialize and manage LLM client (legacy) and Strands model provider (new)
    - Load agents from registry (supports both legacy and Strands agents)
    - Provide lifecycle management (start/stop)
    - Serve as dependency injection container for agents
    """

    def __init__(self, config: Optional[AgentCoreConfig] = None, use_strands: bool = True):
        """Initialize AgentCore runtime.

        Args:
            config: AgentCore configuration (defaults to from_env)
            use_strands: If True, use Strands SDK agents; if False, use legacy agents
        """
        self.config = config or AgentCoreConfig.from_env()
        self.use_strands = use_strands
        self.llm_client: Optional[LLMClient] = None
        self.strands_model = None
        self.agents: Dict[str, Union[AgentCoreBaseAgent, Any]] = {}
        self._started = False

        logger.info(f"AgentCore runtime initialized (use_strands={use_strands})")

    async def start(self) -> None:
        """Start the runtime.

        - Initializes LLM client (legacy) or Strands model provider (new)
        - Loads registered agents
        """
        if self._started:
            logger.warning("AgentCore already started")
            return

        logger.info("Starting AgentCore runtime...")

        if self.use_strands:
            # Initialize Strands model provider
            self.strands_model = create_litellm_model(self.config)
            logger.info("Strands LiteLLM model provider initialized")

            # Load Strands agents
            self._load_strands_agents()
        else:
            # Initialize legacy LLM client
            self.llm_client = LLMClient(self.config)
            logger.info("Legacy LLM client initialized")

            # Load legacy agents from registry
            self._load_legacy_agents()

        self._started = True
        logger.info(f"AgentCore runtime started with {len(self.agents)} agents")

    def _load_strands_agents(self) -> None:
        """Load Strands SDK agents."""
        from text2x.agentcore.agents.auto_annotation.strands_agent import AutoAnnotationAgent
        from text2x.agentcore.agents.annotation_assistant.strands_agent import AnnotationAssistantAgent
        from text2x.agentcore.agents.query.strands_agent import QueryAgent

        # Create Strands agents
        self.agents["auto_annotation"] = AutoAnnotationAgent(
            model=self.strands_model,
            name="auto_annotation",
        )
        self.agents["annotation_assistant"] = AnnotationAssistantAgent(
            model=self.strands_model,
            name="annotation_assistant",
        )
        self.agents["query"] = QueryAgent(
            model=self.strands_model,
            name="query",
        )

        logger.info(f"Loaded {len(self.agents)} Strands agents")

    def _load_legacy_agents(self) -> None:
        """Load legacy agents from registry."""
        registry = get_registry()
        agent_names = registry.list()

        for agent_name in agent_names:
            try:
                agent_class = registry.get(agent_name)
                agent_instance = agent_class(runtime=self, name=agent_name)
                self.agents[agent_name] = agent_instance
                logger.info(f"Loaded legacy agent: {agent_name}")
            except Exception as e:
                logger.error(f"Failed to load agent '{agent_name}': {e}", exc_info=True)

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

        # Clear model/client
        self.strands_model = None
        self.llm_client = None

        self._started = False
        logger.info("AgentCore runtime stopped")

    def get_agent(self, name: str) -> Union[AgentCoreBaseAgent, Any]:
        """Get an agent by name.

        Args:
            name: Agent name

        Returns:
            Agent instance (legacy or Strands)

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


# Factory function for convenience
def create_agentcore(use_strands: bool = True, config: Optional[AgentCoreConfig] = None) -> AgentCore:
    """Create an AgentCore runtime instance.

    Args:
        use_strands: If True, use Strands SDK agents; if False, use legacy agents
        config: Optional configuration override

    Returns:
        AgentCore runtime instance
    """
    return AgentCore(config=config, use_strands=use_strands)
