#!/usr/bin/env python3
"""
Example WebSocket client for Text2DSL streaming query processing.

This demonstrates how to connect to the WebSocket endpoint and receive
real-time updates as the system processes a natural language query.

Usage:
    python examples/websocket_client.py
"""
import asyncio
import json
import sys
from typing import Optional

try:
    import websockets
except ImportError:
    print("Error: websockets package not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


async def stream_query(
    query: str,
    provider_id: str = "postgres-main",
    conversation_id: Optional[str] = None,
    trace_level: str = "summary",
    enable_execution: bool = False,
    websocket_url: str = "ws://localhost:8000/ws/query",
):
    """
    Stream a query to the Text2DSL WebSocket endpoint.

    Args:
        query: Natural language query
        provider_id: Database provider identifier
        conversation_id: Optional conversation ID for multi-turn dialogue
        trace_level: Trace detail level (none, summary, full)
        enable_execution: Whether to execute the generated query
        websocket_url: WebSocket endpoint URL
    """
    print(f"\n{'='*80}")
    print(f"Connecting to: {websocket_url}")
    print(f"Query: {query}")
    print(f"Provider: {provider_id}")
    print(f"Trace Level: {trace_level}")
    print(f"Execute Query: {enable_execution}")
    print(f"{'='*80}\n")

    try:
        async with websockets.connect(websocket_url) as websocket:
            # Send query request
            request = {
                "provider_id": provider_id,
                "query": query,
                "options": {
                    "trace_level": trace_level,
                    "max_iterations": 3,
                    "confidence_threshold": 0.8,
                    "enable_execution": enable_execution,
                },
            }

            if conversation_id:
                request["conversation_id"] = conversation_id

            print(f"📤 Sending query request...\n")
            await websocket.send(json.dumps(request))

            # Receive and display events
            event_count = 0
            while True:
                try:
                    message = await websocket.recv()
                    event = json.loads(message)
                    event_count += 1

                    event_type = event.get("type")
                    data = event.get("data", {})
                    trace = event.get("trace")

                    # Display event based on type
                    if event_type == "progress":
                        stage = data.get("stage", "unknown")
                        message_text = data.get("message", "")
                        progress = data.get("progress", 0) * 100

                        print(f"⏳ [{progress:5.1f}%] {stage:20s} - {message_text}")

                        if trace:
                            print(f"   └─ Trace: {json.dumps(trace, indent=6)}")

                    elif event_type == "clarification":
                        questions = data.get("questions", [])
                        print(f"\n❓ Clarification needed:")
                        for i, q in enumerate(questions, 1):
                            print(f"   {i}. {q}")
                        print()

                    elif event_type == "result":
                        result = data.get("result", {})
                        print(f"\n{'='*80}")
                        print(f"✅ Query Generation Completed!")
                        print(f"{'='*80}")
                        print(f"\nGenerated Query:")
                        print(f"  {result.get('generated_query', 'N/A')}")
                        print(f"\nConfidence Score: {result.get('confidence_score', 0):.2f}")
                        print(f"Validation Status: {result.get('validation_status', 'unknown')}")
                        print(f"Iterations: {result.get('iterations', 0)}")

                        # Display validation details
                        validation = result.get("validation_result", {})
                        if validation.get("suggestions"):
                            print(f"\n💡 Suggestions:")
                            for suggestion in validation["suggestions"]:
                                print(f"   • {suggestion}")

                        # Display execution results
                        execution = result.get("execution_result")
                        if execution:
                            print(f"\n🔍 Execution Results:")
                            print(f"   Success: {execution.get('success', False)}")
                            print(f"   Row Count: {execution.get('row_count', 0)}")
                            print(f"   Execution Time: {execution.get('execution_time_ms', 0)}ms")

                        # Display trace summary
                        if trace:
                            print(f"\n📊 Trace Summary:")
                            print(f"   {json.dumps(trace, indent=3)}")

                        reasoning_trace = result.get("reasoning_trace")
                        if reasoning_trace:
                            print(f"\n🧠 Reasoning Trace:")
                            print(f"   Total Latency: {reasoning_trace.get('orchestrator_latency_ms', 0)}ms")
                            print(f"   Total Tokens: {reasoning_trace.get('total_tokens_input', 0)} input, "
                                  f"{reasoning_trace.get('total_tokens_output', 0)} output")
                            print(f"   Total Cost: ${reasoning_trace.get('total_cost_usd', 0):.4f}")

                        print(f"\n{'='*80}\n")
                        break  # End after receiving result

                    elif event_type == "error":
                        error_type = data.get("error", "unknown")
                        error_message = data.get("message", "")
                        error_details = data.get("details", {})

                        print(f"\n{'='*80}")
                        print(f"❌ Error: {error_type}")
                        print(f"{'='*80}")
                        print(f"Message: {error_message}")
                        if error_details:
                            print(f"Details: {json.dumps(error_details, indent=2)}")
                        print(f"{'='*80}\n")
                        break  # End after receiving error

                    else:
                        print(f"⚠️  Unknown event type: {event_type}")
                        print(f"   Data: {json.dumps(data, indent=2)}\n")

                except websockets.exceptions.ConnectionClosed:
                    print("\n🔌 Connection closed by server")
                    break

            print(f"📊 Total events received: {event_count}\n")

    except ConnectionRefusedError:
        print(f"\n❌ Error: Could not connect to {websocket_url}")
        print("   Make sure the Text2DSL API server is running.")
        print("   Start it with: uvicorn text2x.api.app:app --reload\n")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        raise


async def main():
    """Run example queries."""
    # Example 1: Simple query with summary trace
    await stream_query(
        query="Show me all users who are over 18 years old",
        provider_id="postgres-main",
        trace_level="summary",
        enable_execution=False,
    )

    # Example 2: Query with full trace
    print("\n\n" + "="*80)
    print("Running second example with full trace...")
    print("="*80 + "\n")

    await stream_query(
        query="Count the number of orders per customer",
        provider_id="postgres-main",
        trace_level="full",
        enable_execution=False,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user\n")
        sys.exit(0)
