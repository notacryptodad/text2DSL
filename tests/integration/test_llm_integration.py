"""Integration tests for LiteLLM with AWS Bedrock."""
import pytest
import os
from unittest.mock import patch, Mock

from text2x.llm import (
    get_completion,
    get_completion_async,
    get_chat_completion,
    get_chat_completion_async,
    get_client,
    LiteLLMClient,
    DEFAULT_MODEL,
    MODELS,
)


class TestLiteLLMBasicFunctions:
    """Test basic LiteLLM functions."""

    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"),
        reason="AWS credentials not available"
    )
    def test_get_completion_sync(self):
        """Test synchronous completion."""
        prompt = "What is 2+2? Answer with just the number."
        response = get_completion(prompt, model=MODELS["haiku"], max_tokens=10)

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        # Should contain "4" in some form
        assert "4" in response

    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"),
        reason="AWS credentials not available"
    )
    @pytest.mark.asyncio
    async def test_get_completion_async(self):
        """Test asynchronous completion."""
        prompt = "What is the capital of France? Answer with just the city name."
        response = await get_completion_async(prompt, model=MODELS["haiku"], max_tokens=20)

        assert response is not None
        assert isinstance(response, str)
        assert "Paris" in response

    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"),
        reason="AWS credentials not available"
    )
    def test_get_completion_with_system_prompt(self):
        """Test completion with system prompt."""
        system = "You are a helpful SQL expert. Be concise."
        prompt = "What does SELECT * FROM users do?"

        response = get_completion(
            prompt,
            system=system,
            model=MODELS["haiku"],
            max_tokens=100
        )

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        # Should mention selecting or retrieving data
        assert any(word in response.lower() for word in ["select", "retrieve", "return", "all"])

    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"),
        reason="AWS credentials not available"
    )
    def test_get_chat_completion(self):
        """Test chat completion with message history."""
        messages = [
            {"role": "user", "content": "My name is Alice."},
            {"role": "assistant", "content": "Hello Alice! How can I help you?"},
            {"role": "user", "content": "What is my name?"}
        ]

        response = get_chat_completion(messages, model=MODELS["haiku"], max_tokens=50)

        assert response is not None
        assert isinstance(response, str)
        assert "Alice" in response

    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"),
        reason="AWS credentials not available"
    )
    @pytest.mark.asyncio
    async def test_get_chat_completion_async(self):
        """Test async chat completion with message history."""
        messages = [
            {"role": "user", "content": "Count to 3."},
        ]

        response = await get_chat_completion_async(messages, model=MODELS["haiku"], max_tokens=30)

        assert response is not None
        assert isinstance(response, str)
        # Should contain numbers 1, 2, 3
        assert any(num in response for num in ["1", "2", "3"])


class TestLiteLLMClient:
    """Test LiteLLMClient class."""

    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"),
        reason="AWS credentials not available"
    )
    def test_client_initialization(self):
        """Test client initialization."""
        client = LiteLLMClient(model=MODELS["haiku"])

        assert client is not None
        assert client.model == MODELS["haiku"]
        assert client.region == "us-east-1"

    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"),
        reason="AWS credentials not available"
    )
    def test_client_complete(self):
        """Test synchronous completion via client."""
        client = LiteLLMClient(model=MODELS["haiku"])

        messages = [{"role": "user", "content": "Say 'hello' in French."}]
        response = client.complete(messages, max_tokens=20)

        assert response is not None
        assert response.choices is not None
        assert len(response.choices) > 0
        assert response.choices[0].message.content is not None
        assert "bonjour" in response.choices[0].message.content.lower()

    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"),
        reason="AWS credentials not available"
    )
    @pytest.mark.asyncio
    async def test_client_acomplete(self):
        """Test asynchronous completion via client."""
        client = LiteLLMClient(model=MODELS["haiku"])

        messages = [{"role": "user", "content": "What is 10 + 5? Just the number."}]
        response = await client.acomplete(messages, max_tokens=10)

        assert response is not None
        assert response.choices is not None
        assert len(response.choices) > 0
        assert "15" in response.choices[0].message.content

    def test_get_client_singleton(self):
        """Test singleton client creation."""
        client1 = get_client()
        client2 = get_client()

        assert client1 is client2


class TestLiteLLMForQueryGeneration:
    """Test LiteLLM for SQL query generation scenarios."""

    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"),
        reason="AWS credentials not available"
    )
    def test_generate_simple_sql_query(self):
        """Test generating a simple SQL query."""
        system = """You are a SQL expert. Generate only the SQL query, no explanations.
Schema: customers (id, name, email)"""

        prompt = "Write a query to get all customers"

        response = get_completion(
            prompt,
            system=system,
            model=MODELS["haiku"],
            temperature=0.0,
            max_tokens=100
        )

        assert response is not None
        response_upper = response.upper()
        assert "SELECT" in response_upper
        assert "FROM" in response_upper
        assert "CUSTOMERS" in response_upper

    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"),
        reason="AWS credentials not available"
    )
    def test_generate_sql_with_join(self):
        """Test generating SQL query with JOIN."""
        system = """You are a SQL expert. Generate only the SQL query, no explanations.
Schema:
- customers (id, name, email)
- orders (id, customer_id, total, status)"""

        prompt = "Write a query to get customer names and their order totals"

        response = get_completion(
            prompt,
            system=system,
            model=MODELS["haiku"],
            temperature=0.0,
            max_tokens=200
        )

        assert response is not None
        response_upper = response.upper()
        assert "SELECT" in response_upper
        assert "JOIN" in response_upper
        assert "CUSTOMERS" in response_upper
        assert "ORDERS" in response_upper

    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"),
        reason="AWS credentials not available"
    )
    @pytest.mark.asyncio
    async def test_generate_sql_with_aggregation(self):
        """Test generating SQL query with aggregation."""
        system = """You are a SQL expert. Generate only the SQL query, no explanations.
Schema: orders (id, customer_id, total, status)"""

        prompt = "Count how many orders each customer has"

        response = await get_completion_async(
            prompt,
            system=system,
            model=MODELS["haiku"],
            temperature=0.0,
            max_tokens=150
        )

        assert response is not None
        response_upper = response.upper()
        assert "SELECT" in response_upper
        assert "COUNT" in response_upper
        assert "GROUP BY" in response_upper


class TestLiteLLMErrorHandling:
    """Test error handling in LiteLLM integration."""

    def test_client_creation_without_credentials(self):
        """Test that client can be created even without AWS credentials."""
        # The client should be created, but calls will fail
        with patch.dict(os.environ, {}, clear=False):
            # Remove AWS credentials temporarily
            env_backup = {}
            for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"]:
                if key in os.environ:
                    env_backup[key] = os.environ.pop(key)

            try:
                client = LiteLLMClient(model=MODELS["haiku"])
                assert client is not None
            finally:
                # Restore credentials
                os.environ.update(env_backup)

    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"),
        reason="AWS credentials not available"
    )
    def test_invalid_model_name(self):
        """Test handling of invalid model name."""
        with pytest.raises(Exception):  # LiteLLM will raise an exception
            get_completion(
                "test",
                model="bedrock/invalid-model-12345",
                max_tokens=10
            )

    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"),
        reason="AWS credentials not available"
    )
    def test_empty_prompt(self):
        """Test handling of empty prompt."""
        # Should handle empty prompt gracefully
        response = get_completion("", model=MODELS["haiku"], max_tokens=10)
        assert response is not None
        assert isinstance(response, str)


class TestModelAliases:
    """Test model alias resolution."""

    def test_model_aliases_exist(self):
        """Test that model aliases are properly defined."""
        assert "opus" in MODELS
        assert "sonnet" in MODELS
        assert "haiku" in MODELS

        assert MODELS["opus"].startswith("bedrock/")
        assert MODELS["sonnet"].startswith("bedrock/")
        assert MODELS["haiku"].startswith("bedrock/")

    def test_default_model(self):
        """Test that default model is set."""
        assert DEFAULT_MODEL is not None
        assert DEFAULT_MODEL.startswith("bedrock/")
        assert "anthropic" in DEFAULT_MODEL.lower()
