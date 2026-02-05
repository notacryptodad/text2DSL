"""LiteLLM client configured for AWS Bedrock.

Uses instance role credentials via boto3 for authentication.
"""

import os
from typing import Any

import boto3
import litellm
from litellm import acompletion, completion


# Configure LiteLLM
litellm.set_verbose = False

# Default model configuration
# Use cross-region inference profile for Claude Opus 4.5
DEFAULT_MODEL = "bedrock/us.anthropic.claude-opus-4-5-20251101-v1:0"
DEFAULT_REGION = os.environ.get("AWS_REGION", "us-east-1")


def _ensure_aws_credentials() -> None:
    """Ensure AWS credentials are available in environment.

    LiteLLM doesn't automatically pick up instance role credentials,
    so we fetch them via boto3 and set environment variables.
    Only called for Bedrock models.
    """
    # Skip if credentials already set (e.g., by explicit env vars)
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return

    session = boto3.Session()
    credentials = session.get_credentials()
    if credentials is None:
        raise RuntimeError("No AWS credentials available")

    creds = credentials.get_frozen_credentials()
    os.environ["AWS_ACCESS_KEY_ID"] = creds.access_key
    os.environ["AWS_SECRET_ACCESS_KEY"] = creds.secret_key
    if creds.token:
        os.environ["AWS_SESSION_TOKEN"] = creds.token


class LiteLLMClient:
    """LiteLLM client wrapper supporting multiple providers."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        region: str = DEFAULT_REGION,
        api_base: str | None = None,
        api_key: str | None = None,
        **kwargs: Any,
    ):
        """Initialize the LiteLLM client.

        Args:
            model: The model identifier (e.g., bedrock/..., nvidia_nim/...)
            region: AWS region for Bedrock (default: us-east-1)
            api_base: API base URL for non-Bedrock providers
            api_key: API key for non-Bedrock providers
            **kwargs: Additional default parameters for completions
        """
        self.model = model
        self.region = region
        self.api_base = api_base
        self.api_key = api_key
        self.default_kwargs = kwargs
        self.is_bedrock = model.startswith("bedrock/")

        # Set API credentials in environment for LiteLLM
        # LiteLLM uses NVIDIA_NIM_API_KEY for nvidia_nim models
        if api_key and "nvidia" in model.lower():
            os.environ["NVIDIA_NIM_API_KEY"] = api_key
        elif api_key:
            os.environ["OPENAI_API_KEY"] = api_key  # Fallback for other providers

        # Only setup AWS credentials for Bedrock models
        if self.is_bedrock:
            os.environ.setdefault("AWS_REGION", region)
            _ensure_aws_credentials()

    def complete(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> Any:
        """Synchronous completion request.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            **kwargs: Override default parameters

        Returns:
            LiteLLM completion response
        """
        # Refresh credentials for Bedrock models
        if self.is_bedrock:
            _ensure_aws_credentials()

        merged_kwargs = {**self.default_kwargs, **kwargs}
        
        # Pass API credentials directly for non-Bedrock providers
        if self.api_key:
            merged_kwargs["api_key"] = self.api_key
        if self.api_base:
            merged_kwargs["api_base"] = self.api_base
            
        return completion(
            model=self.model,
            messages=messages,
            **merged_kwargs,
        )

    async def acomplete(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> Any:
        """Asynchronous completion request.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            **kwargs: Override default parameters

        Returns:
            LiteLLM completion response
        """
        # Refresh credentials for Bedrock models
        if self.is_bedrock:
            _ensure_aws_credentials()

        merged_kwargs = {**self.default_kwargs, **kwargs}
        
        # Pass API credentials directly for non-Bedrock providers
        if self.api_key:
            merged_kwargs["api_key"] = self.api_key
        if self.api_base:
            merged_kwargs["api_base"] = self.api_base
            
        return await acompletion(
            model=self.model,
            messages=messages,
            **merged_kwargs,
        )

    def __repr__(self) -> str:
        return f"LiteLLMClient(model={self.model!r}, region={self.region!r})"


# Module-level singleton instance
_client: LiteLLMClient | None = None


def get_client(
    model: str = DEFAULT_MODEL,
    region: str = DEFAULT_REGION,
    api_base: str | None = None,
    api_key: str | None = None,
    **kwargs: Any,
) -> LiteLLMClient:
    """Get or create a singleton LiteLLM client.

    Args:
        model: The model identifier
        region: AWS region for Bedrock
        api_base: API base URL for non-Bedrock providers
        api_key: API key for non-Bedrock providers
        **kwargs: Additional default parameters

    Returns:
        LiteLLMClient instance
    """
    global _client
    if _client is None:
        _client = LiteLLMClient(
            model=model, region=region, api_base=api_base, api_key=api_key, **kwargs
        )
    return _client
