# Text2X CLI Documentation

The Text2X CLI is a production-ready command-line interface for the Text2DSL system that allows users to convert natural language queries into executable database queries.

## Installation

```bash
# Install from source
cd text2DSL
pip install -e .

# Verify installation
text2x --version
```

## Quick Start

```bash
# List available providers
text2x providers list

# Submit a query
text2x query "Show all users over 18" -p postgres-main

# View conversation history
text2x conversation show <conversation-id>
```

## Configuration

The CLI uses a configuration file located at `~/.text2dsl/config.yaml`. You can create this file manually or use the example:

```bash
# Copy example configuration
cp config.yaml.example ~/.text2dsl/config.yaml

# Edit with your preferred editor
nano ~/.text2dsl/config.yaml
```

### Configuration Options

```yaml
# API connection settings
api_url: http://localhost:8000
timeout: 300  # Request timeout in seconds

# Query processing defaults
trace_level: none  # Options: none, summary, full
max_iterations: 3  # Maximum refinement iterations
confidence_threshold: 0.8  # Minimum confidence score (0.0-1.0)
enable_execution: false  # Whether to execute generated queries by default

# Debug settings
debug: false  # Show detailed error traces
```

### Configuration Management Commands

```bash
# Show current configuration
text2x config show

# Set a configuration value
text2x config set api_url http://production-api:8000
text2x config set trace_level summary

# Reset to defaults
text2x config reset
```

## Commands

### Query Commands

#### `text2x query`

Submit a natural language query to generate executable database queries.

**Usage:**
```bash
text2x query [OPTIONS] QUERY_TEXT
```

**Options:**
- `-p, --provider TEXT` - Database provider ID (required)
- `-c, --conversation-id TEXT` - Continue existing conversation (UUID)
- `--max-iterations INTEGER` - Maximum refinement iterations (default: 3)
- `--confidence-threshold FLOAT` - Minimum confidence score 0.0-1.0 (default: 0.8)
- `--trace [none|summary|full]` - Reasoning trace detail level (default: none)
- `--execute / --no-execute` - Execute the generated query
- `--json` - Output raw JSON response

**Examples:**

```bash
# Basic query
text2x query "Show all users over 18" -p postgres-main

# With execution enabled
text2x query "Show all orders from last month" -p postgres-main --execute

# Continue a conversation
text2x query "Filter by status = shipped" -c <conversation-id> -p postgres-main

# With detailed trace
text2x query "Count orders by status" -p postgres-main --trace full

# Get JSON output
text2x query "Show users" -p postgres-main --json
```

**Output:**

The command displays:
- Conversation and turn IDs
- Generated SQL query with syntax highlighting
- Confidence score and validation status
- Validation errors, warnings, and suggestions
- Execution results (if enabled)
- Reasoning trace (if requested)

### Conversation Commands

#### `text2x conversation show`

Display conversation details and history including all turns.

**Usage:**
```bash
text2x conversation show [OPTIONS] CONVERSATION_ID
```

**Options:**
- `--json` - Output raw JSON response

**Examples:**

```bash
# Show conversation details
text2x conversation show 550e8400-e29b-41d4-a716-446655440000

# Get JSON output
text2x conversation show 550e8400-e29b-41d4-a716-446655440000 --json
```

**Output:**

The command displays:
- Conversation metadata (provider, status, turn count)
- Created and updated timestamps
- All conversation turns with queries and results

### Provider Commands

#### `text2x providers list`

List all available database providers and their connection status.

**Usage:**
```bash
text2x providers list [OPTIONS]
```

**Options:**
- `--json` - Output raw JSON response

**Examples:**

```bash
# List all providers
text2x providers list

# Get JSON output
text2x providers list --json
```

**Output:**

The command displays a table with:
- Provider ID
- Provider name
- Provider type (postgresql, athena, opensearch, etc.)
- Connection status
- Number of tables
- Last schema refresh timestamp

#### `text2x providers show`

Show detailed information about a specific provider.

**Usage:**
```bash
text2x providers show [OPTIONS] PROVIDER_ID
```

**Options:**
- `--json` - Output raw JSON response

**Examples:**

```bash
# Show provider details
text2x providers show postgres-main

# Get JSON output
text2x providers show postgres-main --json
```

**Output:**

The command displays:
- Provider ID, name, and type
- Description
- Connection status
- Table count
- Schema refresh timestamps
- Created and updated timestamps

## Global Options

All commands support these global options:

- `--api-url TEXT` - Override API base URL (env: `TEXT2X_API_URL`)
- `--version` - Show CLI version
- `--help` - Show help message

**Examples:**

```bash
# Use custom API URL
text2x --api-url http://staging-api:8000 providers list

# Use environment variable
export TEXT2X_API_URL=http://production-api:8000
text2x providers list

# Show version
text2x --version

# Show help
text2x --help
text2x query --help
```

## Output Formats

### Pretty-Printed Output (Default)

By default, the CLI displays formatted, human-readable output with:
- Color coding for different elements
- Tables for structured data
- Syntax highlighting for SQL queries
- Tree views for reasoning traces
- Icons and symbols for status indicators

### JSON Output

Use the `--json` flag to get raw JSON responses for programmatic use:

```bash
text2x query "Show users" -p postgres-main --json | jq '.generated_query'
```

## Error Handling

The CLI provides user-friendly error messages for common scenarios:

### Connection Errors

```bash
$ text2x providers list
Connection Error: Failed to connect to API: Connection refused
```

**Solution:** Ensure the Text2X API is running at the configured URL.

### Invalid Provider

```bash
$ text2x query "Show users" -p invalid-provider
Error: Provider invalid-provider not found
```

**Solution:** Use `text2x providers list` to see available providers.

### Validation Errors

If a query fails validation, the CLI displays:
- Validation errors with details
- Warnings for potential issues
- Suggestions for improvements

### API Errors

The CLI handles API errors gracefully:
- 400 Bad Request: Invalid input
- 404 Not Found: Resource not found
- 500 Internal Server Error: Server error

## Advanced Usage

### Scripting and Automation

The CLI is designed for both interactive and programmatic use:

```bash
#!/bin/bash
# Generate queries for multiple providers

PROVIDERS=("postgres-main" "athena-analytics" "opensearch-logs")
QUERY="Show all records from last 7 days"

for provider in "${PROVIDERS[@]}"; do
    echo "Processing: $provider"
    text2x query "$QUERY" -p "$provider" --json > "${provider}-result.json"
done
```

### Piping and Integration

```bash
# Extract just the generated query
text2x query "Show users" -p postgres-main --json | jq -r '.generated_query'

# Check if query has high confidence
RESULT=$(text2x query "Show users" -p postgres-main --json)
CONFIDENCE=$(echo "$RESULT" | jq -r '.confidence_score')
if (( $(echo "$CONFIDENCE > 0.9" | bc -l) )); then
    echo "High confidence query"
fi
```

### Multi-Turn Conversations

```bash
# Start a conversation
RESULT=$(text2x query "Show all users" -p postgres-main --json)
CONV_ID=$(echo "$RESULT" | jq -r '.conversation_id')

# Continue the conversation
text2x query "Filter by age over 18" -c "$CONV_ID" -p postgres-main
text2x query "Order by created date" -c "$CONV_ID" -p postgres-main

# View the full conversation
text2x conversation show "$CONV_ID"
```

## Performance Considerations

### Timeout Settings

Adjust timeout for complex queries:

```bash
text2x config set timeout 600  # 10 minutes
```

### Caching

The API caches:
- Schema information
- RAG examples
- Common queries

No client-side caching is currently implemented.

## Troubleshooting

### CLI not found after installation

```bash
# Ensure pip bin directory is in PATH
pip show text2dsl
python -m text2x.cli --help
```

### Configuration not loading

```bash
# Check configuration file location
ls -la ~/.text2dsl/config.yaml

# Verify YAML syntax
python -c "import yaml; yaml.safe_load(open('~/.text2dsl/config.yaml'))"
```

### API connection issues

```bash
# Test API health directly
curl http://localhost:8000/health

# Check API URL configuration
text2x config show | grep api_url
```

### Debug mode

Enable debug mode for detailed error traces:

```bash
text2x config set debug true
```

## Examples

### Basic Workflow

```bash
# 1. Check available providers
text2x providers list

# 2. Submit a query
text2x query "Show all active users" -p postgres-main

# 3. Continue with refinements
text2x query "Order by registration date" -c <conversation-id> -p postgres-main

# 4. View full conversation
text2x conversation show <conversation-id>
```

### Production Query Workflow

```bash
# Generate query with high confidence threshold
text2x query "Critical orders from last hour" \
    -p postgres-main \
    --confidence-threshold 0.95 \
    --max-iterations 5 \
    --trace full

# If confident, execute the query
text2x query "Critical orders from last hour" \
    -p postgres-main \
    --execute \
    --json > results.json
```

### Schema Exploration

```bash
# List all providers and their tables
text2x providers list

# Get detailed provider information
text2x providers show postgres-main

# Get full schema (via API, not implemented in CLI yet)
curl http://localhost:8000/api/v1/providers/postgres-main/schema | jq
```

## Integration with Other Tools

### jq (JSON processing)

```bash
# Extract specific fields
text2x query "Show users" -p postgres-main --json | jq '.generated_query'
text2x query "Show users" -p postgres-main --json | jq '.confidence_score'

# Filter by confidence
text2x query "Show users" -p postgres-main --json | jq 'select(.confidence_score > 0.9)'
```

### watch (Monitoring)

```bash
# Monitor provider status
watch -n 10 'text2x providers list'
```

### Scripts and CI/CD

```bash
# Validate queries in CI
#!/bin/bash
set -e

QUERIES=(
    "Show all users"
    "Count orders by status"
    "Revenue by month"
)

for query in "${QUERIES[@]}"; do
    RESULT=$(text2x query "$query" -p postgres-main --json)
    CONFIDENCE=$(echo "$RESULT" | jq -r '.confidence_score')

    if (( $(echo "$CONFIDENCE < 0.8" | bc -l) )); then
        echo "FAIL: Low confidence for: $query"
        exit 1
    fi
done

echo "All queries validated successfully"
```

## Support and Feedback

For issues, questions, or feature requests:
- Check the API documentation: `/docs` endpoint
- Review the design document: `design.md`
- Check logs with `--trace full` for debugging

## Version History

- **0.1.0** - Initial release
  - Basic query submission
  - Conversation management
  - Provider listing
  - Configuration management
  - Pretty-printed output with Rich
  - JSON output mode
  - Progress indicators
  - Error handling

## Future Enhancements

Planned features:
- Interactive mode with prompt
- WebSocket streaming support
- Local query history
- Query templates and favorites
- Schema browsing commands
- RAG example management
- Expert review queue integration
- Auto-completion for providers
- Query syntax validation before submission
