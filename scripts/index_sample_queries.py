#!/usr/bin/env python3
"""
Script to index sample queries from tests/fixtures/sample_queries.json into OpenSearch.

This script:
1. Loads sample queries from the fixture file
2. Creates the OpenSearch index if it doesn't exist
3. Generates embeddings using Bedrock Titan
4. Indexes all queries into OpenSearch for RAG retrieval

Usage:
    python scripts/index_sample_queries.py
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import boto3
from opensearchpy import AsyncOpenSearch, RequestError

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SampleQueryIndexer:
    """Handles indexing of sample queries into OpenSearch."""

    def __init__(
        self,
        opensearch_host: str = "localhost",
        opensearch_port: int = 9200,
        index_name: str = "text2dsl-queries",
        aws_region: str = "us-east-1",
        embedding_model: str = "amazon.titan-embed-text-v2:0",
    ):
        """Initialize the indexer."""
        self.index_name = index_name
        self.embedding_model = embedding_model
        self.embedding_dimension = 1024  # Titan v2 dimension

        # Create OpenSearch client
        self.client = AsyncOpenSearch(
            hosts=[{"host": opensearch_host, "port": opensearch_port}],
            http_auth=None,  # No auth for local instance
            use_ssl=False,
            verify_certs=False,
            timeout=30,
        )

        # Create Bedrock client for embeddings
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=aws_region,
        )

        logger.info(
            f"Initialized indexer for index '{index_name}' at {opensearch_host}:{opensearch_port}"
        )

    async def create_index(self) -> bool:
        """Create the OpenSearch index with k-NN configuration."""
        try:
            # Check if index exists
            exists = await self.client.indices.exists(index=self.index_name)

            if exists:
                logger.info(f"Index '{self.index_name}' already exists")
                return False

            # Define index mapping with k-NN support
            index_body = {
                "settings": {
                    "index": {
                        "knn": True,
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
                        "question": {
                            "type": "text",
                            "analyzer": "standard",
                        },
                        "sql": {
                            "type": "text",
                            "index": False,
                        },
                        "difficulty": {"type": "keyword"},
                        "created_at": {"type": "date"},
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

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector using AWS Bedrock Titan."""
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
                f"Generated embedding (dimension={len(embedding)}) for text: '{text[:50]}...'"
            )
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def index_query(self, query_id: str, query: Dict[str, Any]) -> bool:
        """Index a single query with its embedding."""
        try:
            # Generate embedding from question
            question = query["question"]
            embedding = await self.generate_embedding(question)

            # Prepare document
            document = {
                "id": query_id,
                "embedding": embedding,
                "question": question,
                "sql": query["sql"],
                "difficulty": query.get("difficulty", "medium"),
                "created_at": "2024-01-01T00:00:00Z",
            }

            # Index document
            response = await self.client.index(
                index=self.index_name,
                id=query_id,
                body=document,
                refresh=False,  # Don't refresh immediately for bulk operations
            )

            logger.debug(
                f"Indexed query {query_id}: '{question[:50]}...' "
                f"(result: {response.get('result')})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to index query {query_id}: {e}")
            return False

    async def index_all_queries(self, queries: List[Dict[str, Any]]) -> int:
        """Index all queries from the list."""
        logger.info(f"Indexing {len(queries)} queries...")

        indexed_count = 0
        failed_count = 0

        for idx, query in enumerate(queries):
            query_id = f"sample_{idx + 1}"

            try:
                success = await self.index_query(query_id, query)
                if success:
                    indexed_count += 1
                else:
                    failed_count += 1

                # Progress update every 5 queries
                if (idx + 1) % 5 == 0:
                    logger.info(f"Progress: {idx + 1}/{len(queries)} queries processed")

            except Exception as e:
                logger.error(f"Error processing query {idx + 1}: {e}")
                failed_count += 1

        # Refresh index to make all documents searchable
        await self.client.indices.refresh(index=self.index_name)

        logger.info(
            f"Indexing complete: {indexed_count} succeeded, {failed_count} failed"
        )
        return indexed_count

    async def close(self):
        """Close OpenSearch client connection."""
        if self.client:
            await self.client.close()
            logger.info("Closed OpenSearch client connection")


def load_sample_queries(file_path: str) -> List[Dict[str, Any]]:
    """Load sample queries from JSON file."""
    try:
        with open(file_path, 'r') as f:
            queries = json.load(f)

        logger.info(f"Loaded {len(queries)} sample queries from {file_path}")
        return queries

    except FileNotFoundError:
        logger.error(f"Sample queries file not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in sample queries file: {e}")
        raise


async def main():
    """Main entry point for the indexing script."""
    # Configuration from environment or defaults
    opensearch_host = os.getenv("OPENSEARCH_HOST", "localhost")
    opensearch_port = int(os.getenv("OPENSEARCH_PORT", "9200"))
    index_name = os.getenv("OPENSEARCH_INDEX", "text2dsl-queries")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    # Path to sample queries file
    project_root = Path(__file__).parent.parent
    queries_file = project_root / "tests" / "fixtures" / "sample_queries.json"

    logger.info("=" * 60)
    logger.info("OpenSearch Sample Queries Indexer")
    logger.info("=" * 60)
    logger.info(f"OpenSearch: {opensearch_host}:{opensearch_port}")
    logger.info(f"Index: {index_name}")
    logger.info(f"AWS Region: {aws_region}")
    logger.info(f"Queries file: {queries_file}")
    logger.info("=" * 60)

    try:
        # Load sample queries
        queries = load_sample_queries(str(queries_file))

        # Create indexer
        indexer = SampleQueryIndexer(
            opensearch_host=opensearch_host,
            opensearch_port=opensearch_port,
            index_name=index_name,
            aws_region=aws_region,
        )

        try:
            # Create index
            logger.info("Creating index...")
            await indexer.create_index()

            # Index all queries
            logger.info("Starting indexing process...")
            indexed_count = await indexer.index_all_queries(queries)

            logger.info("=" * 60)
            logger.info(f"Successfully indexed {indexed_count} queries!")
            logger.info("=" * 60)

            return 0

        finally:
            await indexer.close()

    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
