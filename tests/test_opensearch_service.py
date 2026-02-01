"""Tests for OpenSearch Service with vector embeddings and similarity search."""

import json
import pytest
from datetime import datetime
from typing import Dict, List
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from uuid import UUID, uuid4

from opensearchpy.exceptions import NotFoundError, RequestError

from text2x.services.opensearch_service import OpenSearchService
from text2x.config import Settings


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_settings():
    """Mock settings for tests."""
    settings = Mock(spec=Settings)
    settings.opensearch_host = "localhost"
    settings.opensearch_port = 9200
    settings.opensearch_index = "test_rag_examples"
    settings.opensearch_use_ssl = False
    settings.opensearch_username = None
    settings.opensearch_password = None
    settings.bedrock_region = "us-east-1"
    settings.bedrock_embedding_model = "amazon.titan-embed-text-v2:0"
    settings.aws_access_key_id = None
    settings.aws_secret_access_key = None
    return settings


@pytest.fixture
def mock_opensearch_client():
    """Mock AsyncOpenSearch client."""
    client = AsyncMock()

    # Mock indices operations
    client.indices = AsyncMock()
    client.indices.exists = AsyncMock(return_value=False)
    client.indices.create = AsyncMock(return_value={"acknowledged": True})

    # Mock index operation
    async def mock_index(**kwargs):
        return {
            "result": "created",
            "_id": kwargs.get("id", str(uuid4())),
            "_index": kwargs.get("index", "test_rag_examples"),
        }

    client.index = AsyncMock(side_effect=mock_index)

    # Mock search operation
    async def mock_search(**kwargs):
        return {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_id": "test-id-1",
                        "_score": 0.95,
                        "_source": {
                            "id": "test-id-1",
                            "nl_query": "Show me all users",
                            "generated_query": "SELECT * FROM users",
                            "provider_id": "test-provider",
                            "status": "approved",
                            "is_good_example": True,
                            "involved_tables": ["users"],
                            "query_intent": "filter",
                            "complexity_level": "simple",
                            "metadata": {},
                        },
                    }
                ],
            }
        }

    client.search = AsyncMock(side_effect=mock_search)

    # Mock delete operation
    async def mock_delete(**kwargs):
        return {"result": "deleted"}

    client.delete = AsyncMock(side_effect=mock_delete)

    # Mock close operation
    client.close = AsyncMock()

    return client


@pytest.fixture
def mock_bedrock_runtime():
    """Mock boto3 Bedrock Runtime client."""
    client = Mock()

    def mock_invoke_model(**kwargs):
        # Generate mock embedding
        embedding = [0.1] * 1024  # Titan v2: 1024 dimensions

        response_body = {"embedding": embedding}

        # Mock response structure
        response = {"body": Mock()}
        response["body"].read = Mock(
            return_value=json.dumps(response_body).encode()
        )

        return response

    client.invoke_model = Mock(side_effect=mock_invoke_model)
    return client


@pytest.fixture
def opensearch_service(mock_settings, mock_opensearch_client, mock_bedrock_runtime):
    """Create OpenSearchService with mocked dependencies."""
    with patch("boto3.client", return_value=mock_bedrock_runtime):
        service = OpenSearchService(
            settings=mock_settings,
            opensearch_client=mock_opensearch_client,
        )
        return service


# ============================================================================
# Initialization Tests
# ============================================================================


def test_service_initialization(mock_settings, mock_opensearch_client):
    """Test that service initializes correctly."""
    with patch("boto3.client"):
        service = OpenSearchService(
            settings=mock_settings,
            opensearch_client=mock_opensearch_client,
        )

        assert service.settings == mock_settings
        assert service.index_name == "test_rag_examples"
        assert service.client == mock_opensearch_client
        assert service.embedding_model == "amazon.titan-embed-text-v2:0"
        assert service.embedding_dimension == 1024


def test_service_initialization_with_auth(mock_opensearch_client):
    """Test service initialization with authentication."""
    settings = Mock(spec=Settings)
    settings.opensearch_host = "secure-cluster.com"
    settings.opensearch_port = 443
    settings.opensearch_index = "rag_examples"
    settings.opensearch_use_ssl = True
    settings.opensearch_username = "admin"
    settings.opensearch_password = "secret"
    settings.bedrock_region = "us-east-1"
    settings.bedrock_embedding_model = "amazon.titan-embed-text-v2:0"
    settings.aws_access_key_id = "test_key"
    settings.aws_secret_access_key = "test_secret"

    with patch("boto3.client") as mock_boto_client:
        service = OpenSearchService(
            settings=settings,
            opensearch_client=mock_opensearch_client,
        )

        # Verify Bedrock client was created with credentials
        mock_boto_client.assert_called_once()
        call_kwargs = mock_boto_client.call_args[1]
        assert call_kwargs["region_name"] == "us-east-1"
        assert call_kwargs["aws_access_key_id"] == "test_key"
        assert call_kwargs["aws_secret_access_key"] == "test_secret"


# ============================================================================
# Index Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_index_if_not_exists_creates_new_index(opensearch_service):
    """Test creating a new index."""
    opensearch_service.client.indices.exists = AsyncMock(return_value=False)

    result = await opensearch_service.create_index_if_not_exists()

    assert result is True
    opensearch_service.client.indices.create.assert_called_once()

    # Verify index settings
    call_args = opensearch_service.client.indices.create.call_args
    index_body = call_args[1]["body"]

    assert index_body["settings"]["index"]["knn"] is True
    assert "embedding" in index_body["mappings"]["properties"]
    assert index_body["mappings"]["properties"]["embedding"]["type"] == "knn_vector"
    assert (
        index_body["mappings"]["properties"]["embedding"]["dimension"] == 1024
    )


@pytest.mark.asyncio
async def test_create_index_if_not_exists_index_already_exists(opensearch_service):
    """Test when index already exists."""
    opensearch_service.client.indices.exists = AsyncMock(return_value=True)

    result = await opensearch_service.create_index_if_not_exists()

    assert result is False
    opensearch_service.client.indices.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_index_handles_resource_already_exists(opensearch_service):
    """Test handling resource_already_exists_exception."""
    opensearch_service.client.indices.exists = AsyncMock(return_value=False)
    opensearch_service.client.indices.create = AsyncMock(
        side_effect=RequestError(
            400, "resource_already_exists_exception", "index already exists"
        )
    )

    result = await opensearch_service.create_index_if_not_exists()

    assert result is False


@pytest.mark.asyncio
async def test_create_index_handles_other_errors(opensearch_service):
    """Test handling other index creation errors."""
    opensearch_service.client.indices.exists = AsyncMock(return_value=False)
    opensearch_service.client.indices.create = AsyncMock(
        side_effect=Exception("Connection error")
    )

    with pytest.raises(Exception, match="Connection error"):
        await opensearch_service.create_index_if_not_exists()


# ============================================================================
# Document Indexing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_index_document_with_vector(opensearch_service):
    """Test indexing a document with pre-computed vector."""
    doc_id = str(uuid4())
    vector = [0.1] * 1024
    metadata = {
        "nl_query": "Show all users",
        "generated_query": "SELECT * FROM users",
        "provider_id": "test-provider",
        "status": "approved",
        "is_good_example": True,
        "involved_tables": ["users"],
        "query_intent": "filter",
        "complexity_level": "simple",
    }

    result = await opensearch_service.index_document(doc_id, vector, metadata)

    assert result is True
    opensearch_service.client.index.assert_called_once()

    # Verify indexed document structure
    call_args = opensearch_service.client.index.call_args
    assert call_args[1]["id"] == doc_id
    assert call_args[1]["index"] == "test_rag_examples"

    document = call_args[1]["body"]
    assert document["id"] == doc_id
    assert document["embedding"] == vector
    assert document["nl_query"] == "Show all users"
    assert document["provider_id"] == "test-provider"


@pytest.mark.asyncio
async def test_index_document_generates_embedding(opensearch_service):
    """Test indexing document with automatic embedding generation."""
    doc_id = str(uuid4())
    metadata = {
        "nl_query": "Count active users",
        "generated_query": "SELECT COUNT(*) FROM users WHERE active = true",
        "provider_id": "test-provider",
    }

    result = await opensearch_service.index_document(doc_id, None, metadata)

    assert result is True

    # Verify embedding was generated
    opensearch_service.bedrock_runtime.invoke_model.assert_called_once()

    # Verify document was indexed with generated embedding
    opensearch_service.client.index.assert_called_once()
    call_args = opensearch_service.client.index.call_args
    document = call_args[1]["body"]
    assert "embedding" in document
    assert len(document["embedding"]) == 1024


@pytest.mark.asyncio
async def test_index_document_missing_nl_query(opensearch_service):
    """Test that indexing fails without nl_query."""
    doc_id = str(uuid4())
    metadata = {
        "generated_query": "SELECT * FROM users",
        "provider_id": "test-provider",
    }

    with pytest.raises(ValueError, match="nl_query is required"):
        await opensearch_service.index_document(doc_id, None, metadata)


@pytest.mark.asyncio
async def test_index_document_handles_errors(opensearch_service):
    """Test handling indexing errors."""
    opensearch_service.client.index = AsyncMock(
        side_effect=Exception("Indexing failed")
    )

    doc_id = str(uuid4())
    metadata = {"nl_query": "test query", "provider_id": "test-provider"}

    with pytest.raises(Exception, match="Indexing failed"):
        await opensearch_service.index_document(doc_id, [0.1] * 1024, metadata)


# ============================================================================
# Search Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_similar_with_vector(opensearch_service):
    """Test vector similarity search."""
    query_vector = [0.2] * 1024

    results = await opensearch_service.search_similar(
        query_vector=query_vector,
        k=5,
        provider_id="test-provider",
    )

    assert len(results) > 0
    assert results[0]["id"] == "test-id-1"
    assert results[0]["score"] == 0.95
    assert results[0]["nl_query"] == "Show me all users"

    opensearch_service.client.search.assert_called_once()


@pytest.mark.asyncio
async def test_search_similar_with_text(opensearch_service):
    """Test text-based search with automatic embedding generation."""
    results = await opensearch_service.search_similar(
        query_text="Show all active users",
        k=5,
    )

    assert len(results) > 0

    # Verify embedding was generated
    opensearch_service.bedrock_runtime.invoke_model.assert_called_once()

    # Verify search was executed
    opensearch_service.client.search.assert_called_once()


@pytest.mark.asyncio
async def test_search_similar_hybrid_mode(opensearch_service):
    """Test hybrid search combining vector and keyword."""
    results = await opensearch_service.search_similar(
        query_text="Show all active users",
        k=5,
        hybrid=True,
    )

    assert len(results) > 0

    # Verify search query uses script_score for hybrid
    call_args = opensearch_service.client.search.call_args
    search_body = call_args[1]["body"]
    assert "script_score" in search_body["query"]


@pytest.mark.asyncio
async def test_search_similar_with_filters(opensearch_service):
    """Test search with provider and intent filters."""
    results = await opensearch_service.search_similar(
        query_text="Show users",
        k=5,
        provider_id="test-provider",
        query_intent="filter",
    )

    # Verify filters were applied
    call_args = opensearch_service.client.search.call_args
    search_body = call_args[1]["body"]

    # Check that filters are present in the query
    assert "filter" in str(search_body)


@pytest.mark.asyncio
async def test_search_similar_min_score_filter(opensearch_service):
    """Test filtering results by minimum score."""
    # Mock search to return results with varying scores
    async def mock_search(**kwargs):
        return {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {
                        "_id": "id-1",
                        "_score": 0.95,
                        "_source": {
                            "id": "id-1",
                            "nl_query": "test query 1",
                            "provider_id": "test",
                            "status": "approved",
                        },
                    },
                    {
                        "_id": "id-2",
                        "_score": 0.75,
                        "_source": {
                            "id": "id-2",
                            "nl_query": "test query 2",
                            "provider_id": "test",
                            "status": "approved",
                        },
                    },
                    {
                        "_id": "id-3",
                        "_score": 0.55,
                        "_source": {
                            "id": "id-3",
                            "nl_query": "test query 3",
                            "provider_id": "test",
                            "status": "approved",
                        },
                    },
                ],
            }
        }

    opensearch_service.client.search = AsyncMock(side_effect=mock_search)

    results = await opensearch_service.search_similar(
        query_text="test",
        k=10,
        min_score=0.7,
    )

    # Only results with score >= 0.7 should be returned
    assert len(results) == 2
    assert all(r["score"] >= 0.7 for r in results)


@pytest.mark.asyncio
async def test_search_similar_no_query_raises_error(opensearch_service):
    """Test that search fails without query_vector or query_text."""
    with pytest.raises(
        ValueError, match="Either query_vector or query_text must be provided"
    ):
        await opensearch_service.search_similar(k=5)


@pytest.mark.asyncio
async def test_search_similar_handles_errors(opensearch_service):
    """Test handling search errors."""
    opensearch_service.client.search = AsyncMock(
        side_effect=Exception("Search failed")
    )

    with pytest.raises(Exception, match="Search failed"):
        await opensearch_service.search_similar(
            query_text="test query",
            k=5,
        )


# ============================================================================
# Document Deletion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_document_success(opensearch_service):
    """Test successful document deletion."""
    doc_id = str(uuid4())

    result = await opensearch_service.delete_document(doc_id)

    assert result is True
    opensearch_service.client.delete.assert_called_once_with(
        index="test_rag_examples",
        id=doc_id,
        refresh=True,
    )


@pytest.mark.asyncio
async def test_delete_document_not_found(opensearch_service):
    """Test deleting non-existent document."""
    opensearch_service.client.delete = AsyncMock(
        side_effect=NotFoundError(404, "not_found", "document not found")
    )

    doc_id = str(uuid4())
    result = await opensearch_service.delete_document(doc_id)

    assert result is False


@pytest.mark.asyncio
async def test_delete_document_handles_errors(opensearch_service):
    """Test handling deletion errors."""
    opensearch_service.client.delete = AsyncMock(
        side_effect=Exception("Deletion failed")
    )

    doc_id = str(uuid4())

    with pytest.raises(Exception, match="Deletion failed"):
        await opensearch_service.delete_document(doc_id)


# ============================================================================
# Embedding Generation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_embedding_success(opensearch_service):
    """Test successful embedding generation."""
    text = "Show me all active users"

    embedding = await opensearch_service._generate_embedding(text)

    assert isinstance(embedding, list)
    assert len(embedding) == 1024
    assert all(isinstance(x, float) for x in embedding)

    # Verify Bedrock was called correctly
    opensearch_service.bedrock_runtime.invoke_model.assert_called_once()
    call_args = opensearch_service.bedrock_runtime.invoke_model.call_args

    assert call_args[1]["modelId"] == "amazon.titan-embed-text-v2:0"
    assert call_args[1]["contentType"] == "application/json"

    # Verify request body
    body = json.loads(call_args[1]["body"])
    assert body["inputText"] == text


@pytest.mark.asyncio
async def test_generate_embedding_handles_errors(opensearch_service):
    """Test handling embedding generation errors."""
    opensearch_service.bedrock_runtime.invoke_model = Mock(
        side_effect=Exception("Bedrock error")
    )

    with pytest.raises(Exception, match="Bedrock error"):
        await opensearch_service._generate_embedding("test text")


@pytest.mark.asyncio
async def test_generate_embedding_invalid_response(opensearch_service):
    """Test handling invalid Bedrock response."""

    def mock_invoke_model(**kwargs):
        response = {"body": Mock()}
        response["body"].read = Mock(
            return_value=json.dumps({"no_embedding": []}).encode()
        )
        return response

    opensearch_service.bedrock_runtime.invoke_model = Mock(
        side_effect=mock_invoke_model
    )

    with pytest.raises(ValueError, match="No embedding returned"):
        await opensearch_service._generate_embedding("test text")


# ============================================================================
# Query Building Tests
# ============================================================================


def test_build_vector_query(opensearch_service):
    """Test building pure vector search query."""
    query_vector = [0.1] * 1024

    query = opensearch_service._build_vector_query(
        query_vector=query_vector,
        k=5,
        provider_id="test-provider",
        query_intent="filter",
    )

    assert query["size"] == 5
    assert "knn" in query["query"]["bool"]["must"][0]
    assert query["query"]["bool"]["must"][0]["knn"]["embedding"]["k"] == 5

    # Verify filters
    filters = query["query"]["bool"]["filter"]
    assert {"term": {"status": "approved"}} in filters
    assert {"term": {"provider_id": "test-provider"}} in filters
    assert {"term": {"query_intent": "filter"}} in filters


def test_build_hybrid_query(opensearch_service):
    """Test building hybrid search query."""
    query_vector = [0.1] * 1024
    query_text = "Show all users"

    query = opensearch_service._build_hybrid_query(
        query_vector=query_vector,
        query_text=query_text,
        k=5,
        provider_id="test-provider",
    )

    assert query["size"] == 5
    assert "script_score" in query["query"]
    assert "cosineSimilarity" in query["query"]["script_score"]["script"]["source"]

    # Verify filters
    filters = query["query"]["script_score"]["query"]["bool"]["filter"]
    assert {"term": {"status": "approved"}} in filters
    assert {"term": {"provider_id": "test-provider"}} in filters


# ============================================================================
# Connection Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_close_connection(opensearch_service):
    """Test closing OpenSearch connection."""
    await opensearch_service.close()

    opensearch_service.client.close.assert_called_once()
