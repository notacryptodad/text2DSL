"""Basic query example using Text2X Python SDK."""

import asyncio
import os

from text2x_client import Text2XClient


async def main():
    """Run a basic query example."""
    # Get configuration from environment or use defaults
    base_url = os.getenv("TEXT2X_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("TEXT2X_API_KEY")

    print(f"Connecting to Text2X API at {base_url}")

    async with Text2XClient(base_url=base_url, api_key=api_key) as client:
        # Check API health
        print("\nChecking API health...")
        health = await client.health_check()
        print(f"API Status: {health['status']}")
        print(f"Version: {health['version']}")

        # List available providers
        print("\nListing available providers...")
        providers = await client.list_providers()
        if not providers:
            print("No providers configured. Please configure a provider first.")
            return

        for provider in providers:
            print(f"  - {provider.name} ({provider.type})")
            print(f"    Status: {provider.connection_status}")
            print(f"    Tables: {provider.table_count}")

        # Use the first available provider
        provider_id = providers[0].id
        print(f"\nUsing provider: {provider_id}")

        # Run a simple query
        print("\nGenerating query from natural language...")
        response = await client.query(
            provider_id=provider_id,
            query="Show me all records from the first table, limit to 10 rows",
            max_iterations=3,
            confidence_threshold=0.7,
            trace_level="summary",
            enable_execution=True,
        )

        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(f"\nGenerated Query:\n{response.generated_query}")
        print(f"\nConfidence Score: {response.confidence_score:.2%}")
        print(f"Validation Status: {response.validation_status}")
        print(f"Iterations: {response.iterations}")
        print(f"Needs Clarification: {response.needs_clarification}")

        if response.clarification_questions:
            print(f"Clarification Questions: {response.clarification_questions}")

        if response.validation_result.errors:
            print(f"\nValidation Errors: {response.validation_result.errors}")

        if response.validation_result.warnings:
            print(f"Validation Warnings: {response.validation_result.warnings}")

        if response.execution_result:
            print(f"\nExecution Result:")
            print(f"  Success: {response.execution_result.success}")
            print(f"  Row Count: {response.execution_result.row_count}")
            print(f"  Execution Time: {response.execution_result.execution_time_ms}ms")

            if response.execution_result.data:
                print(f"\nSample Data (first 3 rows):")
                for i, row in enumerate(response.execution_result.data[:3], 1):
                    print(f"  Row {i}: {row}")

        if response.reasoning_trace:
            print(f"\nReasoning Trace:")
            print(f"  Total Tokens (Input): {response.reasoning_trace.total_tokens_input}")
            print(f"  Total Tokens (Output): {response.reasoning_trace.total_tokens_output}")
            print(f"  Total Cost: ${response.reasoning_trace.total_cost_usd:.4f}")
            print(f"  Orchestrator Latency: {response.reasoning_trace.orchestrator_latency_ms}ms")

        # Submit feedback
        print("\n" + "=" * 70)
        print("SUBMITTING FEEDBACK")
        print("=" * 70)
        await client.submit_feedback(
            conversation_id=response.conversation_id,
            rating=5,
            is_query_correct=True,
            comments="Example query worked perfectly!",
        )
        print("Feedback submitted successfully")


if __name__ == "__main__":
    asyncio.run(main())
