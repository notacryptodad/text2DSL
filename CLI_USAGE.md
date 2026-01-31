# Text2X CLI Usage Guide

## Overview

The Text2X CLI is a production-ready command-line interface for converting natural language queries into executable database queries using a multi-agent AI system.

## Installation

```bash
# Install from source
cd text2DSL
pip install -e .

# Verify installation
text2x --version
```

## Configuration

The CLI uses a YAML configuration file at `~/.text2dsl/config.yaml`.

### Initial Setup

```bash
# Copy example configuration
cp config.yaml.example ~/.text2dsl/config.yaml

# View current configuration
text2x config show

# Set configuration values
text2x config set api_url http://localhost:8000
text2x config set trace_level summary
text2x config set confidence_threshold 0.9
text2x config set debug true

# Reset to defaults
text2x config reset
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `api_url` | string | `http://localhost:8000` | API server URL |
| `timeout` | integer | `300` | Request timeout in seconds |
| `trace_level` | enum | `none` | Trace detail level: `none`, `summary`, `full` |
| `max_iterations` | integer | `3` | Maximum refinement iterations (1-10) |
| `confidence_threshold` | float | `0.8` | Minimum confidence score (0.0-1.0) |
| `enable_execution` | boolean | `false` | Execute queries by default |
| `debug` | boolean | `false` | Show detailed error traces |

## Commands

### Query Commands

#### Submit a Query

```bash
text2x query "NATURAL_LANGUAGE_QUERY" -p PROVIDER_ID [OPTIONS]
```

**Options:**
- `-p, --provider TEXT` - Database provider ID (required)
- `-c, --conversation-id TEXT` - Continue existing conversation (UUID)
- `--max-iterations INTEGER` - Maximum refinement iterations (1-10)
- `--confidence-threshold FLOAT` - Minimum confidence score (0.0-1.0)
- `--trace [none|summary|full]` - Reasoning trace detail level
- `--execute / --no-execute` - Execute the generated query
- `--json` - Output raw JSON response

**Examples:**

```bash
# Basic query
text2x query "Show all users over 18" -p postgres-main

# With execution enabled
text2x query "Show all orders from last month" -p postgres-main --execute

# Continue a conversation
text2x query "Filter by status = shipped" -c a7b3c4d5-1234-5678-90ab-cdef12345678 -p postgres-main

# With detailed trace
text2x query "Count orders by status" -p postgres-main --trace full

# High confidence threshold
text2x query "Critical orders from last hour" -p postgres-main --confidence-threshold 0.95

# JSON output for scripting
text2x query "Show users" -p postgres-main --json | jq '.generated_query'
```

**Output Format:**

The command displays:
- Conversation and turn IDs
- Generated SQL query with syntax highlighting
- Confidence score and validation status
- Number of iterations
- Validation errors, warnings, and suggestions
- Execution results (if enabled) with data preview
- Reasoning trace (if requested)
- Hint for continuing the conversation

### Conversation Commands

#### Show Conversation

```bash
text2x conversation show CONVERSATION_ID [OPTIONS]
```

**Options:**
- `--json` - Output raw JSON response

**Examples:**

```bash
# Show conversation details
text2x conversation show a7b3c4d5-1234-5678-90ab-cdef12345678

# Get JSON output
text2x conversation show a7b3c4d5-1234-5678-90ab-cdef12345678 --json
```

**Output Format:**

The command displays:
- Conversation metadata (ID, provider, status, turn count)
- Created and updated timestamps
- All conversation turns with:
  - Turn number
  - User input
  - Generated query
  - Confidence score
  - Validation status

### Provider Commands

#### List Providers

```bash
text2x providers list [OPTIONS]
```

**Options:**
- `--json` - Output raw JSON response

**Examples:**

```bash
# List all providers
text2x providers list

# Get JSON output for scripting
text2x providers list --json | jq '.[] | select(.connection_status == "connected")'
```

**Output Format:**

The command displays a table with:
- Provider ID
- Provider name
- Provider type (postgresql, athena, opensearch, splunk, mongodb, redis)
- Connection status (🟢 connected / 🔴 disconnected)
- Number of tables
- Last schema refresh timestamp

#### Show Provider Details

```bash
text2x providers show PROVIDER_ID [OPTIONS]
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

**Output Format:**

The command displays:
- Provider ID, name, and type
- Description
- Connection status
- Table count
- Last schema refresh timestamp
- Created and updated timestamps

### Configuration Commands

#### Show Configuration

```bash
text2x config show
```

Displays the current configuration with all settings.

#### Set Configuration Value

```bash
text2x config set KEY VALUE
```

**Examples:**

```bash
text2x config set api_url http://production-api:8000
text2x config set trace_level full
text2x config set confidence_threshold 0.85
text2x config set enable_execution true
text2x config set debug false
```

The command validates:
- Key names against known configuration options
- Value types (integer, float, boolean, string)
- Value ranges (e.g., confidence_threshold 0.0-1.0)
- Enum values (e.g., trace_level: none, summary, full)

#### Reset Configuration

```bash
text2x config reset
```

Resets all configuration to default values. Requires confirmation.

## Global Options

All commands support these global options:

- `--api-url TEXT` - Override API base URL (env: `TEXT2X_API_URL`)
- `--debug` - Enable debug mode with detailed error traces
- `--version` - Show CLI version
- `--help` - Show help message

**Examples:**

```bash
# Use custom API URL
text2x --api-url http://staging-api:8000 providers list

# Use environment variable
export TEXT2X_API_URL=http://production-api:8000
text2x providers list

# Enable debug mode
text2x --debug query "Show users" -p postgres-main
```

## Output Formats

### Pretty-Printed Output (Default)

By default, the CLI displays formatted, human-readable output with:
- Color coding for different elements
- Tables for structured data
- Syntax highlighting for SQL queries
- Tree views for reasoning traces
- Icons and symbols for status indicators
- Progress spinners for long operations

### JSON Output

Use the `--json` flag to get raw JSON responses for programmatic use:

```bash
# Extract specific fields
text2x query "Show users" -p postgres-main --json | jq '.generated_query'
text2x query "Show users" -p postgres-main --json | jq '.confidence_score'

# Filter by confidence
text2x query "Show users" -p postgres-main --json | jq 'select(.confidence_score > 0.9)'

# Get provider IDs
text2x providers list --json | jq '.[].id'
```

## Error Handling

The CLI provides user-friendly error messages for common scenarios:

### Connection Errors

```
Connection Error: Failed to connect to API: Connection refused
```

**Solution:** Ensure the Text2X API is running at the configured URL.

### Invalid Provider

```
Error: Provider invalid-provider not found
```

**Solution:** Use `text2x providers list` to see available providers.

### Validation Errors

If a query fails validation, the CLI displays:
- ✗ Validation errors with details
- ⚠ Warnings for potential issues
- ℹ Suggestions for improvements

### API Errors

- 400 Bad Request: Invalid input parameters
- 404 Not Found: Resource not found
- 500 Internal Server Error: Server error

### Debug Mode

Enable debug mode for detailed error traces:

```bash
# Via command line
text2x --debug query "Show users" -p postgres-main

# Via configuration
text2x config set debug true
```

## Advanced Usage

### Scripting and Automation

```bash
#!/bin/bash
# Generate queries for multiple providers

PROVIDERS=("postgres-main" "athena-analytics" "opensearch-logs")
QUERY="Show all records from last 7 days"

for provider in "${PROVIDERS[@]}"; do
    echo "Processing: $provider"
    text2x query "$QUERY" -p "$provider" --json > "${provider}-result.json"

    # Check confidence score
    CONFIDENCE=$(jq -r '.confidence_score' "${provider}-result.json")
    echo "  Confidence: $CONFIDENCE"
done
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

### CI/CD Integration

```bash
#!/bin/bash
# Validate queries in CI pipeline
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

### Data Pipeline Integration

```bash
# Extract query and execute with psql
GENERATED_SQL=$(text2x query "Show active users from last 30 days" \
    -p postgres-main --json | jq -r '.generated_query')

echo "$GENERATED_SQL" | psql -h localhost -U user -d database
```

### Monitoring

```bash
# Monitor provider status
watch -n 10 'text2x providers list'

# Check API health
while true; do
    text2x providers list > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "$(date): API is healthy"
    else
        echo "$(date): API is down!"
    fi
    sleep 60
done
```

## Tips and Best Practices

1. **Use Configuration File**: Set common options in `~/.text2dsl/config.yaml` to avoid repeating them.

2. **Start with Low Confidence**: Use lower confidence thresholds (0.7-0.8) for exploratory queries, higher (0.9+) for production.

3. **Use Traces for Debugging**: Enable `--trace full` when queries don't work as expected to understand the AI reasoning.

4. **Multi-Turn for Refinement**: Use conversation IDs to iteratively refine queries instead of crafting complex queries upfront.

5. **Test Before Execution**: Always review generated queries before enabling `--execute`.

6. **Use JSON for Automation**: Use `--json` flag with `jq` for parsing in scripts and pipelines.

7. **Check Provider Status**: Use `text2x providers list` to verify connections before submitting queries.

8. **Environment-Specific URLs**: Use `TEXT2X_API_URL` environment variable for different environments.

## Troubleshooting

### CLI Not Found

```bash
# Check installation
pip show text2dsl

# Use module syntax
python3 -m text2x.cli --help

# Check PATH
echo $PATH | grep -o "[^:]*bin"
```

### Configuration Not Loading

```bash
# Check file location
ls -la ~/.text2dsl/config.yaml

# Verify YAML syntax
python3 -c "import yaml; print(yaml.safe_load(open('~/.text2dsl/config.yaml')))"

# Reset and reconfigure
text2x config reset
```

### API Connection Issues

```bash
# Test API directly
curl http://localhost:8000/health

# Check configuration
text2x config show | grep api_url

# Override URL
text2x --api-url http://localhost:8000 providers list
```

### Permission Errors

```bash
# Check config directory permissions
ls -la ~/.text2dsl/

# Create directory if missing
mkdir -p ~/.text2dsl/
chmod 755 ~/.text2dsl/
```

## Feature Highlights

### ✅ Implemented Features

1. **Query Submission**
   - Natural language to SQL conversion
   - Multi-turn conversations
   - Iterative refinement
   - Confidence scoring
   - Query execution

2. **Conversation Management**
   - View conversation history
   - Continue existing conversations
   - Multi-turn context

3. **Provider Management**
   - List all providers
   - View provider details
   - Connection status
   - Schema information

4. **Configuration Management**
   - YAML configuration file
   - Set individual values
   - Reset to defaults
   - Type validation

5. **Output Formatting**
   - Pretty-printed output with Rich
   - Syntax highlighting for SQL
   - Tables for structured data
   - Tree views for traces
   - JSON output mode

6. **Error Handling**
   - User-friendly error messages
   - Connection error handling
   - Validation feedback
   - Debug mode

7. **Progress Indicators**
   - Spinner for API calls
   - Status messages
   - Transient progress display

## Version Information

- **Current Version**: 0.1.0
- **Python Required**: >= 3.11
- **Dependencies**: click, rich, httpx, pyyaml

## Support

For issues, questions, or feature requests:
- Check the API documentation: `/docs` endpoint
- Review the design document: `design.md`
- Use debug mode: `--debug` flag
- Enable full traces: `--trace full`
