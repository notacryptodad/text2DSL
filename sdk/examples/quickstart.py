"""Quickstart example for Text2X Python SDK."""

import asyncio
import os
from text2x_client import Text2XClient


async def main():
    """Quick start with Text2X SDK."""
    # Get API configuration from environment
    base_url = os.getenv("TEXT2X_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("TEXT2X_API_KEY")

    print("Text2X Python SDK - Quickstart Example")
    print("=" * 70)

    # Create client using async context manager (handles cleanup automatically)
    async with Text2XClient(base_url=base_url, api_key=api_key) as client:
        # 1. Check API health
        print("\n1. Checking API health...")
        health = await client.health_check()
        print(f"   Status: {health.get('status', 'unknown')}")

        # 2. List available providers
        print("\n2. Listing available database providers...")
        providers = await client.list_providers()

        if not providers:
            print("   No providers configured. Please configure a provider first.")
            print("   See the documentation for provider setup instructions.")
            return

        for provider in providers:
            print(f"   - {provider.name} ({provider.type})")
            print(f"     Status: {provider.connection_status}")
            print(f"     Tables: {provider.table_count}")

        # Use the first available provider
        provider_id = providers[0].id

        # 3. Generate a query from natural language
        print(f"\n3. Generating query for provider: {provider_id}")
        print("   Natural language: 'Show me all records, limit to 10'")

        response = await client.query(
            provider_id=provider_id,
            query="Show me all records, limit to 10",
            max_iterations=3,
            confidence_threshold=0.7,
        )

        print(f"\n   Generated SQL:")
        print(f"   {response.generated_query}")
        print(f"\n   Confidence: {response.confidence_score:.2%}")
        print(f"   Validation: {response.validation_status}")
        print(f"   Iterations: {response.iterations}")

        # 4. Check if clarification is needed
        if response.needs_clarification:
            print("\n   ⚠ System needs clarification:")
            for q in response.clarification_questions:
                print(f"   - {q}")

        # 5. Submit feedback
        print("\n4. Submitting feedback...")
        await client.submit_feedback(
            conversation_id=response.conversation_id,
            rating=5,
            is_query_correct=True,
            comments="Quickstart example completed successfully!",
        )
        print("   ✓ Feedback submitted")

    print("\n" + "=" * 70)
    print("Quickstart completed! See other examples for more advanced usage:")
    print("  - basic_query.py: Full query processing with execution")
    print("  - websocket_streaming.py: Real-time streaming with WebSocket")
    print("  - multi_turn_conversation.py: Multi-turn dialogue examples")
    print("  - rag_management.py: Managing RAG examples")


if __name__ == "__main__":
    asyncio.run(main())
