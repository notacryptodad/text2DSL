#!/usr/bin/env python3
"""
Script to index sample queries into OpenSearch with embeddings and metadata.

This script:
1. Loads sample queries from a JSON/YAML file or database
2. Generates embeddings for each natural_language_query using Bedrock Titan
3. Classifies query_intent and complexity_level
4. Bulk indexes to OpenSearch using the new multi-provider schema
5. Supports dry-run mode for validation

Usage:
    python scripts/index_sample_queries.py --provider-type sql --source-file data/sample_queries.json
    python scripts/index_sample_queries.py --dry-run
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import boto3
import yaml
from opensearchpy import AsyncOpenSearch, RequestError, helpers

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class QueryClassifier:
    """Classifies queries by intent and complexity."""

    # SQL keyword patterns for intent classification
    INTENT_PATTERNS = {
        "aggregation": r"\b(COUNT|SUM|AVG|MAX|MIN|GROUP BY)\b",
        "join": r"\b(JOIN|INNER JOIN|LEFT JOIN|RIGHT JOIN|OUTER JOIN)\b",
        "filter": r"\b(WHERE|HAVING)\b",
        "sort": r"\b(ORDER BY)\b",
        "subquery": r"\(SELECT\b",
        "window": r"\b(OVER|PARTITION BY|ROW_NUMBER|RANK)\b",
        "insert": r"\b(INSERT INTO)\b",
        "update": r"\b(UPDATE)\b",
        "delete": r"\b(DELETE FROM)\b",
    }

    @classmethod
    def classify_intent(cls, dsl_query: str) -> str:
        """
        Classify the query intent based on SQL keywords.
        Returns the primary intent (aggregation, join, filter, sort, etc.).
        """
        query_upper = dsl_query.upper()

        # Check for multiple intents and prioritize
        matched_intents = []
        for intent, pattern in cls.INTENT_PATTERNS.items():
            if re.search(pattern, query_upper):
                matched_intents.append(intent)

        if not matched_intents:
            return "simple_select"

        # Priority order: window > subquery > aggregation > join > filter > sort
        priority = ["window", "subquery", "aggregation", "join", "filter", "sort", "insert", "update", "delete"]
        for intent in priority:
            if intent in matched_intents:
                return intent

        return matched_intents[0]

    @classmethod
    def classify_complexity(cls, dsl_query: str) -> str:
        """
        Classify query complexity based on structure.
        Returns: simple, medium, or complex.
        """
        query_upper = dsl_query.upper()

        # Complexity indicators
        has_join = bool(re.search(r"\bJOIN\b", query_upper))
        has_subquery = bool(re.search(r"\(SELECT\b", query_upper))
        has_aggregation = bool(re.search(r"\b(GROUP BY|HAVING)\b", query_upper))
        has_window = bool(re.search(r"\b(OVER|PARTITION BY)\b", query_upper))
        num_tables = len(re.findall(r"\bFROM\b|\bJOIN\b", query_upper))

        # Complex queries
        if has_window or has_subquery or (has_join and has_aggregation) or num_tables > 2:
            return "complex"

        # Medium queries
        if has_join or has_aggregation or num_tables > 1:
            return "medium"

        # Simple queries
        return "simple"

    @classmethod
    def extract_tables(cls, dsl_query: str) -> List[str]:
        """Extract table names from SQL query."""
        # Pattern to match table names after FROM and JOIN
        pattern = r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
        matches = re.findall(pattern, dsl_query, re.IGNORECASE)
        return list(set(matches)) if matches else ["unknown"]

    @classmethod
    def extract_fields(cls, dsl_query: str) -> List[str]:
        """Extract field names from SELECT clause."""
        # Simple extraction of fields from SELECT
        select_match = re.search(r"SELECT\s+(.*?)\s+FROM", dsl_query, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return []

        select_clause = select_match.group(1)

        # Handle SELECT *
        if "*" in select_clause:
            return ["*"]

        # Extract field names (basic pattern)
        fields = []
        for part in select_clause.split(","):
            part = part.strip()
            # Handle aliases (AS)
            if " AS " in part.upper():
                part = part.split(" AS ")[0].strip()
            # Handle functions
            if "(" in part:
                continue  # Skip aggregate functions for now
            # Extract field name
            if "." in part:
                fields.append(part.split(".")[-1].strip())
            else:
                fields.append(part.strip())

        return fields[:10] if fields else []  # Limit to 10 fields


class SampleQueryIndexer:
    """Handles indexing of sample queries into OpenSearch with embeddings."""

    def __init__(
        self,
        opensearch_host: str = "localhost",
        opensearch_port: int = 9200,
        provider_type: str = "sql",
        provider_id: str = "default",
        aws_region: str = "us-east-1",
        embedding_model: str = "amazon.titan-embed-text-v2:0",
        dry_run: bool = False,
    ):
        """Initialize the indexer."""
        self.provider_type = provider_type
        self.provider_id = provider_id
        self.index_name = f"text2dsl-samples-{provider_type}"
        self.embedding_model = embedding_model
        self.embedding_dimension = 1024  # Titan v2 dimension
        self.dry_run = dry_run

        # Create OpenSearch client
        self.client = AsyncOpenSearch(
            hosts=[{"host": opensearch_host, "port": opensearch_port}],
            http_auth=None,  # No auth for local instance
            use_ssl=False,
            verify_certs=False,
            timeout=30,
        )

        # Create Bedrock client for embeddings
        if not dry_run:
            self.bedrock_runtime = boto3.client(
                service_name="bedrock-runtime",
                region_name=aws_region,
            )
        else:
            self.bedrock_runtime = None

        logger.info(
            f"Initialized indexer for index '{self.index_name}' at {opensearch_host}:{opensearch_port}"
        )
        if dry_run:
            logger.info("DRY RUN MODE: No data will be written to OpenSearch or Bedrock")

    async def create_index(self) -> bool:
        """Create the OpenSearch index with the new multi-provider schema."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create index '{self.index_name}'")
            return True

        try:
            # Check if index exists
            exists = await self.client.indices.exists(index=self.index_name)

            if exists:
                logger.info(f"Index '{self.index_name}' already exists")
                return False

            # Load mapping from design document
            mapping_file = Path(__file__).parent.parent / "docs" / "opensearch-dsl-design" / "opensearch-index-mapping.json"

            if mapping_file.exists():
                with open(mapping_file, "r") as f:
                    index_body = json.load(f)
                logger.info(f"Loaded index mapping from {mapping_file}")
            else:
                # Fallback to inline mapping if file not found
                logger.warning(f"Mapping file not found at {mapping_file}, using inline mapping")
                index_body = self._get_default_mapping()

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

    def _get_default_mapping(self) -> Dict[str, Any]:
        """Get default index mapping if file not found."""
        return {
            "settings": {
                "index": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1,
                    "refresh_interval": "5s",
                    "knn": True,
                    "knn.algo_param.ef_search": 512,
                },
                "analysis": {
                    "analyzer": {
                        "natural_language_analyzer": {
                            "type": "standard",
                            "stopwords": "_english_"
                        },
                        "dsl_query_analyzer": {
                            "type": "custom",
                            "tokenizer": "whitespace",
                            "filter": ["lowercase"]
                        }
                    }
                }
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
                            "keyword": {"type": "keyword", "ignore_above": 256}
                        }
                    },
                    "dsl_query": {"type": "text", "index": False},
                    "dsl_query_analyzed": {
                        "type": "text",
                        "analyzer": "dsl_query_analyzer"
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
                    "source": {"type": "keyword"},
                    "usage_count": {"type": "integer"},
                    "success_rate": {"type": "float"},
                    "avg_similarity_score": {"type": "float"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "indexed_at": {"type": "date"},
                }
            },
        }

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector using AWS Bedrock Titan."""
        if self.dry_run:
            # Return dummy embedding for dry run
            return [0.0] * self.embedding_dimension

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

    async def prepare_document(
        self, query_id: str, query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare a document for indexing with embeddings and metadata."""
        # Support both old and new field names
        natural_language_query = query.get("natural_language_query") or query.get("question")
        dsl_query = query.get("dsl_query") or query.get("sql")

        if not natural_language_query or not dsl_query:
            raise ValueError(f"Query {query_id} missing required fields")

        # Generate embedding
        embedding = await self.generate_embedding(natural_language_query)

        # Classify query
        query_intent = QueryClassifier.classify_intent(dsl_query)
        complexity_level = QueryClassifier.classify_complexity(dsl_query)
        involved_tables = QueryClassifier.extract_tables(dsl_query)
        involved_fields = QueryClassifier.extract_fields(dsl_query)

        # Prepare document with new schema
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        document = {
            "id": query_id,
            "provider_type": self.provider_type,
            "provider_id": self.provider_id,
            "natural_language_query": natural_language_query,
            "dsl_query": dsl_query,
            "dsl_query_analyzed": dsl_query,
            "embedding": embedding,
            "embedding_model": self.embedding_model,
            "query_intent": query_intent,
            "complexity_level": complexity_level,
            "difficulty": query.get("difficulty") or complexity_level,  # Backward compatibility
            "involved_tables": involved_tables,
            "involved_fields": involved_fields,
            "is_good_example": query.get("is_good_example", True),
            "status": query.get("status", "approved"),
            "source": query.get("source", "sample"),
            "usage_count": query.get("usage_count", 0),
            "success_rate": query.get("success_rate", 1.0),
            "avg_similarity_score": query.get("avg_similarity_score", 0.0),
            "created_at": query.get("created_at", now),
            "updated_at": now,
            "indexed_at": now,
        }

        return document

    async def bulk_index_queries(self, queries: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Bulk index all queries with embeddings."""
        logger.info(f"Processing {len(queries)} queries for bulk indexing...")

        if self.dry_run:
            logger.info("[DRY RUN] Processing queries without indexing:")
            for idx, query in enumerate(queries):
                query_id = f"sample_{idx + 1}"
                doc = await self.prepare_document(query_id, query)
                logger.info(
                    f"  [{query_id}] {doc['natural_language_query'][:60]}... "
                    f"(intent={doc['query_intent']}, complexity={doc['complexity_level']})"
                )
            return len(queries), 0

        # Prepare all documents with embeddings
        actions = []
        failed_count = 0

        for idx, query in enumerate(queries):
            query_id = f"sample_{idx + 1}"

            try:
                document = await self.prepare_document(query_id, query)

                # Prepare bulk action
                action = {
                    "_index": self.index_name,
                    "_id": query_id,
                    "_source": document,
                }
                actions.append(action)

                # Progress update
                if (idx + 1) % 10 == 0:
                    logger.info(
                        f"Progress: {idx + 1}/{len(queries)} queries prepared "
                        f"(intent={document['query_intent']}, complexity={document['complexity_level']})"
                    )

            except Exception as e:
                logger.error(f"Error preparing query {query_id}: {e}")
                failed_count += 1
                continue

        # Bulk index all documents
        if actions:
            logger.info(f"Bulk indexing {len(actions)} documents...")
            success, failed = await helpers.async_bulk(
                self.client,
                actions,
                chunk_size=100,
                raise_on_error=False,
            )

            # Refresh index to make documents searchable
            await self.client.indices.refresh(index=self.index_name)

            logger.info(
                f"Bulk indexing complete: {success} succeeded, {len(failed)} failed"
            )
            return success, len(failed) + failed_count
        else:
            logger.warning("No documents to index")
            return 0, failed_count

    async def close(self):
        """Close OpenSearch client connection."""
        if self.client:
            await self.client.close()
            logger.info("Closed OpenSearch client connection")


def load_sample_queries(file_path: str) -> List[Dict[str, Any]]:
    """Load sample queries from JSON or YAML file."""
    try:
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            raise FileNotFoundError(f"Sample queries file not found: {file_path}")

        with open(file_path, 'r') as f:
            # Detect file format
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                queries = yaml.safe_load(f)
            elif file_path.endswith('.json'):
                queries = json.load(f)
            else:
                # Try JSON first, then YAML
                try:
                    f.seek(0)
                    queries = json.load(f)
                except json.JSONDecodeError:
                    f.seek(0)
                    queries = yaml.safe_load(f)

        if not isinstance(queries, list):
            raise ValueError("Sample queries file must contain a list of queries")

        logger.info(f"Loaded {len(queries)} sample queries from {file_path}")
        return queries

    except FileNotFoundError:
        logger.error(f"Sample queries file not found: {file_path}")
        raise
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        logger.error(f"Invalid format in sample queries file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading sample queries: {e}")
        raise


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Index sample queries into OpenSearch with embeddings and metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Index SQL queries from default file
  python scripts/index_sample_queries.py --provider-type sql

  # Index from custom file
  python scripts/index_sample_queries.py --provider-type sql --source-file data/sample_queries.json

  # Dry run to validate without indexing
  python scripts/index_sample_queries.py --dry-run

  # Index MongoDB queries
  python scripts/index_sample_queries.py --provider-type mongodb --source-file data/mongodb_queries.json
        """
    )

    parser.add_argument(
        "--provider-type",
        type=str,
        default="sql",
        choices=["sql", "mongodb", "splunk", "elasticsearch"],
        help="Provider type (default: sql)"
    )

    parser.add_argument(
        "--provider-id",
        type=str,
        default="default",
        help="Provider instance ID (default: default)"
    )

    parser.add_argument(
        "--source-file",
        type=str,
        help="Path to sample queries JSON/YAML file (default: data/sample_queries.json or tests/fixtures/sample_queries.json)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate queries without indexing to OpenSearch or calling Bedrock"
    )

    parser.add_argument(
        "--opensearch-host",
        type=str,
        default=os.getenv("OPENSEARCH_HOST", "localhost"),
        help="OpenSearch host (default: localhost)"
    )

    parser.add_argument(
        "--opensearch-port",
        type=int,
        default=int(os.getenv("OPENSEARCH_PORT", "9200")),
        help="OpenSearch port (default: 9200)"
    )

    parser.add_argument(
        "--aws-region",
        type=str,
        default=os.getenv("AWS_REGION", "us-east-1"),
        help="AWS region for Bedrock (default: us-east-1)"
    )

    parser.add_argument(
        "--embedding-model",
        type=str,
        default="amazon.titan-embed-text-v2:0",
        help="Bedrock embedding model ID (default: amazon.titan-embed-text-v2:0)"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


async def main():
    """Main entry point for the indexing script."""
    args = parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine source file
    project_root = Path(__file__).parent.parent

    if args.source_file:
        queries_file = Path(args.source_file)
    else:
        # Try data/sample_queries.json first, then tests/fixtures/sample_queries.json
        queries_file = project_root / "data" / "sample_queries.json"
        if not queries_file.exists():
            queries_file = project_root / "tests" / "fixtures" / "sample_queries.json"

    logger.info("=" * 70)
    logger.info("OpenSearch Sample Queries Indexer (Multi-Provider RAG)")
    logger.info("=" * 70)
    logger.info(f"Provider Type: {args.provider_type}")
    logger.info(f"Provider ID: {args.provider_id}")
    logger.info(f"Index Name: text2dsl-samples-{args.provider_type}")
    logger.info(f"OpenSearch: {args.opensearch_host}:{args.opensearch_port}")
    logger.info(f"AWS Region: {args.aws_region}")
    logger.info(f"Embedding Model: {args.embedding_model}")
    logger.info(f"Queries File: {queries_file}")
    logger.info(f"Dry Run: {args.dry_run}")
    logger.info("=" * 70)

    try:
        # Load sample queries
        queries = load_sample_queries(str(queries_file))

        # Create indexer
        indexer = SampleQueryIndexer(
            opensearch_host=args.opensearch_host,
            opensearch_port=args.opensearch_port,
            provider_type=args.provider_type,
            provider_id=args.provider_id,
            aws_region=args.aws_region,
            embedding_model=args.embedding_model,
            dry_run=args.dry_run,
        )

        try:
            # Create index
            if not args.dry_run:
                logger.info("Creating index (if not exists)...")
                await indexer.create_index()

            # Bulk index all queries
            logger.info("Starting bulk indexing process...")
            success_count, failed_count = await indexer.bulk_index_queries(queries)

            logger.info("=" * 70)
            if args.dry_run:
                logger.info(f"DRY RUN: Validated {success_count} queries")
            else:
                logger.info(f"Successfully indexed {success_count} queries!")
                if failed_count > 0:
                    logger.warning(f"Failed to index {failed_count} queries")
            logger.info("=" * 70)

            return 0 if failed_count == 0 else 1

        finally:
            await indexer.close()

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        logger.info("Please create the sample queries file or specify --source-file")
        return 1
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
