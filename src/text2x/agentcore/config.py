"""AgentCore configuration."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentCoreConfig:
    """Configuration for AgentCore runtime.

    Attributes:
        model: LLM model identifier (e.g., 'bedrock/us.anthropic.claude-opus-4-5')
        region: AWS region for Bedrock (default: us-east-1)
        temperature: LLM temperature (0.0-1.0)
        max_tokens: Maximum tokens for LLM response
        timeout: Request timeout in seconds
        use_litellm: Whether to use LiteLLM (default: True)
        api_base: API base URL for non-Bedrock providers
        api_key: API key for non-Bedrock providers
    """

    model: str = "bedrock/us.anthropic.claude-opus-4-5-20251101-v1:0"
    region: str = "us-east-1"
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: float = 120.0
    use_litellm: bool = True
    api_base: Optional[str] = None
    api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AgentCoreConfig":
        """Create configuration from environment variables."""
        import os

        return cls(
            model=os.getenv("AGENTCORE_MODEL", os.getenv("LLM_MODEL", cls.model)),
            region=os.getenv("AWS_REGION", cls.region),
            temperature=float(os.getenv("AGENTCORE_TEMPERATURE", str(cls.temperature))),
            max_tokens=int(os.getenv("AGENTCORE_MAX_TOKENS", str(cls.max_tokens))),
            timeout=float(os.getenv("AGENTCORE_TIMEOUT", str(cls.timeout))),
            use_litellm=os.getenv("AGENTCORE_USE_LITELLM", "true").lower() == "true",
            api_base=os.getenv("LLM_API_BASE"),
            api_key=os.getenv("LLM_API_KEY"),
        )
