"""
OpenSearch service for managing vector embeddings and similarity search.

This service provides:
- Document indexing with vector embeddings
- k-NN similarity search
- Hybrid search (vector + keyword)
- AWS Bedrock Titan embedding generation
- Index management
"""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

import boto3
from opensearchpy import AsyncOpenSearch, OpenSearch
from opensearchpy.exceptions import NotFoundError, RequestError

from text2x.config import Settings, get_settings

logger = logging.getLogger(__name__)


class OpenSearchService:
    """Service for OpenSearch vector operations and similarity search."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        opensearch_client: Optional[AsyncOpenSearch] = None,
    ):
        """
        Initialize OpenSearch service.

        Args:
            settings: Application settings (will use get_settings() if not provided)
            opensearch_client: Optional pre-configured OpenSearch client
        """
        self.settings = settings or get_settings()
        self.index_name = self.settings.opensearch_index

        # Initialize OpenSearch client
        if opensearch_client:
            self.client = opensearch_client
        else:
            self.client = self._create_client()

        # Initialize Bedrock client for embeddings
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.settings.bedrock_region,
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
        )

        self.embedding_model = self.settings.bedrock_embedding_model
        self.embedding_dimension = 1024  # Titan v2 embedding dimension

        logger.info(
            f"OpenSearchService initialized with index '{self.index_name}' "
            f"and embedding model '{self.embedding_model}'"
        )

    def _create_client(self) -> AsyncOpenSearch:
        """
        Create OpenSearch client from settings.

        Returns:
            Configured AsyncOpenSearch client
        """
        # Build connection parameters
        host = self.settings.opensearch_host
        port = self.settings.opensearch_port
        use_ssl = self.settings.opensearch_use_ssl

        # Authentication
        http_auth = None
        if self.settings.opensearch_username and self.settings.opensearch_password:
            http_auth = (
                self.settings.opensearch_username,
                self.settings.opensearch_password,
            )

        client = AsyncOpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=http_auth,
            use_ssl=use_ssl,
            verify_certs=use_ssl,
            ssl_show_warn=False,
            timeout=30,
        )

        logger.info(f"Created OpenSearch client for {host}:{port}")
        return client

    async def create_index_if_not_exists(self) -> bool:
        """
        Create OpenSearch index with k-NN settings if it doesn't exist.

        The index is configured for:
        - k-NN vector search on embedding field
        - Full-text search on nl_query field
        - Filtering on provider_id, status, intent, etc.

        Returns:
            True if index was created, False if it already existed

        Raises:
            Exception: If index creation fails
        """
        try:
            # Check if index exists
            exists = await self.client.indices.exists(index=self.index_name)

            if exists:
                logger.info(f"Index '{self.index_name}' already exists")
                return False

            # Define index mapping
            index_body = {
                "settings": {
                    "index": {
                        "knn": True,  # Enable k-NN
                        "knn.algo_param.ef_search": 512,
                        "number_of_shards": 2,
                        "number_of_replicas": 1,
                    }
                },
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": self.embedding_dimension,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": 512,
                                    "m": 16,
                                },
                            },
                        },
                        "nl_query": {
                            "type": "text",
                            "analyzer": "standard",
                        },
                        "generated_query": {
                            "type": "text",
                            "index": False,
                        },
                        "provider_id": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "is_good_example": {"type": "boolean"},
                        "involved_tables": {"type": "keyword"},
                        "query_intent": {"type": "keyword"},
                        "complexity_level": {"type": "keyword"},
                        "reviewed_by": {"type": "keyword"},
                        "reviewed_at": {"type": "date"},
                        "expert_corrected_query": {
                            "type": "text",
                            "index": False,
                        },
                        "metadata": {"type": "object", "enabled": False},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                    }
                },
            }

            # Create index
            await self.client.indices.create(
                index=self.index_name,
                body=index_body,
            )

            logger.info(
                f"Created index '{self.index_name}' with k-NN configuration "
                f"(dimension={self.embedding_dimension})"
            )
            return True

        except RequestError as e:
            if "resource_already_exists_exception" in str(e):
                logger.info(f"Index '{self.index_name}' already exists")
                return False
            else:
                logger.error(f"Failed to create index: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error creating index: {e}")
            raise

    async def index_document(
        self,
        doc_id: str,
        vector: Optional[List[float]],
        metadata: Dict[str, Any],
    ) -> bool:
        """
        Index a document with its vector embedding and metadata.

        If vector is not provided, it will be generated from nl_query in metadata.

        Args:
            doc_id: Document ID (usually RAGExample UUID)
            vector: Pre-computed embedding vector (optional)
            metadata: Document metadata including:
                - nl_query: Natural language query (required)
                - generated_query: Generated DSL query
                - provider_id: Provider ID
                - status: Example status
                - is_good_example: Whether this is a good example
                - involved_tables: List of table names
                - query_intent: Query intent
                - complexity_level: Complexity level
                - reviewed_by: Reviewer username
                - reviewed_at: Review timestamp
                - expert_corrected_query: Expert correction
                - metadata: Additional metadata dict

        Returns:
            True if successful

        Raises:
            ValueError: If required fields are missing
            Exception: If indexing fails
        """
        if "nl_query" not in metadata:
            raise ValueError("nl_query is required in metadata")

        # Generate embedding if not provided
        if vector is None:
            logger.debug(f"Generating embedding for document {doc_id}")
            vector = await self._generate_embedding(metadata["nl_query"])

        # Prepare document
        document = {
            "id": doc_id,
            "embedding": vector,
            "nl_query": metadata.get("nl_query"),
            "generated_query": metadata.get("generated_query"),
            "provider_id": metadata.get("provider_id"),
            "status": metadata.get("status", "approved"),
            "is_good_example": metadata.get("is_good_example", True),
            "involved_tables": metadata.get("involved_tables", []),
            "query_intent": metadata.get("query_intent", "unknown"),
            "complexity_level": metadata.get("complexity_level", "medium"),
            "reviewed_by": metadata.get("reviewed_by"),
            "reviewed_at": metadata.get("reviewed_at"),
            "expert_corrected_query": metadata.get("expert_corrected_query"),
            "metadata": metadata.get("metadata", {}),
            "created_at": metadata.get("created_at"),
            "updated_at": metadata.get("updated_at"),
        }

        try:
            # Index document
            response = await self.client.index(
                index=self.index_name,
                id=doc_id,
                body=document,
                refresh=True,  # Make immediately searchable
            )

            logger.info(
                f"Indexed document {doc_id} in '{self.index_name}' "
                f"(result: {response.get('result')})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to index document {doc_id}: {e}")
            raise

    async def search_similar(
        self,
        query_vector: Optional[List[float]] = None,
        query_text: Optional[str] = None,
        k: int = 5,
        provider_id: Optional[str] = None,
        query_intent: Optional[str] = None,
        min_score: float = 0.0,
        hybrid: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using k-NN vector search.

        Supports:
        - Pure vector search (using query_vector)
        - Pure text search (using query_text with BM25)
        - Hybrid search (combining both with weights)

        Args:
            query_vector: Query embedding vector (optional if query_text provided)
            query_text: Query text for keyword search (optional)
            k: Number of results to return
            provider_id: Filter by provider ID
            query_intent: Filter by query intent
            min_score: Minimum similarity score threshold
            hybrid: If True, use hybrid search combining vector + keyword

        Returns:
            List of matching documents with scores and metadata

        Raises:
            ValueError: If neither query_vector nor query_text is provided
            Exception: If search fails
        """
        if query_vector is None and query_text is None:
            raise ValueError("Either query_vector or query_text must be provided")

        # Generate embedding from text if vector not provided
        if query_vector is None and query_text is not None:
            logger.debug("Generating embedding for search query")
            query_vector = await self._generate_embedding(query_text)

        try:
            # Build search query
            if hybrid and query_text is not None:
                # Hybrid search: vector + keyword
                search_body = self._build_hybrid_query(
                    query_vector=query_vector,
                    query_text=query_text,
                    k=k,
                    provider_id=provider_id,
                    query_intent=query_intent,
                )
            else:
                # Pure vector search
                search_body = self._build_vector_query(
                    query_vector=query_vector,
                    k=k,
                    provider_id=provider_id,
                    query_intent=query_intent,
                )

            # Execute search
            response = await self.client.search(
                index=self.index_name,
                body=search_body,
            )

            # Parse results
            results = []
            for hit in response.get("hits", {}).get("hits", []):
                score = hit.get("_score", 0.0)

                # Filter by minimum score
                if score < min_score:
                    continue

                result = {
                    "id": hit["_source"].get("id"),
                    "score": score,
                    "nl_query": hit["_source"].get("nl_query"),
                    "generated_query": hit["_source"].get("generated_query"),
                    "provider_id": hit["_source"].get("provider_id"),
                    "status": hit["_source"].get("status"),
                    "is_good_example": hit["_source"].get("is_good_example"),
                    "involved_tables": hit["_source"].get("involved_tables", []),
                    "query_intent": hit["_source"].get("query_intent"),
                    "complexity_level": hit["_source"].get("complexity_level"),
                    "expert_corrected_query": hit["_source"].get("expert_corrected_query"),
                    "metadata": hit["_source"].get("metadata", {}),
                }
                results.append(result)

            logger.info(
                f"Found {len(results)} similar documents "
                f"(total hits: {response.get('hits', {}).get('total', {}).get('value', 0)})"
            )
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from the index.

        Args:
            doc_id: Document ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            Exception: If deletion fails
        """
        try:
            response = await self.client.delete(
                index=self.index_name,
                id=doc_id,
                refresh=True,
            )

            logger.info(f"Deleted document {doc_id} from '{self.index_name}'")
            return True

        except NotFoundError:
            logger.warning(f"Document {doc_id} not found in '{self.index_name}'")
            return False
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            raise

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector using AWS Bedrock Titan.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        try:
            # Prepare request body for Titan embeddings
            body = json.dumps({"inputText": text})

            # Invoke Bedrock model
            response = self.bedrock_runtime.invoke_model(
                modelId=self.embedding_model,
                contentType="application/json",
                accept="application/json",
                body=body,
            )

            # Parse response
            response_body = json.loads(response["body"].read())
            embedding = response_body.get("embedding")

            if not embedding:
                raise ValueError("No embedding returned from Bedrock")

            logger.debug(
                f"Generated embedding (dimension={len(embedding)}) "
                f"for text: '{text[:50]}...'"
            )
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def _build_vector_query(
        self,
        query_vector: List[float],
        k: int,
        provider_id: Optional[str] = None,
        query_intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build pure k-NN vector search query."""
        # Build filters
        filters = [
            {"term": {"status": "approved"}},
        ]

        if provider_id:
            filters.append({"term": {"provider_id": provider_id}})

        if query_intent:
            filters.append({"term": {"query_intent": query_intent}})

        query = {
            "size": k,
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_vector,
                                    "k": k,
                                }
                            }
                        }
                    ],
                    "filter": filters,
                }
            },
        }

        return query

    def _build_hybrid_query(
        self,
        query_vector: List[float],
        query_text: str,
        k: int,
        provider_id: Optional[str] = None,
        query_intent: Optional[str] = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Build hybrid search query combining vector and keyword search.

        Uses weighted combination of:
        - k-NN vector similarity
        - BM25 keyword matching
        """
        # Build filters
        filters = [
            {"term": {"status": "approved"}},
        ]

        if provider_id:
            filters.append({"term": {"provider_id": provider_id}})

        if query_intent:
            filters.append({"term": {"query_intent": query_intent}})

        # Hybrid query with script_score for weighted combination
        query = {
            "size": k,
            "query": {
                "script_score": {
                    "query": {
                        "bool": {
                            "should": [
                                {
                                    "match": {
                                        "nl_query": {
                                            "query": query_text,
                                            "boost": keyword_weight,
                                        }
                                    }
                                },
                            ],
                            "filter": filters,
                        }
                    },
                    "script": {
                        "source": f"""
                            float vectorScore = cosineSimilarity(params.query_vector, 'embedding') + 1.0;
                            float keywordScore = _score;
                            return {vector_weight} * vectorScore + {keyword_weight} * keywordScore;
                        """,
                        "params": {
                            "query_vector": query_vector,
                        },
                    },
                }
            },
        }

        return query

    async def close(self):
        """Close OpenSearch client connection."""
        if self.client:
            await self.client.close()
            logger.info("Closed OpenSearch client connection")
