# Text2X CLI - Production-Ready Command Line Interface

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful command-line interface for converting natural language queries into executable database queries using multi-agent AI.

## Features

- 🚀 **Fast Query Submission** - Submit natural language queries and get SQL in seconds
- 💬 **Multi-Turn Conversations** - Refine queries through interactive conversations
- 🔍 **Multiple Providers** - Support for PostgreSQL, Athena, OpenSearch, Splunk, MongoDB, Redis
- 🎨 **Beautiful Output** - Rich formatting with syntax highlighting and tables
- 📊 **Query Execution** - Optionally execute queries and view results
- 🔬 **Reasoning Traces** - Deep dive into AI decision-making process
- ⚙️ **Configurable** - YAML configuration with sensible defaults
- 🛠️ **Scriptable** - JSON output mode for automation and integration

## Quick Start

### Installation

```bash
# Install from source
cd text2DSL
pip install -e .

# Verify installation
text2x --version
```

### First Query

```bash
# 1. List available providers
text2x providers list

# 2. Submit your first query
text2x query "Show all users over 18" -p postgres-main

# 3. Execute the query
text2x query "Show all users over 18" -p postgres-main --execute
```

## Usage Examples

### Basic Query

```bash
text2x query "Show all orders from last month" -p postgres-main
```

Output:
```
╭────────────╮
│ Query Result │
╰────────────╯

Conversation ID   a7b3c4d5-1234-5678-90ab-cdef12345678
Turn ID          t1b2c3d4-5678-90ab-cdef-123456789012
Confidence Score  95.50%
Validation Status valid
Iterations       2

Generated Query:
╭──────────────────────────────────────────╮
│ 1 SELECT *                               │
│ 2 FROM orders                            │
│ 3 WHERE created_at >= NOW() - INTERVAL  │
│ 4   '1 month';                           │
╰──────────────────────────────────────────╯

To continue this conversation, use: --conversation-id a7b3c4d5-1234-5678-90ab-cdef12345678
```

### With Query Execution

```bash
text2x query "Count users by country" -p postgres-main --execute
```

Output includes execution results:
```
Execution Successful
  Rows returned: 5
  Execution time: 42ms

Result Data:
╭─────────┬───────╮
│ country │ count │
├─────────┼───────┤
│ US      │ 1234  │
│ UK      │ 567   │
│ CA      │ 890   │
│ AU      │ 345   │
│ DE      │ 678   │
╰─────────┴───────╯
```

### Multi-Turn Conversation

```bash
# Start conversation
text2x query "Show all users" -p postgres-main

# Continue conversation (use conversation ID from previous output)
text2x query "Filter by active status" -c a7b3c4d5-1234-5678-90ab-cdef12345678 -p postgres-main

# Add more refinements
text2x query "Order by registration date descending" -c a7b3c4d5-1234-5678-90ab-cdef12345678 -p postgres-main

# View full conversation history
text2x conversation show a7b3c4d5-1234-5678-90ab-cdef12345678
```

### With Reasoning Trace

```bash
text2x query "Show revenue by product category" -p postgres-main --trace full
```

Output includes detailed trace:
```
Reasoning Trace:
🔍 Query Processing
├── Orchestrator (1234ms)
│   ├── Schema Expert (234ms)
│   │   ├── Tokens: 1500 in / 300 out
│   │   ├── tables_found: ['orders', 'products', 'order_items']
│   │   └── join_strategy: product_id
│   ├── RAG Retrieval (123ms)
│   │   ├── Tokens: 800 in / 200 out
│   │   ├── examples_retrieved: 3
│   │   └── similarity_score: 0.89
│   ├── Query Builder (567ms)
│   │   ├── Tokens: 2000 in / 400 out
│   │   ├── Iterations: 2
│   │   └── refinement_reason: Added GROUP BY clause
│   ├── Validator (89ms)
│   │   ├── Tokens: 1200 in / 150 out
│   │   └── validation_status: valid
│   └── Summary
│       ├── Total Tokens: 5500 in / 1050 out
│       └── Total Cost: $0.0234
```

### JSON Output for Scripting

```bash
# Get just the generated query
text2x query "Show users" -p postgres-main --json | jq -r '.generated_query'

# Check confidence score
RESULT=$(text2x query "Show users" -p postgres-main --json)
CONFIDENCE=$(echo "$RESULT" | jq -r '.confidence_score')
if (( $(echo "$CONFIDENCE > 0.9" | bc -l) )); then
    echo "High confidence query"
fi

# Extract conversation ID for continuation
CONV_ID=$(text2x query "Show users" -p postgres-main --json | jq -r '.conversation_id')
text2x query "Filter by age > 18" -c "$CONV_ID" -p postgres-main
```

## Configuration

### Configuration File

Create `~/.text2dsl/config.yaml`:

```yaml
# API connection
api_url: http://localhost:8000
timeout: 300

# Query processing
trace_level: none
max_iterations: 3
confidence_threshold: 0.8
enable_execution: false

# Debug
debug: false
```

### Configuration Commands

```bash
# View current configuration
text2x config show

# Set values
text2x config set api_url http://production-api:8000
text2x config set trace_level summary
text2x config set confidence_threshold 0.9

# Reset to defaults
text2x config reset
```

### Environment Variables

```bash
# Override API URL via environment variable
export TEXT2X_API_URL=http://production-api:8000
text2x providers list
```

## All Commands

### Query Commands

```bash
# Basic query
text2x query "QUERY" -p PROVIDER_ID

# With options
text2x query "QUERY" -p PROVIDER_ID \
  --max-iterations 5 \
  --confidence-threshold 0.95 \
  --trace full \
  --execute

# Continue conversation
text2x query "QUERY" -c CONVERSATION_ID -p PROVIDER_ID

# JSON output
text2x query "QUERY" -p PROVIDER_ID --json
```

### Provider Commands

```bash
# List all providers
text2x providers list

# Show provider details
text2x providers show PROVIDER_ID

# JSON output
text2x providers list --json
text2x providers show PROVIDER_ID --json
```

### Conversation Commands

```bash
# Show conversation history
text2x conversation show CONVERSATION_ID

# JSON output
text2x conversation show CONVERSATION_ID --json
```

### Configuration Commands

```bash
# Show configuration
text2x config show

# Set configuration value
text2x config set KEY VALUE

# Reset configuration
text2x config reset
```

### Global Options

```bash
# Custom API URL
text2x --api-url http://staging:8000 COMMAND

# Enable debug mode
text2x --debug COMMAND

# Show version
text2x --version

# Show help
text2x --help
text2x COMMAND --help
```

## Use Cases

### 1. Development & Testing

```bash
# Test query generation during development
text2x query "Show all active users" -p dev-postgres

# Test with high confidence threshold
text2x query "Critical query" -p dev-postgres --confidence-threshold 0.95

# Debug query issues
text2x query "Complex query" -p dev-postgres --trace full --debug
```

### 2. Data Analysis

```bash
# Generate and execute analytical queries
text2x query "Revenue by product category last quarter" \
  -p analytics-db \
  --execute

# Iteratively refine analysis
text2x query "Show sales trends" -p analytics-db
text2x query "Break down by region" -c <conv-id> -p analytics-db
text2x query "Compare to last year" -c <conv-id> -p analytics-db
```

### 3. CI/CD Pipelines

```bash
#!/bin/bash
# Validate queries before deployment

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

echo "All queries validated"
```

### 4. Automation & Scripting

```bash
#!/bin/bash
# Generate daily report queries

PROVIDERS=("postgres-main" "athena-analytics" "opensearch-logs")
QUERY="Show activity from last 24 hours"

for provider in "${PROVIDERS[@]}"; do
  echo "Processing: $provider"

  RESULT=$(text2x query "$QUERY" -p "$provider" --json)
  QUERY_SQL=$(echo "$RESULT" | jq -r '.generated_query')

  # Save to file
  echo "$QUERY_SQL" > "daily_report_${provider}.sql"

  # Execute if high confidence
  CONFIDENCE=$(echo "$RESULT" | jq -r '.confidence_score')
  if (( $(echo "$CONFIDENCE > 0.9" | bc -l) )); then
    text2x query "$QUERY" -p "$provider" --execute --json > "result_${provider}.json"
  fi
done
```

### 5. Monitoring & Operations

```bash
# Monitor provider health
watch -n 10 'text2x providers list'

# Check query quality
text2x query "Critical operational query" -p prod-db \
  --confidence-threshold 0.95 \
  --max-iterations 5 \
  --trace summary
```

## Architecture

The CLI is built with:

- **Click**: Command-line interface framework
- **Rich**: Beautiful terminal output
- **HTTPX**: Async HTTP client
- **PyYAML**: Configuration file parsing

## Error Handling

The CLI provides clear, actionable error messages:

```bash
# Connection error
$ text2x providers list
Connection Error: Failed to connect to API: Connection refused

# Invalid provider
$ text2x query "Show users" -p invalid
Error: Provider invalid not found

# Validation errors
$ text2x query "Show users" -p postgres-main
Validation Errors:
  ✗ Table 'users' not found in schema
  ⚠ Consider using table 'user_accounts' instead
```

## Performance

- **Fast Startup**: < 100ms CLI initialization
- **Streaming**: Progress indicators for long operations
- **Caching**: Server-side schema and RAG caching
- **Timeouts**: Configurable request timeouts (default: 300s)

## Troubleshooting

### CLI Not Found After Installation

```bash
# Verify installation
pip show text2dsl

# Use module syntax
python3 -m text2x.cli --help

# Check PATH
which text2x
```

### Configuration Issues

```bash
# Check configuration file
cat ~/.text2dsl/config.yaml

# Verify YAML syntax
python3 -c "import yaml; yaml.safe_load(open('~/.text2dsl/config.yaml'))"

# Reset configuration
text2x config reset
```

### API Connection Issues

```bash
# Test API health
curl http://localhost:8000/health

# Check configured URL
text2x config show | grep api_url

# Override URL temporarily
text2x --api-url http://localhost:8000 providers list
```

## Development

### Running from Source

```bash
# Run CLI module directly
python3 -m text2x.cli --help

# Run specific command
python3 -m text2x.cli query "Show users" -p postgres-main
```

### Testing

```bash
# Run demo script
./test_cli_demo.sh

# Test all commands
python3 -m text2x.cli --help
python3 -m text2x.cli query --help
python3 -m text2x.cli providers list --help
python3 -m text2x.cli conversation show --help
python3 -m text2x.cli config show
```

## Documentation

- **CLI Documentation**: [CLI.md](./CLI.md)
- **Usage Guide**: [CLI_USAGE.md](./CLI_USAGE.md)
- **API Documentation**: Available at `/docs` endpoint
- **Design Document**: [design.md](./design.md)

## Roadmap

Future enhancements planned:

- [ ] Interactive mode with prompt
- [ ] WebSocket streaming support
- [ ] Local query history
- [ ] Query templates and favorites
- [ ] Schema browsing commands
- [ ] RAG example management
- [ ] Expert review queue integration
- [ ] Auto-completion for providers
- [ ] Query syntax validation before submission
- [ ] Export results to CSV/JSON files
- [ ] Query performance analytics
- [ ] Multi-provider query comparison

## Contributing

Contributions are welcome! Areas for improvement:

1. Additional output formats (CSV, Markdown)
2. Interactive mode
3. Query history management
4. Performance optimizations
5. Additional provider support
6. Enhanced error messages

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or feature requests:

1. Check this documentation
2. Review CLI.md for detailed command reference
3. Enable debug mode: `--debug`
4. Use trace mode: `--trace full`
5. Check API documentation at `/docs`

## Version

Current Version: **0.1.0**

## Credits

Built with:
- [Click](https://click.palletsprojects.com/) - Command line interface framework
- [Rich](https://rich.readthedocs.io/) - Beautiful terminal output
- [HTTPX](https://www.python-httpx.org/) - Async HTTP client
- [PyYAML](https://pyyaml.org/) - YAML parser
