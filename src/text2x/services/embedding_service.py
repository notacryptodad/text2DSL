"""Bedrock Titan Embedding Service for RAG"""
import asyncio
import json
import logging
import time
from typing import List, Optional
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class BedrockEmbeddingService:
    """
    Service for generating embeddings using AWS Bedrock Titan models.

    Features:
    - Asynchronous embedding generation
    - Batch processing support
    - Automatic rate limiting and retries
    - Error handling for AWS service issues

    Model: amazon.titan-embed-text-v2:0 (1024 dimensions)
    Fallback: amazon.titan-embed-text-v1 (1536 dimensions)
    """

    def __init__(
        self,
        region: str = "us-east-1",
        model_id: str = "amazon.titan-embed-text-v2:0",
        max_batch_size: int = 25,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """
        Initialize Bedrock embedding service.

        Args:
            region: AWS region for Bedrock service
            model_id: Bedrock embedding model ID
            max_batch_size: Maximum texts to embed in one batch
            aws_access_key_id: Optional AWS access key (uses instance role if not provided)
            aws_secret_access_key: Optional AWS secret key (uses instance role if not provided)
        """
        self.region = region
        self.model_id = model_id
        self.max_batch_size = max_batch_size

        # Initialize Bedrock runtime client using boto3 session pattern
        # This matches the credential pattern from src/text2x/llm/__init__.py
        try:
            session = boto3.Session(region_name=region)

            # If explicit credentials provided, use them
            if aws_access_key_id and aws_secret_access_key:
                session = boto3.Session(
                    region_name=region,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key
                )

            # Get credentials from session (either explicit or from instance role)
            creds = session.get_credentials()
            if not creds:
                raise ValueError(
                    "Failed to obtain AWS credentials. Ensure IAM role is attached "
                    "or AWS credentials are configured."
                )

            self.client = session.client("bedrock-runtime")

            logger.info(
                f"BedrockEmbeddingService initialized with model={model_id}, "
                f"region={region}, max_batch_size={max_batch_size}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise

    @retry(
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed (max 8192 tokens for Titan v2)

        Returns:
            Embedding vector (1024 dimensions for v2, 1536 for v1)

        Raises:
            ClientError: If AWS API call fails
            ValueError: If text is empty or too long
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Truncate if too long (approximate token limit)
        max_chars = 30000  # ~8000 tokens
        if len(text) > max_chars:
            logger.warning(f"Text truncated from {len(text)} to {max_chars} chars")
            text = text[:max_chars]

        try:
            # Run synchronous boto3 call in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                self._invoke_bedrock_sync,
                text
            )

            return embedding

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Bedrock API error ({error_code}): {e}")
            raise
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def _invoke_bedrock_sync(self, text: str) -> List[float]:
        """
        Synchronous Bedrock invocation (runs in thread pool).

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Prepare request body based on model version
        if "v2" in self.model_id:
            # Titan v2 format
            request_body = {
                "inputText": text,
                "dimensions": 1024,
                "normalize": True
            }
        else:
            # Titan v1 format
            request_body = {
                "inputText": text
            }

        # Invoke Bedrock model
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )

        # Parse response
        response_body = json.loads(response["body"].read())
        embedding = response_body.get("embedding")

        if not embedding:
            raise ValueError("No embedding returned from Bedrock")

        return embedding

    async def embed_batch(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in parallel.

        Args:
            texts: List of texts to embed
            show_progress: Whether to log progress (useful for large batches)

        Returns:
            List of embedding vectors in same order as input texts

        Raises:
            ValueError: If texts list is empty
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        logger.info(f"Embedding batch of {len(texts)} texts")
        start_time = time.time()

        # Process in chunks to respect rate limits
        embeddings = []
        total_batches = (len(texts) + self.max_batch_size - 1) // self.max_batch_size

        for i in range(0, len(texts), self.max_batch_size):
            batch = texts[i:i + self.max_batch_size]
            batch_num = i // self.max_batch_size + 1

            if show_progress:
                logger.info(f"Processing batch {batch_num}/{total_batches}")

            # Create tasks for parallel processing within batch
            tasks = [self.embed_text(text) for text in batch]
            batch_embeddings = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any errors in the batch
            for idx, result in enumerate(batch_embeddings):
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to embed text {i + idx}: {result}. "
                        "Returning zero vector."
                    )
                    # Return zero vector as fallback
                    dimension = 1024 if "v2" in self.model_id else 1536
                    embeddings.append([0.0] * dimension)
                else:
                    embeddings.append(result)

            # Rate limiting: small delay between batches
            if i + self.max_batch_size < len(texts):
                await asyncio.sleep(0.1)

        duration = time.time() - start_time
        logger.info(
            f"Embedded {len(texts)} texts in {duration:.2f}s "
            f"({len(texts)/duration:.1f} texts/s)"
        )

        return embeddings


@lru_cache(maxsize=1)
def get_embedding_service(
    region: str = "us-east-1",
    model_id: str = "amazon.titan-embed-text-v2:0",
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
) -> BedrockEmbeddingService:
    """
    Get or create a cached embedding service instance.

    This ensures we reuse the Bedrock client across requests.

    Args:
        region: AWS region
        model_id: Bedrock model ID
        aws_access_key_id: Optional AWS access key
        aws_secret_access_key: Optional AWS secret key

    Returns:
        Cached BedrockEmbeddingService instance
    """
    return BedrockEmbeddingService(
        region=region,
        model_id=model_id,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
