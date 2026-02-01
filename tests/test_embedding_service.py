"""Tests for Bedrock Titan Embedding Service"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from text2x.services.embedding_service import (
    BedrockEmbeddingService,
    get_embedding_service,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_bedrock_client():
    """Mock boto3 Bedrock client"""
    client = Mock()

    # Mock successful response
    def mock_invoke_model(**kwargs):
        model_id = kwargs.get("modelId", "amazon.titan-embed-text-v2:0")

        # Generate mock embedding based on model version
        if "v2" in model_id:
            embedding = [0.1] * 1024  # Titan v2: 1024 dimensions
        else:
            embedding = [0.1] * 1536  # Titan v1: 1536 dimensions

        response_body = {"embedding": embedding}

        # Mock the response structure
        response = {
            "body": Mock()
        }
        response["body"].read = Mock(return_value=json.dumps(response_body).encode())

        return response

    client.invoke_model = Mock(side_effect=mock_invoke_model)

    return client


@pytest.fixture
def embedding_service(mock_bedrock_client):
    """Create embedding service with mocked client"""
    with patch("boto3.client", return_value=mock_bedrock_client):
        service = BedrockEmbeddingService(
            region="us-east-1",
            model_id="amazon.titan-embed-text-v2:0",
        )
        return service


# ============================================================================
# Initialization Tests
# ============================================================================

def test_service_initialization():
    """Test that service initializes correctly with default parameters"""
    with patch("boto3.client") as mock_boto_client:
        service = BedrockEmbeddingService(
            region="us-west-2",
            model_id="amazon.titan-embed-text-v2:0",
        )

        assert service.region == "us-west-2"
        assert service.model_id == "amazon.titan-embed-text-v2:0"
        assert service.max_batch_size == 25

        # Verify boto3 client was created
        mock_boto_client.assert_called_once()
        call_kwargs = mock_boto_client.call_args[1]
        assert call_kwargs["region_name"] == "us-west-2"


def test_service_initialization_with_credentials():
    """Test that service initializes with explicit AWS credentials"""
    with patch("boto3.client") as mock_boto_client:
        service = BedrockEmbeddingService(
            region="us-east-1",
            model_id="amazon.titan-embed-text-v2:0",
            aws_access_key_id="test_key",
            aws_secret_access_key="test_secret",
        )

        # Verify credentials were passed
        call_kwargs = mock_boto_client.call_args[1]
        assert call_kwargs["aws_access_key_id"] == "test_key"
        assert call_kwargs["aws_secret_access_key"] == "test_secret"


# ============================================================================
# Single Text Embedding Tests
# ============================================================================

@pytest.mark.asyncio
async def test_embed_text_success(embedding_service):
    """Test successful embedding generation for single text"""
    text = "What is the total revenue for Q1 2024?"

    embedding = await embedding_service.embed_text(text)

    assert embedding is not None
    assert isinstance(embedding, list)
    assert len(embedding) == 1024  # Titan v2 dimensions
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.asyncio
async def test_embed_text_v1_model(mock_bedrock_client):
    """Test embedding with Titan v1 model (1536 dimensions)"""
    with patch("boto3.client", return_value=mock_bedrock_client):
        service = BedrockEmbeddingService(
            region="us-east-1",
            model_id="amazon.titan-embed-text-v1",
        )

        embedding = await service.embed_text("Test query")

        assert len(embedding) == 1536  # Titan v1 dimensions


@pytest.mark.asyncio
async def test_embed_text_empty_string(embedding_service):
    """Test that empty string raises ValueError"""
    with pytest.raises(ValueError, match="Text cannot be empty"):
        await embedding_service.embed_text("")


@pytest.mark.asyncio
async def test_embed_text_whitespace_only(embedding_service):
    """Test that whitespace-only string raises ValueError"""
    with pytest.raises(ValueError, match="Text cannot be empty"):
        await embedding_service.embed_text("   ")


@pytest.mark.asyncio
async def test_embed_text_truncation(embedding_service, mock_bedrock_client):
    """Test that long text is truncated"""
    # Create text longer than max_chars (30000)
    long_text = "a" * 40000

    embedding = await embedding_service.embed_text(long_text)

    assert embedding is not None

    # Verify invoke_model was called with truncated text
    call_args = mock_bedrock_client.invoke_model.call_args
    body = json.loads(call_args[1]["body"])
    assert len(body["inputText"]) == 30000


@pytest.mark.asyncio
async def test_embed_text_bedrock_error(embedding_service, mock_bedrock_client):
    """Test handling of Bedrock API errors"""
    # Mock ClientError
    error_response = {
        "Error": {
            "Code": "ThrottlingException",
            "Message": "Rate exceeded"
        }
    }
    mock_bedrock_client.invoke_model.side_effect = ClientError(
        error_response,
        "InvokeModel"
    )

    # Should raise after retries
    with pytest.raises(ClientError):
        await embedding_service.embed_text("Test query")


@pytest.mark.asyncio
async def test_embed_text_invalid_response(embedding_service, mock_bedrock_client):
    """Test handling of invalid response from Bedrock"""
    # Mock response without embedding field
    response = {
        "body": Mock()
    }
    response["body"].read = Mock(return_value=json.dumps({}).encode())
    # Need to reset side_effect to None before setting return_value
    mock_bedrock_client.invoke_model.side_effect = None
    mock_bedrock_client.invoke_model.return_value = response

    # The retry decorator will retry this, but should eventually raise ValueError
    with pytest.raises(ValueError, match="No embedding returned from Bedrock"):
        await embedding_service.embed_text("Test query")


# ============================================================================
# Batch Embedding Tests
# ============================================================================

@pytest.mark.asyncio
async def test_embed_batch_success(embedding_service):
    """Test successful batch embedding generation"""
    texts = [
        "What is the total revenue?",
        "How many customers do we have?",
        "Show me the top products",
    ]

    embeddings = await embedding_service.embed_batch(texts)

    assert len(embeddings) == 3
    assert all(len(emb) == 1024 for emb in embeddings)
    assert all(isinstance(emb, list) for emb in embeddings)


@pytest.mark.asyncio
async def test_embed_batch_empty_list(embedding_service):
    """Test that empty list raises ValueError"""
    with pytest.raises(ValueError, match="Texts list cannot be empty"):
        await embedding_service.embed_batch([])


@pytest.mark.asyncio
async def test_embed_batch_large_batch(embedding_service):
    """Test batch processing with more texts than max_batch_size"""
    # Create 50 texts (max_batch_size is 25)
    texts = [f"Query number {i}" for i in range(50)]

    embeddings = await embedding_service.embed_batch(texts)

    assert len(embeddings) == 50
    assert all(len(emb) == 1024 for emb in embeddings)


@pytest.mark.asyncio
async def test_embed_batch_partial_failure(embedding_service, mock_bedrock_client):
    """Test that batch continues even if some embeddings fail"""
    texts = ["Query 1", "Query 2", "Query 3"]

    # Make the second call fail
    call_count = [0]
    original_invoke = mock_bedrock_client.invoke_model

    def mock_invoke_with_failure(**kwargs):
        call_count[0] += 1
        if call_count[0] == 2:
            raise ClientError(
                {"Error": {"Code": "ServiceException", "Message": "Service error"}},
                "InvokeModel"
            )
        return original_invoke(**kwargs)

    mock_bedrock_client.invoke_model.side_effect = mock_invoke_with_failure

    embeddings = await embedding_service.embed_batch(texts)

    # Should still return 3 embeddings (with zero vector for failed one)
    assert len(embeddings) == 3
    assert embeddings[1] == [0.0] * 1024  # Failed embedding becomes zero vector


@pytest.mark.asyncio
async def test_embed_batch_with_progress(embedding_service, caplog):
    """Test batch embedding with progress logging"""
    import logging
    caplog.set_level(logging.INFO)

    texts = [f"Query {i}" for i in range(30)]  # More than one batch

    await embedding_service.embed_batch(texts, show_progress=True)

    # Check that progress was logged
    assert "Processing batch" in caplog.text


# ============================================================================
# Request Body Format Tests
# ============================================================================

@pytest.mark.asyncio
async def test_titan_v2_request_format(embedding_service, mock_bedrock_client):
    """Test that Titan v2 request uses correct format"""
    await embedding_service.embed_text("Test query")

    call_args = mock_bedrock_client.invoke_model.call_args
    body = json.loads(call_args[1]["body"])

    assert "inputText" in body
    assert "dimensions" in body
    assert body["dimensions"] == 1024
    assert "normalize" in body
    assert body["normalize"] is True


@pytest.mark.asyncio
async def test_titan_v1_request_format(mock_bedrock_client):
    """Test that Titan v1 request uses correct format"""
    with patch("boto3.client", return_value=mock_bedrock_client):
        service = BedrockEmbeddingService(
            region="us-east-1",
            model_id="amazon.titan-embed-text-v1",
        )

        await service.embed_text("Test query")

        call_args = mock_bedrock_client.invoke_model.call_args
        body = json.loads(call_args[1]["body"])

        # v1 format should not have dimensions or normalize
        assert "inputText" in body
        assert "dimensions" not in body
        assert "normalize" not in body


# ============================================================================
# Caching Tests
# ============================================================================

def test_get_embedding_service_caching():
    """Test that get_embedding_service returns cached instance"""
    with patch("boto3.client") as mock_boto_client:
        # Clear cache
        get_embedding_service.cache_clear()

        service1 = get_embedding_service(
            region="us-east-1",
            model_id="amazon.titan-embed-text-v2:0"
        )

        service2 = get_embedding_service(
            region="us-east-1",
            model_id="amazon.titan-embed-text-v2:0"
        )

        # Should return same instance
        assert service1 is service2

        # boto3.client should only be called once due to caching
        assert mock_boto_client.call_count == 1


# ============================================================================
# Retry Logic Tests
# ============================================================================

@pytest.mark.asyncio
async def test_retry_on_throttling(embedding_service, mock_bedrock_client):
    """Test that service retries on throttling errors"""
    call_count = [0]

    def mock_invoke_with_retry(**kwargs):
        call_count[0] += 1
        if call_count[0] < 3:
            # Fail first 2 times
            raise ClientError(
                {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
                "InvokeModel"
            )
        # Succeed on 3rd try - return successful embedding
        model_id = kwargs.get("modelId", "amazon.titan-embed-text-v2:0")
        embedding = [0.1] * 1024  # Titan v2: 1024 dimensions
        response_body = {"embedding": embedding}
        response = {
            "body": Mock()
        }
        response["body"].read = Mock(return_value=json.dumps(response_body).encode())
        return response

    mock_bedrock_client.invoke_model.side_effect = mock_invoke_with_retry

    # Should succeed after retries
    embedding = await embedding_service.embed_text("Test query")
    assert embedding is not None
    assert call_count[0] == 3  # Should have tried 3 times


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.asyncio
async def test_batch_performance_logging(embedding_service, caplog):
    """Test that batch embedding logs performance metrics"""
    import logging
    caplog.set_level(logging.INFO)

    texts = [f"Query {i}" for i in range(10)]

    await embedding_service.embed_batch(texts)

    # Check that performance was logged
    assert "Embedded 10 texts" in caplog.text
    assert "texts/s" in caplog.text
