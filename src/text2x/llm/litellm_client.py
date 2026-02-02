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
    """LiteLLM client wrapper for AWS Bedrock."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        region: str = DEFAULT_REGION,
        **kwargs: Any,
    ):
        """Initialize the LiteLLM client.

        Args:
            model: The Bedrock model identifier (default: Claude Opus 4.5)
            region: AWS region for Bedrock (default: us-east-1)
            **kwargs: Additional default parameters for completions
        """
        self.model = model
        self.region = region
        self.default_kwargs = kwargs

        # Ensure AWS region is set
        os.environ.setdefault("AWS_REGION", region)

        # Ensure credentials are available for LiteLLM
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
        # Refresh credentials before each call (handles token expiration)
        _ensure_aws_credentials()

        merged_kwargs = {**self.default_kwargs, **kwargs}
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
        # Refresh credentials before each call (handles token expiration)
        _ensure_aws_credentials()

        merged_kwargs = {**self.default_kwargs, **kwargs}
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
    **kwargs: Any,
) -> LiteLLMClient:
    """Get or create a singleton LiteLLM client.

    Args:
        model: The Bedrock model identifier
        region: AWS region for Bedrock
        **kwargs: Additional default parameters

    Returns:
        LiteLLMClient instance
    """
    global _client
    if _client is None:
        _client = LiteLLMClient(model=model, region=region, **kwargs)
    return _client
