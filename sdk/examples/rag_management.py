"""RAG example management using Text2X Python SDK."""

import asyncio
import os

from text2x_client import Text2XClient, ComplexityLevel, QueryIntent


async def main():
    """Demonstrate RAG example management."""
    base_url = os.getenv("TEXT2X_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("TEXT2X_API_KEY")

    print("RAG Example Management")
    print("=" * 70)
    print("This example demonstrates how to manage RAG examples for")
    print("improving query generation quality.\n")

    async with Text2XClient(base_url=base_url, api_key=api_key) as client:
        # Get provider
        providers = await client.list_providers()
        if not providers:
            print("No providers configured.")
            return

        provider_id = providers[0].id
        print(f"Using provider: {provider_id}\n")

        # Add some good examples
        print("ADDING GOOD EXAMPLES")
        print("-" * 70)

        good_examples = [
            {
                "natural_language_query": "Show me all customers",
                "generated_query": "SELECT * FROM customers;",
                "involved_tables": ["customers"],
                "query_intent": QueryIntent.FILTER,
                "complexity_level": ComplexityLevel.SIMPLE,
            },
            {
                "natural_language_query": "Count active users from last month",
                "generated_query": """
                    SELECT COUNT(*)
                    FROM users
                    WHERE status = 'active'
                      AND created_at >= DATE_TRUNC('month', NOW() - INTERVAL '1 month')
                      AND created_at < DATE_TRUNC('month', NOW());
                """.strip(),
                "involved_tables": ["users"],
                "query_intent": QueryIntent.AGGREGATION,
                "complexity_level": ComplexityLevel.MEDIUM,
            },
            {
                "natural_language_query": "Get top 10 customers by total order value",
                "generated_query": """
                    SELECT
                        c.id,
                        c.name,
                        SUM(o.total_amount) as total_value
                    FROM customers c
                    JOIN orders o ON c.id = o.customer_id
                    GROUP BY c.id, c.name
                    ORDER BY total_value DESC
                    LIMIT 10;
                """.strip(),
                "involved_tables": ["customers", "orders"],
                "query_intent": QueryIntent.JOIN,
                "complexity_level": ComplexityLevel.COMPLEX,
            },
        ]

        for i, example in enumerate(good_examples, 1):
            print(f"\nAdding good example {i}...")
            print(f"  Question: {example['natural_language_query']}")

            result = await client.add_example(
                provider_id=provider_id,
                natural_language_query=example["natural_language_query"],
                generated_query=example["generated_query"],
                is_good_example=True,
                involved_tables=example["involved_tables"],
                query_intent=example["query_intent"].value,
                complexity_level=example["complexity_level"].value,
            )

            print(f"  ✓ Added with ID: {result.id}")
            print(f"  Status: {result.status}")

        # Add a bad example (what not to do)
        print("\n\nADDING BAD EXAMPLES")
        print("-" * 70)

        bad_examples = [
            {
                "natural_language_query": "Show me users",
                "generated_query": "SELECT * FROM users;",  # Missing WHERE clause, pulls all data
                "involved_tables": ["users"],
                "query_intent": QueryIntent.FILTER,
                "complexity_level": ComplexityLevel.SIMPLE,
            },
        ]

        for i, example in enumerate(bad_examples, 1):
            print(f"\nAdding bad example {i}...")
            print(f"  Question: {example['natural_language_query']}")
            print(f"  Why it's bad: Pulls all data without any filtering")

            result = await client.add_example(
                provider_id=provider_id,
                natural_language_query=example["natural_language_query"],
                generated_query=example["generated_query"],
                is_good_example=False,  # Mark as bad example
                involved_tables=example["involved_tables"],
                query_intent=example["query_intent"].value,
                complexity_level=example["complexity_level"].value,
            )

            print(f"  ✓ Added with ID: {result.id}")

        # List all examples
        print("\n\n" + "=" * 70)
        print("LISTING EXAMPLES")
        print("=" * 70)

        # List approved examples
        print("\nApproved Examples:")
        approved = await client.list_examples(
            provider_id=provider_id, status="approved", limit=10
        )

        if approved:
            for example in approved:
                print(f"\n  ID: {example.id}")
                print(f"  Question: {example.natural_language_query}")
                print(f"  Query: {example.generated_query[:80]}...")
                print(f"  Tables: {example.involved_tables}")
                print(f"  Intent: {example.query_intent}")
                print(f"  Complexity: {example.complexity_level}")
                print(f"  Good: {example.is_good_example}")
        else:
            print("  No approved examples found.")

        # List pending review
        print("\n\nPending Review:")
        pending = await client.list_examples(
            provider_id=provider_id, status="pending_review", limit=10
        )

        if pending:
            for example in pending:
                print(f"\n  ID: {example.id}")
                print(f"  Question: {example.natural_language_query}")
                print(f"  Status: {example.status}")
                print(f"  Good: {example.is_good_example}")
        else:
            print("  No examples pending review.")

        # Test query with RAG
        print("\n\n" + "=" * 70)
        print("TESTING QUERY WITH RAG")
        print("=" * 70)

        test_query = "Show me the top customers by order value"
        print(f"\nQuery: {test_query}")
        print("(Should use the RAG example we added)")

        response = await client.query(
            provider_id=provider_id,
            query=test_query,
            trace_level="full",
            rag_top_k=5,  # Retrieve top 5 similar examples
        )

        print(f"\nGenerated: {response.generated_query}")
        print(f"Confidence: {response.confidence_score:.2%}")

        if response.reasoning_trace and response.reasoning_trace.rag_agent:
            rag_trace = response.reasoning_trace.rag_agent
            print(f"\nRAG Agent Trace:")
            print(f"  Latency: {rag_trace.latency_ms}ms")
            print(f"  Iterations: {rag_trace.iterations}")
            if rag_trace.details:
                examples_used = rag_trace.details.get("examples_retrieved", [])
                print(f"  Examples Retrieved: {len(examples_used)}")


async def review_queue_management():
    """Demonstrate review queue management."""
    base_url = os.getenv("TEXT2X_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("TEXT2X_API_KEY")

    print("\n\nReview Queue Management")
    print("=" * 70)

    async with Text2XClient(base_url=base_url, api_key=api_key) as client:
        # Get review queue
        print("\nFetching review queue...")
        queue = await client.get_review_queue(limit=10)

        if not queue:
            print("Review queue is empty.")
            return

        print(f"Found {len(queue)} items in queue:")

        for i, item in enumerate(queue, 1):
            print(f"\n{i}. Review Item")
            print(f"   ID: {item.id}")
            print(f"   Priority: {item.priority}")
            print(f"   Reason: {item.reason_for_review}")
            print(f"   Provider: {item.provider_id}")
            print(f"   User Query: {item.user_input}")
            print(f"   Generated: {item.generated_query[:80]}...")
            print(f"   Confidence: {item.confidence_score:.2%}")
            print(f"   Validation: {item.validation_status}")
            print(f"   Created: {item.created_at}")

        # Review the first item (approve it)
        if queue:
            item = queue[0]
            print(f"\n\nReviewing item {item.id}...")

            await client.submit_review(
                review_id=item.id,
                approved=True,
                feedback="Query looks good, approved for RAG",
            )

            print("✓ Review submitted successfully")


async def example_correction():
    """Demonstrate correcting examples through review."""
    base_url = os.getenv("TEXT2X_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("TEXT2X_API_KEY")

    print("\n\nExample Correction")
    print("=" * 70)

    async with Text2XClient(base_url=base_url, api_key=api_key) as client:
        providers = await client.list_providers()
        if not providers:
            return

        provider_id = providers[0].id

        # Generate a query that might need correction
        print("\nGenerating query...")
        query = "Show me all users"

        response = await client.query(
            provider_id=provider_id,
            query=query,
            trace_level="none",
        )

        print(f"Generated: {response.generated_query}")
        print(f"Confidence: {response.confidence_score:.2%}")

        # Provide feedback with correction
        print("\n\nSubmitting feedback with correction...")

        corrected_query = """
            SELECT id, name, email, created_at
            FROM users
            WHERE status = 'active'
            ORDER BY created_at DESC
            LIMIT 100;
        """.strip()

        await client.submit_feedback(
            conversation_id=response.conversation_id,
            rating=3,
            is_query_correct=False,
            corrected_query=corrected_query,
            comments="Original query was too broad. Added status filter, limited results, and specific columns.",
        )

        print("✓ Feedback with correction submitted")
        print("\nCorrected query:")
        print(corrected_query)


if __name__ == "__main__":
    # Run the main RAG management example
    asyncio.run(main())

    # Uncomment to run other examples:
    # asyncio.run(review_queue_management())
    # asyncio.run(example_correction())
