"""LiteLLM client for AWS Bedrock integration

IMPORTANT: This module sets up AWS credentials before importing litellm.
Import order matters - boto3 credentials must be in env vars first.
"""
import os
import boto3

# Default settings - use cross-region inference profiles
DEFAULT_MODEL = "bedrock/us.anthropic.claude-opus-4-5-20251101-v1:0"
DEFAULT_REGION = os.getenv("AWS_REGION", "us-east-1")


def _setup_aws_credentials():
    """Setup AWS credentials from instance role for LiteLLM"""
    try:
        session = boto3.Session(region_name=DEFAULT_REGION)
        creds = session.get_credentials()
        if creds:
            frozen = creds.get_frozen_credentials()
            os.environ['AWS_ACCESS_KEY_ID'] = frozen.access_key
            os.environ['AWS_SECRET_ACCESS_KEY'] = frozen.secret_key
            if frozen.token:
                os.environ['AWS_SESSION_TOKEN'] = frozen.token
            os.environ['AWS_REGION_NAME'] = DEFAULT_REGION
            return True
    except Exception as e:
        print(f"Warning: Could not setup AWS credentials: {e}")
    return False


# Setup credentials BEFORE importing litellm
_setup_aws_credentials()

# Now import litellm (after credentials are in env)
from typing import Optional, List, Dict, Any
import litellm
from litellm import completion, acompletion

litellm.set_verbose = False


def get_completion(
    prompt: str,
    model: str = None,
    system: str = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    **kwargs
) -> str:
    """Synchronous completion using LiteLLM with Bedrock"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    response = completion(
        model=model or DEFAULT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )
    return response.choices[0].message.content


async def get_completion_async(
    prompt: str,
    model: str = None,
    system: str = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    **kwargs
) -> str:
    """Async completion using LiteLLM with Bedrock"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    response = await acompletion(
        model=model or DEFAULT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )
    return response.choices[0].message.content


def get_chat_completion(
    messages: List[Dict[str, str]],
    model: str = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    **kwargs
) -> str:
    """Chat completion with message history"""
    response = completion(
        model=model or DEFAULT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )
    return response.choices[0].message.content


async def get_chat_completion_async(
    messages: List[Dict[str, str]],
    model: str = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    **kwargs
) -> str:
    """Async chat completion with message history"""
    response = await acompletion(
        model=model or DEFAULT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )
    return response.choices[0].message.content


# Model aliases for convenience - use cross-region inference profiles
MODELS = {
    "opus": "bedrock/us.anthropic.claude-opus-4-5-20251101-v1:0",
    "sonnet": "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0", 
    "haiku": "bedrock/us.anthropic.claude-3-haiku-20240307-v1:0",
}


def get_model(alias: str) -> str:
    """Get full model name from alias"""
    return MODELS.get(alias, alias)


# Also export the client class for more advanced usage
from .litellm_client import LiteLLMClient, get_client

__all__ = [
    "LiteLLMClient",
    "get_client",
    "get_completion",
    "get_completion_async",
    "get_chat_completion",
    "get_chat_completion_async",
    "get_model",
    "MODELS",
    "DEFAULT_MODEL",
    "DEFAULT_REGION",
]
