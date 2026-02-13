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

    async def create_index_if_not_exists(self, index_name: str = None) -> bool:
        """
        Create OpenSearch index with k-NN settings and custom analyzers.

        Uses the multi-provider schema from opensearch-index-mapping.json design:
        - k-NN HNSW vector search (1024-dim, cosine similarity)
        - Custom analyzers for natural language and DSL queries
        - Provider-specific filtering fields
        - Quality tracking and usage analytics fields

        Args:
            index_name: Optional index name override (defaults to self.index_name)

        Returns:
            True if index was created, False if it already existed
        """
        target_index = index_name or self.index_name

        try:
            exists = await self.client.indices.exists(index=target_index)
            if exists:
                logger.info(f"Index '{target_index}' already exists")
                return False

            index_body = {
                "settings": {
                    "index": {
                        "number_of_shards": 2,
                        "number_of_replicas": 1,
                        "refresh_interval": "5s",
                        "max_result_window": 10000,
                        "knn": True,
                        "knn.algo_param.ef_search": 512,
                    },
                    "analysis": {
                        "analyzer": {
                            "natural_language_analyzer": {
                                "type": "standard",
                                "stopwords": "_english_",
                            },
                            "dsl_query_analyzer": {
                                "type": "custom",
                                "tokenizer": "whitespace",
                                "filter": ["lowercase"],
                            },
                        },
                    },
                },
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "provider_type": {"type": "keyword"},
                        "provider_id": {"type": "keyword"},
                        "natural_language_query": {
                            "type": "text",
                            "analyzer": "natural_language_analyzer",
                            "fields": {
                                "keyword": {"type": "keyword", "ignore_above": 256},
                            },
                        },
                        "dsl_query": {"type": "text", "index": False},
                        "dsl_query_analyzed": {
                            "type": "text",
                            "analyzer": "dsl_query_analyzer",
                        },
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
                        "embedding_model": {"type": "keyword"},
                        "query_intent": {"type": "keyword"},
                        "complexity_level": {"type": "keyword"},
                        "difficulty": {"type": "keyword"},
                        "involved_tables": {"type": "keyword"},
                        "involved_fields": {"type": "keyword"},
                        "is_good_example": {"type": "boolean"},
                        "status": {"type": "keyword"},
                        "reviewed_by": {"type": "keyword"},
                        "reviewed_at": {"type": "date"},
                        "expert_corrected_query": {"type": "text", "index": False},
                        "source": {"type": "keyword"},
                        "source_conversation_id": {"type": "keyword"},
                        "source_metadata": {
                            "type": "object",
                            "enabled": True,
                            "dynamic": True,
                        },
                        "usage_count": {"type": "integer"},
                        "success_rate": {"type": "float"},
                        "avg_similarity_score": {"type": "float"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                        "indexed_at": {"type": "date"},
                        # Legacy field aliases for backward compatibility
                        "nl_query": {
                            "type": "text",
                            "analyzer": "natural_language_analyzer",
                        },
                        "generated_query": {"type": "text", "index": False},
                        "metadata": {"type": "object", "enabled": False},
                    }
                },
            }

            await self.client.indices.create(index=target_index, body=index_body)

            logger.info(
                f"Created index '{target_index}' with k-NN + custom analyzers "
                f"(dimension={self.embedding_dimension})"
            )
            return True

        except RequestError as e:
            if "resource_already_exists_exception" in str(e):
                logger.info(f"Index '{target_index}' already exists")
                return False
            else:
                logger.error(f"Failed to create index: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error creating index: {e}")
            raise

    async def create_provider_index(self, provider_type: str) -> bool:
        """
        Create a provider-specific index using the naming convention from the design.

        Index names: text2dsl-samples-{sql,mongodb,splunk,custom-*}

        Args:
            provider_type: Provider type (sql, mongodb, splunk, or custom name)

        Returns:
            True if index was created, False if it already existed
        """
        index_name = f"text2dsl-samples-{provider_type.lower()}"
        return await self.create_index_if_not_exists(index_name=index_name)

    async def index_document(
        self,
        doc_id: str,
        vector: Optional[List[float]],
        metadata: Dict[str, Any],
    ) -> bool:
        """
        Index a document with its vector embedding and metadata.

        Supports both legacy field names (nl_query, generated_query) and
        new field names (natural_language_query, dsl_query) from the design.

        Args:
            doc_id: Document ID (usually RAGExample UUID)
            vector: Pre-computed embedding vector (optional)
            metadata: Document metadata

        Returns:
            True if successful
        """
        # Support both old and new field names
        nl_query = (
            metadata.get("natural_language_query")
            or metadata.get("nl_query")
        )
        if not nl_query:
            raise ValueError("natural_language_query or nl_query is required in metadata")

        dsl_query = (
            metadata.get("dsl_query")
            or metadata.get("generated_query")
        )

        # Generate embedding if not provided
        if vector is None:
            logger.debug(f"Generating embedding for document {doc_id}")
            vector = await self._generate_embedding(nl_query)

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()

        document = {
            "id": doc_id,
            "embedding": vector,
            "embedding_model": "titan-v2",
            # New schema fields
            "natural_language_query": nl_query,
            "dsl_query": dsl_query,
            "dsl_query_analyzed": dsl_query,
            "provider_type": metadata.get("provider_type", "sql"),
            "provider_id": metadata.get("provider_id"),
            "status": metadata.get("status", "approved"),
            "is_good_example": metadata.get("is_good_example", True),
            "involved_tables": metadata.get("involved_tables", []),
            "involved_fields": metadata.get("involved_fields", []),
            "query_intent": metadata.get("query_intent", "unknown"),
            "complexity_level": metadata.get("complexity_level", "medium"),
            "difficulty": metadata.get("difficulty", metadata.get("complexity_level", "medium")),
            "source": metadata.get("source", "user_generated"),
            "source_conversation_id": metadata.get("source_conversation_id"),
            "source_metadata": metadata.get("source_metadata", metadata.get("metadata", {})),
            "reviewed_by": metadata.get("reviewed_by"),
            "reviewed_at": metadata.get("reviewed_at"),
            "expert_corrected_query": metadata.get("expert_corrected_query"),
            "usage_count": metadata.get("usage_count", 0),
            "success_rate": metadata.get("success_rate"),
            "avg_similarity_score": metadata.get("avg_similarity_score"),
            "created_at": metadata.get("created_at", now),
            "updated_at": metadata.get("updated_at", now),
            "indexed_at": now,
            # Legacy aliases for backward compatibility
            "nl_query": nl_query,
            "generated_query": dsl_query,
            "metadata": metadata.get("metadata", {}),
        }

        try:
            response = await self.client.index(
                index=self.index_name,
                id=doc_id,
                body=document,
                refresh=True,
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
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using k-NN vector search.

        Supports:
        - Pure vector search (using query_vector)
        - Pure text search (using query_text with BM25)
        - Hybrid search (combining both with configurable weights)

        Args:
            query_vector: Query embedding vector (optional if query_text provided)
            query_text: Query text for keyword search (optional)
            k: Number of results to return
            provider_id: Filter by provider ID
            query_intent: Filter by query intent
            min_score: Minimum similarity score threshold
            hybrid: If True, use hybrid search combining vector + keyword
            vector_weight: Weight for semantic/embedding similarity (0.0-1.0)
            keyword_weight: Weight for BM25 keyword matching (0.0-1.0)

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
                    vector_weight=vector_weight,
                    keyword_weight=keyword_weight,
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

        Uses the script_score pattern (#6) from search-query-templates.json:
        - Weighted combination of cosine similarity + BM25
        - Searches across both natural_language_query and dsl_query_analyzed fields
        - Intent-based dynamic weighting per embedding-strategy.md:
          - aggregation: 0.8 vector / 0.2 keyword
          - filter/exact: 0.5 vector / 0.5 keyword
          - join/complex: 0.7 vector / 0.3 keyword
          - Default: 0.7 vector / 0.3 keyword
        """
        # Intent-based dynamic weighting from embedding-strategy.md
        # Only apply intent defaults when caller uses default weights (0.7/0.3)
        intent_weights = {
            "aggregation": (0.8, 0.2),
            "filter": (0.5, 0.5),
            "exact": (0.5, 0.5),
            "join": (0.7, 0.3),
            "complex": (0.7, 0.3),
        }

        caller_used_defaults = (vector_weight == 0.7 and keyword_weight == 0.3)
        if query_intent and query_intent in intent_weights and caller_used_defaults:
            vector_weight, keyword_weight = intent_weights[query_intent]

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
                "script_score": {
                    "query": {
                        "bool": {
                            "should": [
                                {
                                    "match": {
                                        "natural_language_query": {
                                            "query": query_text,
                                            "boost": 0.3,
                                        }
                                    }
                                },
                                {
                                    "match": {
                                        "nl_query": {
                                            "query": query_text,
                                            "boost": 0.2,
                                        }
                                    }
                                },
                                {
                                    "match": {
                                        "dsl_query_analyzed": {
                                            "query": query_text,
                                            "boost": 0.1,
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
