"""Multi-turn conversation example using Text2X Python SDK."""

import asyncio
import os

from text2x_client import Text2XClient


async def main():
    """Run a multi-turn conversation example."""
    base_url = os.getenv("TEXT2X_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("TEXT2X_API_KEY")

    print("Multi-turn Conversation Example")
    print("=" * 70)
    print("This example demonstrates how to build queries iteratively")
    print("through multiple conversation turns.\n")

    async with Text2XClient(base_url=base_url, api_key=api_key) as client:
        # Get available providers
        providers = await client.list_providers()
        if not providers:
            print("No providers configured.")
            return

        provider_id = providers[0].id
        print(f"Using provider: {provider_id}\n")

        conversation_id = None

        # Turn 1: Initial query
        print("TURN 1: Initial Query")
        print("-" * 70)
        query1 = "Show me all customers"
        print(f"User: {query1}")

        response1 = await client.query(
            provider_id=provider_id,
            query=query1,
            trace_level="none",
        )

        conversation_id = response1.conversation_id
        print(f"\nAssistant:")
        print(f"  Generated Query: {response1.generated_query}")
        print(f"  Confidence: {response1.confidence_score:.2%}")
        print(f"  Conversation ID: {conversation_id}")

        # Small delay for demonstration
        await asyncio.sleep(1)

        # Turn 2: Refine the query
        print("\n\nTURN 2: Refine Query")
        print("-" * 70)
        query2 = "Only show active customers"
        print(f"User: {query2}")

        response2 = await client.query(
            provider_id=provider_id,
            query=query2,
            conversation_id=conversation_id,
            trace_level="none",
        )

        print(f"\nAssistant:")
        print(f"  Generated Query: {response2.generated_query}")
        print(f"  Confidence: {response2.confidence_score:.2%}")

        await asyncio.sleep(1)

        # Turn 3: Add sorting
        print("\n\nTURN 3: Add Sorting")
        print("-" * 70)
        query3 = "Sort by registration date, most recent first"
        print(f"User: {query3}")

        response3 = await client.query(
            provider_id=provider_id,
            query=query3,
            conversation_id=conversation_id,
            trace_level="none",
        )

        print(f"\nAssistant:")
        print(f"  Generated Query: {response3.generated_query}")
        print(f"  Confidence: {response3.confidence_score:.2%}")

        await asyncio.sleep(1)

        # Turn 4: Add limit
        print("\n\nTURN 4: Add Limit")
        print("-" * 70)
        query4 = "Show only the top 10"
        print(f"User: {query4}")

        response4 = await client.query(
            provider_id=provider_id,
            query=query4,
            conversation_id=conversation_id,
            trace_level="summary",
        )

        print(f"\nAssistant:")
        print(f"  Generated Query: {response4.generated_query}")
        print(f"  Confidence: {response4.confidence_score:.2%}")
        print(f"  Iterations: {response4.iterations}")

        # Get full conversation history
        print("\n\n" + "=" * 70)
        print("CONVERSATION HISTORY")
        print("=" * 70)

        conversation = await client.get_conversation(conversation_id)
        print(f"\nConversation ID: {conversation.id}")
        print(f"Provider: {conversation.provider_id}")
        print(f"Status: {conversation.status}")
        print(f"Total Turns: {conversation.turn_count}")
        print(f"Created: {conversation.created_at}")
        print(f"Updated: {conversation.updated_at}")

        print("\n\nTurn History:")
        for turn in conversation.turns:
            print(f"\n  Turn {turn.turn_number}:")
            print(f"    User Input: {turn.user_input}")
            print(f"    Generated: {turn.generated_query[:80]}...")
            print(f"    Confidence: {turn.confidence_score:.2%}")
            print(f"    Validation: {turn.validation_status}")
            print(f"    Created: {turn.created_at}")

        # Submit feedback for the conversation
        print("\n\n" + "=" * 70)
        print("FEEDBACK")
        print("=" * 70)

        await client.submit_feedback(
            conversation_id=conversation_id,
            rating=5,
            is_query_correct=True,
            comments="Great multi-turn experience! The system understood context perfectly.",
        )

        print("Feedback submitted successfully!")


async def branching_conversation():
    """Example of branching conversations (exploring different paths)."""
    base_url = os.getenv("TEXT2X_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("TEXT2X_API_KEY")

    print("\n\nBranching Conversation Example")
    print("=" * 70)
    print("This example shows how to explore different query variations")
    print("from the same starting point.\n")

    async with Text2XClient(base_url=base_url, api_key=api_key) as client:
        providers = await client.list_providers()
        if not providers:
            return

        provider_id = providers[0].id

        # Starting point
        print("STARTING QUERY")
        print("-" * 70)
        base_query = "Show me sales data"
        print(f"User: {base_query}")

        base_response = await client.query(
            provider_id=provider_id,
            query=base_query,
        )

        conversation_id = base_response.conversation_id
        print(f"Generated: {base_response.generated_query}\n")

        # Branch 1: Time-based filtering
        print("\nBRANCH 1: Time-based filtering")
        print("-" * 70)

        branch1_query = "Filter to last 30 days"
        print(f"User: {branch1_query}")

        branch1_response = await client.query(
            provider_id=provider_id,
            query=branch1_query,
            conversation_id=conversation_id,
        )

        print(f"Generated: {branch1_response.generated_query}")

        # Continue branch 1
        branch1_cont = "Group by product category"
        print(f"\nUser: {branch1_cont}")

        branch1_cont_response = await client.query(
            provider_id=provider_id,
            query=branch1_cont,
            conversation_id=conversation_id,
        )

        print(f"Generated: {branch1_cont_response.generated_query}")

        # Branch 2: Start new conversation from base (different direction)
        print("\n\nBRANCH 2: Amount-based filtering (new conversation)")
        print("-" * 70)

        branch2_query = "Show me sales data"  # Start fresh
        branch2_response = await client.query(
            provider_id=provider_id,
            query=branch2_query,
        )

        conversation_id_2 = branch2_response.conversation_id

        branch2_filter = "Only show sales greater than $1000"
        print(f"User: {branch2_filter}")

        branch2_filter_response = await client.query(
            provider_id=provider_id,
            query=branch2_filter,
            conversation_id=conversation_id_2,
        )

        print(f"Generated: {branch2_filter_response.generated_query}")

        # Continue branch 2
        branch2_cont = "Sort by amount descending"
        print(f"\nUser: {branch2_cont}")

        branch2_cont_response = await client.query(
            provider_id=provider_id,
            query=branch2_cont,
            conversation_id=conversation_id_2,
        )

        print(f"Generated: {branch2_cont_response.generated_query}")

        print("\n\n" + "=" * 70)
        print("COMPARISON")
        print("=" * 70)
        print("\nBranch 1 (Time-based):")
        print(f"  {branch1_cont_response.generated_query}")
        print("\nBranch 2 (Amount-based):")
        print(f"  {branch2_cont_response.generated_query}")


if __name__ == "__main__":
    # Run the main multi-turn conversation
    asyncio.run(main())

    # Uncomment to run branching example:
    # asyncio.run(branching_conversation())
