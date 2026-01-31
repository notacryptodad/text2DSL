# Splunk Provider for Text2X

The Splunk Provider enables Text2X to work with Splunk's Search Processing Language (SPL) for querying and analyzing machine-generated data.

## Overview

The Splunk Provider implements the `QueryProvider` interface to support:
- Schema introspection (indexes, sourcetypes, fields)
- SPL query validation
- Query execution with result retrieval
- Search job management
- Asynchronous operations

## Features

### Capabilities

- **Schema Introspection**: Retrieve indexes, sourcetypes, and common fields
- **Query Validation**: Validate SPL syntax using Splunk's parser
- **Query Execution**: Execute searches and retrieve results
- **Search Job Management**: Monitor, poll, and cancel search jobs
- **Result Pagination**: Automatic result limiting with `head` command
- **Connection Pooling**: Efficient connection management
- **Schema Caching**: 1-hour cache for schema information

### Authentication Methods

1. **Username/Password**: Basic authentication
2. **Token-based**: Bearer token authentication
3. **SSL/TLS**: Configurable certificate verification

## Architecture

### Class Hierarchy

```
QueryProvider (ABC)
    └── SplunkProvider
            ├── SplunkConnectionConfig (connection settings)
            ├── ProviderConfig (behavior settings)
            └── Splunk SDK (splunklib.client)
```

### Key Components

#### SplunkProvider

Main provider class that implements the `QueryProvider` interface.

**Methods:**
- `get_provider_id()`: Returns unique provider identifier
- `get_query_language()`: Returns "SPL"
- `get_capabilities()`: Lists supported capabilities
- `get_schema()`: Retrieves schema information
- `validate_syntax()`: Validates SPL query syntax
- `execute_query()`: Executes query and returns results
- `get_search_job_status()`: Gets status of a search job
- `cancel_search_job()`: Cancels a running search job
- `close()`: Cleans up connections

#### SplunkConnectionConfig

Configuration for Splunk connection.

**Parameters:**
- `host`: Splunk host address
- `port`: Management port (default: 8089)
- `username`: Username for authentication
- `password`: Password for authentication
- `scheme`: Connection scheme (http/https)
- `token`: Optional bearer token for token auth
- `verify`: SSL certificate verification
- `owner`: Owner context (default: admin)
- `app`: App context (default: search)
- `extra_params`: Additional connection parameters

#### SplunkSearchJob

Represents a Splunk search job with status information.

**Properties:**
- `sid`: Search job ID
- `status`: Job status (QUEUED, RUNNING, DONE, FAILED, etc.)
- `progress`: Completion progress (0-100%)
- `event_count`: Number of events processed
- `result_count`: Number of results
- `run_duration`: Execution time in seconds
- `error`: Error message if failed

## Implementation Details

### Schema Introspection

The provider treats Splunk indexes as "tables" and maps them to the `TableInfo` structure:

```python
SchemaDefinition
├── tables: List[TableInfo]           # Indexes
│   ├── name: str                     # Index name
│   ├── columns: List[ColumnInfo]     # Common fields
│   ├── comment: str                  # Sourcetype info
│   └── row_count: int                # Event count
├── sourcetypes: List[str]            # All sourcetypes
└── metadata: Dict                    # Provider metadata
```

**Common Fields Retrieved:**
- `_time`: Event timestamp
- `_raw`: Raw event data
- `host`: Source host
- `source`: Event source
- `sourcetype`: Data type
- `index`: Index name
- `_indextime`: Indexing timestamp
- Additional extracted fields (discovered dynamically)

### Query Validation

Validation process:
1. Basic syntax checks (empty query, pipe formatting)
2. Splunk parser validation (creates test job)
3. Returns warnings for best practices
4. Provides detailed error messages

### Query Execution

Execution flow:
1. Add `| head` limit if not present
2. Create search job with `exec_mode=blocking`
3. Poll job status until completion
4. Retrieve results in JSON format
5. Convert to `ExecutionResult` format
6. Clean up (cancel job)

**Automatic Safeguards:**
- Timeout enforcement (configurable)
- Row limit enforcement (via `head` command)
- Error handling and reporting

### Search Job Polling

The provider polls search jobs with configurable interval:
- Default poll interval: 0.5 seconds
- Checks `is_done()` status
- Tracks progress and metrics
- Handles failures gracefully

## Usage Examples

### Basic Setup

```python
from text2x.providers import create_splunk_provider

provider = create_splunk_provider(
    host="splunk.example.com",
    port=8089,
    username="admin",
    password="changeme"
)
```

### Schema Retrieval

```python
schema = await provider.get_schema()

# Access indexes
for index in schema.tables:
    print(f"{index.name}: {index.row_count} events")

# Access sourcetypes
print(f"Sourcetypes: {schema.sourcetypes}")
```

### Query Validation

```python
query = "search index=main error | stats count by host"
result = await provider.validate_syntax(query)

if result.valid:
    print("Query is valid")
else:
    print(f"Error: {result.error}")
```

### Query Execution

```python
result = await provider.execute_query(
    "search index=web status=500 | head 100",
    limit=100
)

if result.success:
    print(f"Found {result.row_count} results")
    for row in result.sample_rows:
        print(row)
```

## Integration with Text2X Agents

### Schema Expert Agent

Retrieves and processes schema information:

```python
# Get schema
schema = await splunk_provider.get_schema()

# Find relevant indexes
relevant_indexes = [
    table for table in schema.tables
    if search_term in table.name.lower()
]

# Build context for LLM
schema_context = {
    "indexes": [idx.name for idx in relevant_indexes],
    "fields": [col.name for col in relevant_indexes[0].columns],
    "sourcetypes": schema.sourcetypes[:10],
}
```

### Query Builder Agent

Generates and validates SPL queries:

```python
# Generate query from natural language
spl_query = llm.generate_spl(
    user_input="Show me errors in web logs",
    schema_context=schema_context,
    examples=rag_examples
)

# Validate before execution
validation = await splunk_provider.validate_syntax(spl_query)

if not validation.valid:
    # Refine query based on validation error
    spl_query = llm.refine_spl(spl_query, validation.error)
```

### Validator Agent

Validates and executes queries:

```python
# Validate syntax
validation = await splunk_provider.validate_syntax(query)

if validation.valid:
    # Execute query
    result = await splunk_provider.execute_query(query)

    if result.success:
        # Check results make sense
        is_valid = validate_results(result, user_intent)
    else:
        # Report execution error
        error_feedback = analyze_error(result.error)
```

## Error Handling

### Common Errors

1. **Connection Errors**
   - Wrong host/port
   - Network issues
   - Authentication failure

2. **Syntax Errors**
   - Invalid SPL commands
   - Malformed queries
   - Unknown fields

3. **Execution Errors**
   - Timeout
   - Permission denied
   - Index not found

### Error Recovery

```python
try:
    result = await provider.execute_query(query)

    if not result.success:
        if "timeout" in result.error.lower():
            # Retry with longer timeout
            provider_config.timeout_seconds = 120
        elif "permission" in result.error.lower():
            # Request elevated privileges
            pass
        else:
            # Handle other errors
            pass

except Exception as e:
    # Handle unexpected errors
    logging.error(f"Query execution failed: {e}")
```

## Performance Considerations

### Schema Caching

Schema is cached for 1 hour to reduce API calls:

```python
# First call - fetches from Splunk
schema1 = await provider.get_schema()  # ~2-5 seconds

# Subsequent calls - from cache
schema2 = await provider.get_schema()  # ~0.001 seconds

# Force refresh
provider._schema_cache = None
schema3 = await provider.get_schema()  # ~2-5 seconds
```

### Query Optimization

Tips for faster queries:
1. Always specify time ranges: `earliest=-1h latest=now`
2. Use indexed fields for filtering
3. Limit results with `| head N`
4. Use stats instead of returning raw events
5. Filter early in the search pipeline

### Connection Pooling

The Splunk SDK manages connections automatically:
- Connections are reused across requests
- No explicit pooling needed
- Call `close()` to clean up

## Best Practices

### Query Safety

1. **Always use time ranges**: Prevents searching all data
2. **Set reasonable limits**: Use `head` command or `limit` parameter
3. **Validate before execution**: Catch syntax errors early
4. **Handle errors gracefully**: Check `result.success`

### Security

1. **Use token authentication**: More secure than passwords
2. **Enable SSL verification**: Set `verify=True` in production
3. **Use least privilege**: Grant minimal required permissions
4. **Rotate credentials**: Regular password/token rotation

### Monitoring

1. **Track execution time**: Use `execution_time_ms`
2. **Monitor error rates**: Log failed queries
3. **Set appropriate timeouts**: Based on query complexity
4. **Cache schema**: Avoid repeated schema fetches

## Testing

### Unit Tests

Located in `tests/test_splunk_provider.py`:
- Provider initialization
- Schema retrieval
- Query validation
- Query execution
- Search job management
- Error handling

Run tests:
```bash
pytest tests/test_splunk_provider.py -v
```

### Integration Tests

Requires running Splunk instance:
```bash
export SPLUNK_HOST=localhost
export SPLUNK_PORT=8089
export SPLUNK_USERNAME=admin
export SPLUNK_PASSWORD=changeme

pytest tests/test_splunk_provider.py --integration
```

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to Splunk
**Solutions**:
- Verify host and port are correct
- Check network connectivity
- Confirm Splunk is running
- Test with `curl https://host:8089`

### Authentication Failures

**Problem**: Authentication denied
**Solutions**:
- Verify username and password
- Check user has search permission
- Try token authentication
- Check user is not locked out

### SSL Errors

**Problem**: SSL certificate verification failed
**Solutions**:
- Set `verify=False` for development
- Install proper SSL certificates
- Use `scheme="http"` if SSL not available
- Configure certificate bundle path

### Query Timeouts

**Problem**: Queries timeout
**Solutions**:
- Increase timeout: `timeout_seconds=120`
- Optimize query (add time ranges, filters)
- Use stats instead of raw events
- Run query directly in Splunk to verify

### Schema Not Found

**Problem**: Empty schema or missing indexes
**Solutions**:
- Check user has permission to list indexes
- Verify indexes contain data
- Check app context is correct
- Try with `owner="admin"` and `app="search"`

## Future Enhancements

Planned features:
1. **Saved Search Support**: Execute saved searches
2. **Real-time Search**: Support for real-time search jobs
3. **Export Support**: Export results to CSV/JSON
4. **Alert Integration**: Query alert configurations
5. **Lookup Tables**: Support for lookups in queries
6. **Data Models**: Integration with data models
7. **Report Generation**: Generate reports from queries

## References

- [Splunk SDK Documentation](https://dev.splunk.com/python)
- [SPL Reference](https://docs.splunk.com/Documentation/Splunk/latest/SearchReference)
- [Text2X Design Document](../../../design.md)
- [Provider Base Class](./base.py)
- [Usage Examples](../../../examples/splunk_provider_example.py)

## Support

For issues and questions:
- File an issue on GitHub
- Check existing provider implementations (SQL, NoSQL)
- Review test cases for examples
- Consult Splunk SDK documentation
