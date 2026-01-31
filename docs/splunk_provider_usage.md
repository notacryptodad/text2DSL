# Splunk Provider Usage Guide

This guide demonstrates how to use the Splunk Provider for SPL (Search Processing Language) queries in Text2X.

## Table of Contents
- [Installation](#installation)
- [Basic Setup](#basic-setup)
- [Schema Introspection](#schema-introspection)
- [Query Validation](#query-validation)
- [Query Execution](#query-execution)
- [Search Job Management](#search-job-management)
- [Error Handling](#error-handling)
- [Advanced Usage](#advanced-usage)

## Installation

Install Text2X with Splunk support:

```bash
pip install text2dsl
# or for development
pip install -e .
```

The Splunk SDK (`splunk-sdk>=2.0.0`) will be installed automatically as a dependency.

## Basic Setup

### Using the Factory Function

```python
from text2x.providers import create_splunk_provider

# Create provider with basic authentication
provider = create_splunk_provider(
    host="splunk.example.com",
    port=8089,
    username="admin",
    password="changeme"
)
```

### Using the Configuration Class

```python
from text2x.providers import SplunkProvider, SplunkConnectionConfig

# Configure connection
config = SplunkConnectionConfig(
    host="splunk.example.com",
    port=8089,
    username="admin",
    password="changeme",
    scheme="https",
    verify=False,  # Set to True to verify SSL certificates
    owner="admin",
    app="search"
)

# Create provider
provider = SplunkProvider(config)
```

### Token-Based Authentication

```python
config = SplunkConnectionConfig(
    host="splunk.example.com",
    port=8089,
    token="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    username="admin",  # Still required for owner field
    password="",  # Empty when using token
)

provider = SplunkProvider(config)
```

## Schema Introspection

The Splunk Provider can retrieve information about indexes, sourcetypes, and common fields.

### Get Complete Schema

```python
import asyncio

async def get_schema():
    schema = await provider.get_schema()

    # Access indexes (treated as "tables")
    print(f"Found {len(schema.tables)} indexes")

    for table in schema.tables:
        print(f"\nIndex: {table.name}")
        print(f"  Event Count: {table.row_count:,}")
        print(f"  Sourcetypes: {table.comment}")
        print(f"  Common Fields: {len(table.columns)}")

        # Show some common fields
        for col in table.columns[:5]:
            print(f"    - {col.name} ({col.type})")

    # Access sourcetypes
    print(f"\nAll Sourcetypes: {schema.sourcetypes}")

    # Metadata
    print(f"\nMetadata:")
    print(f"  Provider: {schema.metadata['provider']}")
    print(f"  Host: {schema.metadata['host']}")
    print(f"  Index Count: {schema.metadata['index_count']}")
    print(f"  Sourcetype Count: {schema.metadata['sourcetype_count']}")

asyncio.run(get_schema())
```

### Schema Caching

The provider caches schema information for 1 hour to improve performance:

```python
# First call - retrieves from Splunk
schema1 = await provider.get_schema()

# Second call within 1 hour - uses cache
schema2 = await provider.get_schema()

# Force refresh by clearing cache
provider._schema_cache = None
provider._cache_time = None
schema3 = await provider.get_schema()
```

## Query Validation

Validate SPL queries before execution.

### Basic Validation

```python
async def validate_query():
    query = "search index=main error | stats count by host"

    result = await provider.validate_syntax(query)

    if result.valid:
        print("✓ Query is valid")
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
    else:
        print(f"✗ Query is invalid: {result.error}")

    print(f"Validation took: {result.validation_time_ms:.2f}ms")

asyncio.run(validate_query())
```

### Validation with Splunk Parser

The provider validates queries using Splunk's built-in parser, ensuring accurate syntax checking:

```python
# Valid query
valid_query = "search index=web status=500 | timechart count by host"
result = await provider.validate_syntax(valid_query)
assert result.valid

# Invalid query - syntax error
invalid_query = "search index=web | invalid_command"
result = await provider.validate_syntax(invalid_query)
assert not result.valid
print(f"Error: {result.error}")
```

## Query Execution

Execute SPL queries and retrieve results.

### Basic Query Execution

```python
async def execute_query():
    query = """
    search index=web status=500 earliest=-1h
    | stats count by host, status
    | sort -count
    """

    # Execute with default limit (1000 rows)
    result = await provider.execute_query(query)

    if result.success:
        print(f"✓ Query executed successfully")
        print(f"  Rows returned: {result.row_count}")
        print(f"  Execution time: {result.execution_time_ms:.2f}ms")
        print(f"  Columns: {', '.join(result.columns)}")

        # Display sample results
        print("\nSample Results:")
        for i, row in enumerate(result.sample_rows[:5], 1):
            print(f"  {i}. {row}")
    else:
        print(f"✗ Query failed: {result.error}")

asyncio.run(execute_query())
```

### Query with Custom Limit

```python
# Limit results to 50 rows
result = await provider.execute_query(
    "search index=main error",
    limit=50
)
```

### Automatic Limit Enforcement

The provider automatically adds a `| head` command if not present:

```python
# Original query
query = "search index=main error"

# Provider ensures limit by adding: | head 100
result = await provider.execute_query(query, limit=100)

# If query already has head/tail, it's preserved
query_with_limit = "search index=main error | head 10"
result = await provider.execute_query(query_with_limit, limit=100)
# Query remains unchanged
```

## Search Job Management

The Splunk Provider supports asynchronous search job management.

### Get Search Job Status

```python
async def monitor_job():
    # Start a long-running search
    query = "search index=_internal earliest=-24h | stats count by component"

    # Note: You need to modify execute_query to return SID if you want to track it
    # For now, this is an example of the API

    sid = "1234567890.12345"  # Search ID from a running job

    status = await provider.get_search_job_status(sid)

    if status:
        print(f"Job Status: {status.status.value}")
        print(f"Progress: {status.progress:.1f}%")
        print(f"Events: {status.event_count:,}")
        print(f"Results: {status.result_count:,}")
        print(f"Runtime: {status.run_duration:.2f}s")

asyncio.run(monitor_job())
```

### Cancel a Running Job

```python
async def cancel_job():
    sid = "1234567890.12345"

    success = await provider.cancel_search_job(sid)

    if success:
        print(f"✓ Job {sid} cancelled successfully")
    else:
        print(f"✗ Failed to cancel job {sid}")

asyncio.run(cancel_job())
```

### Poll for Job Completion

The provider automatically polls for job completion during execution:

```python
# The provider handles polling internally
result = await provider.execute_query(
    "search index=_internal earliest=-24h | stats count by component"
)

# Job is polled every 0.5 seconds until complete
```

## Error Handling

### Handle Connection Errors

```python
try:
    provider = create_splunk_provider(
        host="invalid.host",
        username="admin",
        password="wrong_password"
    )

    schema = await provider.get_schema()
except Exception as e:
    print(f"Connection error: {e}")
```

### Handle Query Errors

```python
query = "search index=nonexistent | invalid syntax"

result = await provider.execute_query(query)

if not result.success:
    print(f"Query failed: {result.error}")

    # Check specific error types
    if "timeout" in result.error.lower():
        print("Query timed out")
    elif "syntax" in result.error.lower():
        print("Syntax error in query")
    elif "permission" in result.error.lower():
        print("Permission denied")
```

### Timeout Configuration

Configure query timeout in provider config:

```python
from text2x.providers import ProviderConfig

provider_config = ProviderConfig(
    provider_type="splunk",
    timeout_seconds=60,  # 60 second timeout
    max_rows=5000
)

provider = SplunkProvider(config, provider_config)
```

## Advanced Usage

### Custom Provider Configuration

```python
from text2x.providers import ProviderConfig

# Configure provider behavior
provider_config = ProviderConfig(
    provider_type="splunk",
    timeout_seconds=120,  # 2 minute timeout
    max_rows=10000,       # Return up to 10,000 rows
    extra_params={
        "retry_attempts": 3,
        "custom_setting": "value"
    }
)

provider = SplunkProvider(splunk_config, provider_config)
```

### Working with Multiple Indexes

```python
async def search_multiple_indexes():
    # Search across multiple indexes
    query = """
    search (index=web OR index=app OR index=security)
        status=500 earliest=-1h
    | stats count by index, host
    | sort -count
    """

    result = await provider.execute_query(query, limit=100)

    if result.success:
        print(f"Found {result.row_count} results across indexes")
        for row in result.sample_rows:
            print(f"  {row}")

asyncio.run(search_multiple_indexes())
```

### Time-Based Searches

```python
async def time_based_search():
    # Search with specific time range
    query = """
    search index=web status=500
        earliest=-24h@h latest=@h
    | timechart span=1h count by status
    """

    result = await provider.execute_query(query)

    # Process time-series data
    for row in result.sample_rows:
        time = row.get('_time')
        count = row.get('count')
        print(f"{time}: {count} events")

asyncio.run(time_based_search())
```

### Aggregations and Statistics

```python
async def aggregation_example():
    query = """
    search index=web
    | stats
        count as total_requests,
        avg(response_time) as avg_response,
        max(response_time) as max_response,
        min(response_time) as min_response
        by host
    | where total_requests > 1000
    | sort -total_requests
    """

    result = await provider.execute_query(query)

    if result.success:
        for row in result.sample_rows:
            print(f"Host: {row['host']}")
            print(f"  Total Requests: {row['total_requests']}")
            print(f"  Avg Response: {row['avg_response']:.2f}ms")
            print(f"  Max Response: {row['max_response']:.2f}ms")

asyncio.run(aggregation_example())
```

### Clean Up Connections

```python
async def with_cleanup():
    provider = create_splunk_provider(
        host="splunk.example.com",
        username="admin",
        password="changeme"
    )

    try:
        # Use provider
        result = await provider.execute_query("search index=main | head 10")
        print(f"Results: {result.row_count}")
    finally:
        # Clean up
        await provider.close()

asyncio.run(with_cleanup())
```

### Context Manager Pattern

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def splunk_provider_context(host, username, password):
    provider = create_splunk_provider(
        host=host,
        username=username,
        password=password
    )
    try:
        yield provider
    finally:
        await provider.close()

async def use_with_context():
    async with splunk_provider_context(
        "splunk.example.com", "admin", "changeme"
    ) as provider:
        result = await provider.execute_query("search index=main | head 10")
        print(f"Results: {result.row_count}")

asyncio.run(use_with_context())
```

## Provider Capabilities

Check what the provider supports:

```python
from text2x.providers import ProviderCapability

capabilities = provider.get_capabilities()

print("Supported capabilities:")
for cap in capabilities:
    print(f"  - {cap.value}")

# Check specific capability
if ProviderCapability.QUERY_EXECUTION in capabilities:
    print("✓ Provider supports query execution")

if ProviderCapability.QUERY_EXPLANATION in capabilities:
    print("✓ Provider supports query explanation")
else:
    print("✗ Provider does not support query explanation")
```

## Integration with Text2X Agents

The Splunk Provider is designed to work seamlessly with Text2X agents:

```python
# In Schema Expert Agent
schema = await splunk_provider.get_schema()
relevant_indexes = [t for t in schema.tables if 'web' in t.name.lower()]

# In Query Builder Agent
query = generate_spl_query(user_input, schema)

# In Validator Agent
validation = await splunk_provider.validate_syntax(query)
if validation.valid:
    execution = await splunk_provider.execute_query(query)
```

## Best Practices

1. **Use Schema Caching**: The provider caches schema for 1 hour. Don't clear cache unnecessarily.

2. **Set Appropriate Limits**: Always set reasonable row limits to prevent overwhelming results.

3. **Use Time Ranges**: Always specify time ranges in production queries to improve performance.

4. **Handle Errors Gracefully**: Check `result.success` and handle errors appropriately.

5. **Clean Up Connections**: Call `await provider.close()` when done.

6. **Use Token Authentication**: For production, use token-based authentication instead of passwords.

7. **Enable SSL Verification**: Set `verify=True` in production environments.

8. **Monitor Query Performance**: Use `execution_time_ms` to track query performance.

## Troubleshooting

### Connection Issues

```python
# Test connection
try:
    schema = await provider.get_schema()
    print("✓ Connection successful")
except Exception as e:
    print(f"✗ Connection failed: {e}")
    # Check: host, port, credentials, network access
```

### Query Timeout

```python
# Increase timeout for long-running queries
provider_config = ProviderConfig(
    provider_type="splunk",
    timeout_seconds=300  # 5 minutes
)

provider = SplunkProvider(splunk_config, provider_config)
```

### SSL Certificate Errors

```python
# For development/testing only - disable SSL verification
config = SplunkConnectionConfig(
    host="splunk.local",
    username="admin",
    password="changeme",
    verify=False  # Disable SSL verification
)

# For production - use proper SSL certificates
config = SplunkConnectionConfig(
    host="splunk.production.com",
    username="admin",
    password="changeme",
    verify=True  # Enable SSL verification
)
```

## Next Steps

- Explore [SQL Provider Usage](sql_provider_usage.md)
- Learn about [NoSQL Provider Usage](nosql_provider_usage.md)
- Read the [Provider Architecture Guide](provider_architecture.md)
- Check out [Agent Integration Examples](agent_integration.md)
