"""Thin wrapper around LiteLLMClient for AgentCore."""
from typing import List, Dict, Any, Optional
import logging

from text2x.llm.litellm_client import LiteLLMClient
from text2x.agentcore.config import AgentCoreConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """Async LLM client wrapper for AgentCore.

    Provides a thin wrapper around LiteLLMClient with:
    - Async invoke() method
    - Simplified message format
    - Error handling and retries
    """

    def __init__(self, config: AgentCoreConfig):
        """Initialize LLM client.

        Args:
            config: AgentCore configuration
        """
        self.config = config
        self.litellm_client = LiteLLMClient(
            model=config.model,
            region=config.region,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        logger.info(f"Initialized LLM client with model: {config.model}")

    async def invoke(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Invoke LLM with messages.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Returns:
            Dict with 'content', 'tokens_used', 'model', 'finish_reason'

        Raises:
            RuntimeError: If LLM invocation fails
        """
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        try:
            response = await self.litellm_client.acomplete(
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
            )

            choice = response.choices[0]
            return {
                "content": choice.message.content,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "model": response.model or self.litellm_client.model,
                "finish_reason": choice.finish_reason or "stop",
            }
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}", exc_info=True)
            raise RuntimeError(f"LLM invocation failed: {str(e)}") from e

    def __repr__(self) -> str:
        return f"LLMClient(model={self.config.model!r})"
