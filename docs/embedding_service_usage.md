# Bedrock Titan Embedding Service Usage

## Overview

The `BedrockEmbeddingService` provides vector embeddings for RAG (Retrieval Augmented Generation) using AWS Bedrock Titan models.

## Features

- **Asynchronous API**: All operations are async for optimal performance
- **Batch Processing**: Efficiently embed multiple texts in parallel
- **Automatic Retries**: Built-in retry logic with exponential backoff for rate limiting
- **Error Handling**: Graceful fallback for failed embeddings
- **Caching**: Singleton pattern for client reuse

## Configuration

Add to your `.env` file or set as environment variables:

```bash
BEDROCK_REGION=us-east-1
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_EMBEDDING_BATCH_SIZE=25

# Optional: If not using instance role
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

## Basic Usage

### Single Text Embedding

```python
from text2x.services.embedding_service import get_embedding_service
from text2x.config import get_settings

# Get settings
settings = get_settings()

# Create or get cached service
service = get_embedding_service(
    region=settings.bedrock_region,
    model_id=settings.bedrock_embedding_model
)

# Generate embedding
query = "What is the total revenue for Q1 2024?"
embedding = await service.embed_text(query)

# embedding is a List[float] with 1024 dimensions (Titan v2)
print(f"Embedding dimensions: {len(embedding)}")
```

### Batch Embedding

```python
# Embed multiple texts efficiently
texts = [
    "What is the total revenue?",
    "How many customers do we have?",
    "Show me the top products",
    # ... more texts
]

embeddings = await service.embed_batch(texts, show_progress=True)

# Returns List[List[float]] in same order as input
for text, embedding in zip(texts, embeddings):
    print(f"Text: {text[:30]}... -> Embedding: {len(embedding)} dims")
```

## Integration with RAG Retrieval Agent

The RAG retrieval agent automatically uses the embedding service when provided:

```python
from text2x.agents.rag_retrieval import RAGRetrievalAgent
from text2x.agents.base import LLMConfig
from text2x.services.embedding_service import get_embedding_service
from text2x.config import get_settings

# Initialize components
settings = get_settings()
llm_config = LLMConfig(
    provider="bedrock",
    model_name=settings.llm_model,
    temperature=0.0
)

# Create embedding service
embedding_service = get_embedding_service(
    region=settings.bedrock_region,
    model_id=settings.bedrock_embedding_model
)

# Create RAG agent with embedding service
rag_agent = RAGRetrievalAgent(
    llm_config=llm_config,
    opensearch_client=opensearch_client,
    provider_id="my-provider-id",
    embedding_service=embedding_service,  # Pass embedding service
    top_k=5
)

# Use the agent
result = await rag_agent.process({
    "user_query": "What is the total revenue?",
    "schema_context": schema_context
})

# Agent will use Bedrock embeddings for semantic search
examples = result["examples"]
```

## Models

### Amazon Titan Embed Text v2 (Recommended)

- **Model ID**: `amazon.titan-embed-text-v2:0`
- **Dimensions**: 1024
- **Max Input**: 8,192 tokens (~30,000 characters)
- **Features**: Normalized embeddings, configurable dimensions

### Amazon Titan Embed Text v1 (Legacy)

- **Model ID**: `amazon.titan-embed-text-v1`
- **Dimensions**: 1536
- **Max Input**: 8,192 tokens

## Error Handling

The service automatically handles common errors:

```python
try:
    embedding = await service.embed_text(long_text)
except ValueError as e:
    # Empty text or invalid input
    print(f"Input error: {e}")
except ClientError as e:
    # AWS API error (after retries)
    print(f"Bedrock error: {e}")
```

For batch operations, failed embeddings are replaced with zero vectors:

```python
embeddings = await service.embed_batch(texts)

# Check for failed embeddings (all zeros)
for i, emb in enumerate(embeddings):
    if all(x == 0.0 for x in emb):
        print(f"Text {i} failed to embed")
```

## Rate Limiting

The service automatically handles rate limiting:

- **Retries**: Up to 3 attempts with exponential backoff
- **Batch Delay**: 100ms pause between batches
- **Concurrent Requests**: Processed in parallel within batch size limit

## Testing

Run the comprehensive test suite:

```bash
# Run all embedding service tests
pytest tests/test_embedding_service.py -v

# Run specific test
pytest tests/test_embedding_service.py::test_embed_batch_success -v
```

## Performance

Typical performance metrics:

- **Single embedding**: ~100-200ms
- **Batch (25 texts)**: ~2-3 seconds
- **Throughput**: ~10-15 texts/second

## Fallback Mode

If the embedding service is not configured, the RAG agent falls back to mock embeddings:

```python
# Agent without embedding service
rag_agent = RAGRetrievalAgent(
    llm_config=llm_config,
    opensearch_client=opensearch_client,
    provider_id="my-provider-id",
    # embedding_service=None  # Will use mock embeddings
)

# Warning will be logged:
# "Using mock embedding - configure BedrockEmbeddingService for production"
```

## AWS Permissions

Required IAM permissions for Bedrock:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-*"
      ]
    }
  ]
}
```

## Troubleshooting

### Import Error

```bash
pip install tenacity boto3
```

### Region Not Supported

Check if Bedrock is available in your region:
- Use `us-east-1` or `us-west-2` for best availability

### Rate Limiting

If you're hitting rate limits frequently:
- Reduce `bedrock_embedding_batch_size`
- Add delays between API calls
- Request quota increase from AWS

## References

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Titan Embedding Models](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- [RAG Retrieval Agent](../src/text2x/agents/rag_retrieval.py)
