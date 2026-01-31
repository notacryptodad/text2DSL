#!/usr/bin/env python3
"""
Example usage of the Splunk Provider for Text2X

This script demonstrates how to:
1. Connect to Splunk
2. Retrieve schema information
3. Validate SPL queries
4. Execute queries and retrieve results
"""

import asyncio
import os
from text2x.providers import (
    create_splunk_provider,
    SplunkProvider,
    SplunkConnectionConfig,
    ProviderConfig
)


async def example_basic_connection():
    """Example: Basic connection to Splunk"""
    print("=" * 60)
    print("Example 1: Basic Connection")
    print("=" * 60)

    # Create provider using factory function
    provider = create_splunk_provider(
        host=os.getenv("SPLUNK_HOST", "localhost"),
        port=int(os.getenv("SPLUNK_PORT", "8089")),
        username=os.getenv("SPLUNK_USERNAME", "admin"),
        password=os.getenv("SPLUNK_PASSWORD", "changeme"),
    )

    # Get provider information
    print(f"Provider ID: {provider.get_provider_id()}")
    print(f"Query Language: {provider.get_query_language()}")
    print(f"Capabilities: {[cap.value for cap in provider.get_capabilities()]}")

    await provider.close()


async def example_schema_introspection():
    """Example: Retrieve and explore Splunk schema"""
    print("\n" + "=" * 60)
    print("Example 2: Schema Introspection")
    print("=" * 60)

    provider = create_splunk_provider(
        host=os.getenv("SPLUNK_HOST", "localhost"),
        port=int(os.getenv("SPLUNK_PORT", "8089")),
        username=os.getenv("SPLUNK_USERNAME", "admin"),
        password=os.getenv("SPLUNK_PASSWORD", "changeme"),
    )

    try:
        # Get schema
        schema = await provider.get_schema()

        print(f"\nFound {len(schema.tables)} indexes:")
        for table in schema.tables[:5]:  # Show first 5 indexes
            print(f"\n  Index: {table.name}")
            print(f"    Events: {table.row_count:,}" if table.row_count else "    Events: Unknown")
            print(f"    Fields: {len(table.columns)}")
            print(f"    Info: {table.comment[:100] if table.comment else 'N/A'}")

        print(f"\nTotal Sourcetypes: {len(schema.sourcetypes) if schema.sourcetypes else 0}")
        if schema.sourcetypes:
            print(f"  Examples: {', '.join(schema.sourcetypes[:5])}")

        print(f"\nMetadata:")
        for key, value in schema.metadata.items():
            print(f"  {key}: {value}")

    finally:
        await provider.close()


async def example_query_validation():
    """Example: Validate SPL queries"""
    print("\n" + "=" * 60)
    print("Example 3: Query Validation")
    print("=" * 60)

    provider = create_splunk_provider(
        host=os.getenv("SPLUNK_HOST", "localhost"),
        port=int(os.getenv("SPLUNK_PORT", "8089")),
        username=os.getenv("SPLUNK_USERNAME", "admin"),
        password=os.getenv("SPLUNK_PASSWORD", "changeme"),
    )

    try:
        # Valid query
        valid_query = "search index=main error | stats count by host"
        print(f"\nValidating valid query:")
        print(f"  Query: {valid_query}")

        result = await provider.validate_syntax(valid_query)
        print(f"  Valid: {result.valid}")
        if result.warnings:
            print(f"  Warnings: {result.warnings}")
        print(f"  Validation time: {result.validation_time_ms:.2f}ms")

        # Query without search prefix (warning)
        query_with_warning = "index=main error"
        print(f"\nValidating query without 'search' prefix:")
        print(f"  Query: {query_with_warning}")

        result = await provider.validate_syntax(query_with_warning)
        print(f"  Valid: {result.valid}")
        if result.warnings:
            print(f"  Warnings:")
            for warning in result.warnings:
                print(f"    - {warning}")

        # Empty query
        print(f"\nValidating empty query:")
        result = await provider.validate_syntax("")
        print(f"  Valid: {result.valid}")
        print(f"  Error: {result.error}")

    finally:
        await provider.close()


async def example_query_execution():
    """Example: Execute SPL queries"""
    print("\n" + "=" * 60)
    print("Example 4: Query Execution")
    print("=" * 60)

    provider = create_splunk_provider(
        host=os.getenv("SPLUNK_HOST", "localhost"),
        port=int(os.getenv("SPLUNK_PORT", "8089")),
        username=os.getenv("SPLUNK_USERNAME", "admin"),
        password=os.getenv("SPLUNK_PASSWORD", "changeme"),
    )

    try:
        # Simple search query
        query = "search index=_internal earliest=-1h | head 10"
        print(f"\nExecuting query:")
        print(f"  Query: {query}")

        result = await provider.execute_query(query, limit=10)

        if result.success:
            print(f"\n  ✓ Query executed successfully")
            print(f"  Rows returned: {result.row_count}")
            print(f"  Execution time: {result.execution_time_ms:.2f}ms")
            print(f"  Columns: {', '.join(result.columns) if result.columns else 'N/A'}")

            if result.sample_rows:
                print(f"\n  Sample Results (first 3 rows):")
                for i, row in enumerate(result.sample_rows[:3], 1):
                    print(f"    {i}. {dict(list(row.items())[:5])}...")  # Show first 5 fields

        else:
            print(f"\n  ✗ Query failed: {result.error}")

        # Stats query
        stats_query = """
        search index=_internal earliest=-1h
        | stats count by component
        | sort -count
        """
        print(f"\nExecuting stats query:")
        print(f"  Query: {stats_query.strip()}")

        result = await provider.execute_query(stats_query, limit=5)

        if result.success:
            print(f"\n  ✓ Query executed successfully")
            print(f"  Results:")
            for row in result.sample_rows:
                component = row.get('component', 'Unknown')
                count = row.get('count', 0)
                print(f"    {component}: {count}")

    finally:
        await provider.close()


async def example_custom_configuration():
    """Example: Custom provider configuration"""
    print("\n" + "=" * 60)
    print("Example 5: Custom Configuration")
    print("=" * 60)

    # Create custom connection config
    conn_config = SplunkConnectionConfig(
        host=os.getenv("SPLUNK_HOST", "localhost"),
        port=int(os.getenv("SPLUNK_PORT", "8089")),
        username=os.getenv("SPLUNK_USERNAME", "admin"),
        password=os.getenv("SPLUNK_PASSWORD", "changeme"),
        scheme="https",
        verify=False,  # Disable SSL verification for dev/test
        owner="admin",
        app="search",
    )

    # Create custom provider config
    provider_config = ProviderConfig(
        provider_type="splunk",
        timeout_seconds=60,  # 60 second timeout
        max_rows=500,        # Max 500 rows
        extra_params={
            "custom_setting": "value"
        }
    )

    provider = SplunkProvider(conn_config, provider_config)

    print(f"Provider configured with:")
    print(f"  Host: {conn_config.host}:{conn_config.port}")
    print(f"  Scheme: {conn_config.scheme}")
    print(f"  SSL Verify: {conn_config.verify}")
    print(f"  Timeout: {provider_config.timeout_seconds}s")
    print(f"  Max Rows: {provider_config.max_rows}")

    await provider.close()


async def example_error_handling():
    """Example: Error handling"""
    print("\n" + "=" * 60)
    print("Example 6: Error Handling")
    print("=" * 60)

    provider = create_splunk_provider(
        host=os.getenv("SPLUNK_HOST", "localhost"),
        port=int(os.getenv("SPLUNK_PORT", "8089")),
        username=os.getenv("SPLUNK_USERNAME", "admin"),
        password=os.getenv("SPLUNK_PASSWORD", "changeme"),
    )

    try:
        # Execute a query that might fail
        invalid_query = "search index=nonexistent_index | invalid_command"

        print(f"Attempting to execute potentially invalid query:")
        print(f"  Query: {invalid_query}")

        result = await provider.execute_query(invalid_query)

        if result.success:
            print(f"  ✓ Query succeeded unexpectedly")
        else:
            print(f"  ✗ Query failed (as expected)")
            print(f"  Error: {result.error}")

            # Check error type
            if "timeout" in result.error.lower():
                print("  Error type: Timeout")
            elif "syntax" in result.error.lower():
                print("  Error type: Syntax Error")
            else:
                print("  Error type: Other")

    except Exception as e:
        print(f"  Exception occurred: {type(e).__name__}: {e}")

    finally:
        await provider.close()


async def main():
    """Run all examples"""
    print("Splunk Provider Examples")
    print("=" * 60)
    print("\nNote: These examples require a running Splunk instance.")
    print("Configure connection using environment variables:")
    print("  SPLUNK_HOST (default: localhost)")
    print("  SPLUNK_PORT (default: 8089)")
    print("  SPLUNK_USERNAME (default: admin)")
    print("  SPLUNK_PASSWORD (default: changeme)")
    print()

    try:
        await example_basic_connection()
        await example_schema_introspection()
        await example_query_validation()
        await example_query_execution()
        await example_custom_configuration()
        await example_error_handling()

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Example failed: {e}")
        print("\nMake sure Splunk is running and accessible.")
        print("Check your connection settings and credentials.")


if __name__ == "__main__":
    asyncio.run(main())
