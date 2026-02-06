"""Strands LiteLLM Model Provider for AgentCore.

Uses Strands SDK's built-in LiteLLMModel for Bedrock integration.
"""

import logging
from typing import Optional

from strands.models.litellm import LiteLLMModel

from text2x.agentcore.config import AgentCoreConfig

logger = logging.getLogger(__name__)


def create_litellm_model(config: Optional[AgentCoreConfig] = None) -> LiteLLMModel:
    """Create a Strands LiteLLM model provider for AgentCore.

    Args:
        config: AgentCore configuration (defaults to from_env)

    Returns:
        LiteLLMModel configured for LLM provider
    """
    if config is None:
        config = AgentCoreConfig.from_env()

    client_args = {
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "api_key": config.api_key,
    }

    if config.api_base:
        client_args["base_url"] = config.api_base

    model = LiteLLMModel(
        model_id=config.model,
        client_args=client_args,
    )

    logger.info(f"Created Strands LiteLLM model provider: {config.model}")
    return model


# Default model factory for convenience
def get_default_model() -> LiteLLMModel:
    """Get the default LiteLLM model for AgentCore.

    Returns:
        LiteLLMModel with default configuration
    """
    return create_litellm_model()
