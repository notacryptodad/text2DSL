#!/usr/bin/env python3
"""Test script to verify Nvidia NIM configuration with LiteLLM."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.text2x.llm.litellm_client import LiteLLMClient


async def test_nvidia_nim():
    """Test Nvidia NIM model with LiteLLM."""
    
    # Get configuration from environment
    model = os.getenv("LLM_MODEL", "nvidia_nim/minimaxai/minimax-m2.1")
    api_base = os.getenv("LLM_API_BASE", "https://integrate.api.nvidia.com/v1")
    api_key = os.getenv("LLM_API_KEY")
    
    print(f"Testing Nvidia NIM configuration:")
    print(f"  Model: {model}")
    print(f"  API Base: {api_base}")
    print(f"  API Key: {'*' * 20 if api_key else 'NOT SET'}")
    print()
    
    if not api_key:
        print("ERROR: LLM_API_KEY not set in environment")
        return
    
    # Create client
    client = LiteLLMClient(
        model=model,
        api_base=api_base,
        api_key=api_key,
        temperature=0.0,
        max_tokens=100,
    )
    
    # Test message
    messages = [
        {"role": "user", "content": "Say 'Hello from Nvidia NIM!' and nothing else."}
    ]
    
    print("Sending test request...")
    try:
        response = await client.acomplete(messages=messages)
        
        print("\n✅ SUCCESS!")
        print(f"Response: {response.choices[0].message.content}")
        print(f"Model: {response.model}")
        print(f"Tokens: {response.usage.total_tokens if response.usage else 'N/A'}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_nvidia_nim())
