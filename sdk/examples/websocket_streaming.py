"""WebSocket streaming example using Text2X Python SDK."""

import asyncio
import os

from text2x_client import WebSocketClient


async def main():
    """Run a WebSocket streaming example."""
    # Get configuration from environment or use defaults
    base_url = os.getenv("TEXT2X_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("TEXT2X_API_KEY")

    # Convert HTTP URL to WebSocket URL
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")

    print(f"Connecting to Text2X WebSocket at {ws_url}")

    async with WebSocketClient(base_url=ws_url, api_key=api_key) as ws_client:
        print("\nStreaming query processing...")
        print("=" * 70)

        # Track progress
        start_time = asyncio.get_event_loop().time()
        event_count = 0

        async for event in ws_client.query_stream(
            provider_id="postgres_main",
            query="Show me all orders from last month with total greater than $1000",
            trace_level="full",
            enable_execution=True,
        ):
            event_count += 1
            elapsed = asyncio.get_event_loop().time() - start_time

            print(f"\n[{elapsed:.2f}s] Event #{event_count}: {event.type.upper()}")
            print("-" * 70)

            if event.is_progress:
                # Progress update
                step = event.data.get("step", "Unknown")
                message = event.data.get("message", "")
                print(f"Progress: {step}")
                if message:
                    print(f"  Message: {message}")

                if event.trace:
                    print(f"  Trace: {event.trace}")

            elif event.is_clarification:
                # System needs clarification
                questions = event.data.get("questions", [])
                conversation_id = event.data.get("conversation_id")

                print(f"Clarification Needed:")
                for i, question in enumerate(questions, 1):
                    print(f"  {i}. {question}")

                print(f"\nConversation ID: {conversation_id}")
                print("To continue, send another query with this conversation_id")

            elif event.is_result:
                # Final result
                print(f"SUCCESS - Query Generated!")
                print(f"\nGenerated Query:")
                print(f"  {event.data.get('generated_query', 'N/A')}")
                print(f"\nConfidence: {event.data.get('confidence_score', 0):.2%}")
                print(f"Validation: {event.data.get('validation_status', 'unknown')}")
                print(f"Iterations: {event.data.get('iterations', 0)}")

                # Show execution results if available
                execution = event.data.get("execution_result")
                if execution:
                    print(f"\nExecution Results:")
                    print(f"  Success: {execution.get('success', False)}")
                    print(f"  Rows: {execution.get('row_count', 0)}")
                    print(f"  Time: {execution.get('execution_time_ms', 0)}ms")

                # Show reasoning trace if available
                if event.trace:
                    print(f"\nReasoning Trace:")
                    print(f"  Total Tokens: {event.trace.get('total_tokens_input', 0)}")
                    print(f"  Cost: ${event.trace.get('total_cost_usd', 0):.4f}")

            elif event.is_error:
                # Error occurred
                print(f"ERROR: {event.data.get('error', 'Unknown error')}")
                print(f"Message: {event.data.get('message', 'No message')}")

                details = event.data.get("details")
                if details:
                    print(f"Details: {details}")

        print("\n" + "=" * 70)
        print(f"Streaming completed - {event_count} events received")
        print(f"Total time: {asyncio.get_event_loop().time() - start_time:.2f}s")


async def multi_query_streaming():
    """Run multiple queries concurrently using streaming."""
    base_url = os.getenv("TEXT2X_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("TEXT2X_API_KEY")
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")

    print("\nRunning multiple concurrent streaming queries...")
    print("=" * 70)

    queries = [
        "Show me all orders",
        "Count total customers",
        "Get top 10 products by revenue",
    ]

    async def process_query(query: str, query_num: int):
        """Process a single query via WebSocket."""
        async with WebSocketClient(base_url=ws_url, api_key=api_key) as ws_client:
            print(f"\n[Query {query_num}] Starting: {query}")

            async for event in ws_client.query_stream(
                provider_id="postgres_main",
                query=query,
            ):
                if event.is_result:
                    generated = event.data.get("generated_query", "N/A")
                    confidence = event.data.get("confidence_score", 0)
                    print(f"[Query {query_num}] ✓ Complete (confidence: {confidence:.2%})")
                    print(f"[Query {query_num}] Result: {generated[:100]}...")
                    return generated

                elif event.is_error:
                    print(f"[Query {query_num}] ✗ Error: {event.data.get('message')}")
                    return None

    # Run all queries concurrently
    tasks = [process_query(q, i + 1) for i, q in enumerate(queries)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    print("\n" + "=" * 70)
    print("All queries completed")
    print("=" * 70)

    for i, (query, result) in enumerate(zip(queries, results), 1):
        if isinstance(result, Exception):
            print(f"{i}. {query} -> ERROR: {result}")
        else:
            print(f"{i}. {query} -> {result[:80]}...")


async def interactive_streaming():
    """Interactive streaming with clarification handling."""
    base_url = os.getenv("TEXT2X_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("TEXT2X_API_KEY")
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")

    print("\nInteractive streaming with clarification handling...")
    print("=" * 70)

    async def clarification_handler(questions: list[str]) -> str:
        """Handle clarification requests."""
        print("\n🤔 The system needs clarification:")
        for i, question in enumerate(questions, 1):
            print(f"  {i}. {question}")

        # In a real application, you would get input from the user
        # For this example, we'll return a default answer
        answer = "Use the orders table and filter by created_at >= last month"
        print(f"\n💬 Answer: {answer}")
        return answer

    async with WebSocketClient(base_url=ws_url, api_key=api_key) as ws_client:
        result = await ws_client.query_stream_with_clarification(
            provider_id="postgres_main",
            query="Show me orders",  # Intentionally vague to trigger clarification
            clarification_callback=clarification_handler,
        )

        if result.is_result:
            print("\n✓ Final Result:")
            print(f"  Query: {result.data.get('generated_query')}")
            print(f"  Confidence: {result.data.get('confidence_score', 0):.2%}")
        else:
            print(f"\n✗ Failed: {result.data}")


if __name__ == "__main__":
    # Run the basic streaming example
    asyncio.run(main())

    # Uncomment to run other examples:
    # asyncio.run(multi_query_streaming())
    # asyncio.run(interactive_streaming())
