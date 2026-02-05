# Nvidia NIM Configuration Guide

## Overview

The Text2DSL codebase has been updated to support Nvidia NIM models through LiteLLM. This allows you to use models like `minimax-m2.1` hosted on Nvidia's API.

## Changes Made

### 1. Environment Configuration (`.env`)

Updated the LLM configuration to use Nvidia NIM:

```bash
# LLM Configuration
LLM_PROVIDER=nvidia_nim
LLM_MODEL=nvidia_nim/minimaxai/minimax-m2.1
LLM_API_BASE=https://integrate.api.nvidia.com/v1
LLM_API_KEY=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
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=4096
LLM_TIMEOUT=120
```

### 2. Code Modifications

#### `src/text2x/llm/litellm_client.py`
- Added `api_base` and `api_key` parameters to `LiteLLMClient.__init__()`
- Modified credential handling to only call AWS credential setup for Bedrock models
- Updated `complete()` and `acomplete()` methods to pass API credentials for non-Bedrock providers
- Updated `get_client()` function signature

#### `src/text2x/agents/base.py`
- Updated `LiteLLMAdapter` to accept and pass `api_base` and `api_key` from config
- Modified model prefix detection to support `nvidia_nim/`, `openai/`, `anthropic/` prefixes

#### `src/text2x/agentcore/config.py`
- Added `api_base` and `api_key` fields to `AgentCoreConfig`
- Updated `from_env()` to read `LLM_API_BASE` and `LLM_API_KEY` from environment

#### `src/text2x/agentcore/llm/client.py`
- Updated `LLMClient.__init__()` to pass `api_base` and `api_key` to `LiteLLMClient`

## Testing

Run the test script to verify the configuration:

```bash
python test_nvidia_nim.py
```

Expected output:
```
Testing Nvidia NIM configuration:
  Model: nvidia_nim/minimaxai/minimax-m2.1
  API Base: https://integrate.api.nvidia.com/v1
  API Key: ********************

Sending test request...

✅ SUCCESS!
Response: Hello from Nvidia NIM!
Model: nvidia_nim/minimaxai/minimax-m2.1
Tokens: 15
```

## Usage

### Starting the Application

```bash
# Start infrastructure
./manage.sh start infra

# Start backend (will use Nvidia NIM model)
./manage.sh start backend

# Start frontend
./manage.sh start frontend
```

### Switching Back to Bedrock

To switch back to AWS Bedrock, update `.env`:

```bash
LLM_PROVIDER=bedrock
LLM_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
LLM_API_BASE=
LLM_API_KEY=
```

And ensure AWS credentials are set:
```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

## Supported Model Formats

The system now supports multiple LiteLLM model formats:

- **Bedrock**: `bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Nvidia NIM**: `nvidia_nim/minimaxai/minimax-m2.1`
- **OpenAI**: `openai/gpt-4`
- **Anthropic**: `anthropic/claude-3-opus-20240229`

## Troubleshooting

### API Key Issues
- Ensure `LLM_API_KEY` is set correctly in `.env`
- Check that the API key has proper permissions

### Connection Errors
- Verify `LLM_API_BASE` URL is correct
- Check network connectivity to Nvidia API

### Model Not Found
- Confirm the model name format: `nvidia_nim/minimaxai/minimax-m2.1`
- Check Nvidia documentation for available models

## Notes

- The Nvidia API key format is: `nvapi-<key>`
- API keys are stored in environment variables, not in code
- AWS credentials are only required when using Bedrock models
- LiteLLM handles the API communication automatically
