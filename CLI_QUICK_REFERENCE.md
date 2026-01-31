# Text2X CLI Quick Reference

## Installation

```bash
pip install -e .
text2x --version
```

## Configuration

```bash
# View config
text2x config show

# Set config
text2x config set api_url http://localhost:8000
text2x config set trace_level summary
text2x config set confidence_threshold 0.9

# Reset config
text2x config reset
```

## Common Commands

### Submit Query

```bash
# Basic
text2x query "Show all users" -p postgres-main

# With execution
text2x query "Show orders" -p postgres-main --execute

# High confidence
text2x query "Critical query" -p postgres-main --confidence-threshold 0.95

# With trace
text2x query "Complex query" -p postgres-main --trace full
```

### Multi-Turn Conversation

```bash
# Start
text2x query "Show all users" -p postgres-main
# Note the conversation ID from output

# Continue
text2x query "Filter by age > 18" -c <conv-id> -p postgres-main
text2x query "Order by name" -c <conv-id> -p postgres-main

# View history
text2x conversation show <conv-id>
```

### Providers

```bash
# List all
text2x providers list

# Show details
text2x providers show postgres-main

# JSON output
text2x providers list --json
```

## Options Reference

### Query Options

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `-p, --provider` | string | Provider ID (required) | `-p postgres-main` |
| `-c, --conversation-id` | UUID | Continue conversation | `-c abc-123-def` |
| `--max-iterations` | int (1-10) | Max refinement loops | `--max-iterations 5` |
| `--confidence-threshold` | float (0-1) | Min confidence | `--confidence-threshold 0.95` |
| `--trace` | enum | Trace level | `--trace full` |
| `--execute` | flag | Execute query | `--execute` |
| `--json` | flag | JSON output | `--json` |

### Global Options

| Option | Description | Example |
|--------|-------------|---------|
| `--api-url` | Override API URL | `--api-url http://localhost:8000` |
| `--debug` | Enable debug mode | `--debug` |
| `--version` | Show version | `--version` |
| `--help` | Show help | `--help` |

## Configuration Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `api_url` | string | `http://localhost:8000` | API base URL |
| `timeout` | int | `300` | Request timeout (seconds) |
| `trace_level` | enum | `none` | Trace level: none/summary/full |
| `max_iterations` | int | `3` | Max refinement iterations |
| `confidence_threshold` | float | `0.8` | Min confidence score |
| `enable_execution` | bool | `false` | Execute by default |
| `debug` | bool | `false` | Show debug traces |

## Scripting Examples

### Extract Query

```bash
text2x query "Show users" -p postgres-main --json | jq -r '.generated_query'
```

### Check Confidence

```bash
RESULT=$(text2x query "Show users" -p postgres-main --json)
CONFIDENCE=$(echo "$RESULT" | jq -r '.confidence_score')
if (( $(echo "$CONFIDENCE > 0.9" | bc -l) )); then
  echo "High confidence"
fi
```

### Get Conversation ID

```bash
CONV_ID=$(text2x query "Show users" -p postgres-main --json | jq -r '.conversation_id')
text2x query "Filter by age > 18" -c "$CONV_ID" -p postgres-main
```

### Batch Processing

```bash
for provider in postgres-main athena-analytics; do
  text2x query "Show data from last week" -p "$provider" --json > "${provider}.json"
done
```

## Output Formatting

### Pretty Mode (Default)

- Colored output with syntax highlighting
- Tables for structured data
- Tree views for traces
- Progress indicators
- Status icons (🟢/🔴, ✗/⚠/ℹ)

### JSON Mode

- Raw JSON response
- Suitable for parsing with `jq`
- All fields included
- No color/formatting

## Environment Variables

```bash
export TEXT2X_API_URL=http://production:8000
text2x query "Show users" -p postgres-main
```

## Troubleshooting

### CLI Not Found

```bash
python3 -m text2x.cli --help
```

### Connection Error

```bash
# Test API
curl http://localhost:8000/health

# Check config
text2x config show | grep api_url
```

### Invalid Provider

```bash
# List available providers
text2x providers list
```

### Debug Mode

```bash
text2x --debug query "Show users" -p postgres-main
```

## File Locations

- Config: `~/.text2dsl/config.yaml`
- Example: `config.yaml.example`

## Exit Codes

- `0`: Success
- `1`: Error (connection, API, validation, etc.)

## Tips

1. **Start Simple**: Begin with basic queries, refine iteratively
2. **Use Traces**: Enable traces for debugging: `--trace full`
3. **Check Confidence**: Use thresholds to ensure quality: `--confidence-threshold 0.95`
4. **Multi-Turn**: Use conversations for iterative refinement
5. **Test First**: Review queries before using `--execute`
6. **Script with JSON**: Use `--json` flag for automation
7. **Set Defaults**: Configure common settings in config file

## Common Patterns

### Development Workflow

```bash
# 1. Check providers
text2x providers list

# 2. Test query
text2x query "Show all users" -p dev-db

# 3. Refine
text2x query "Filter by active" -c <conv-id> -p dev-db

# 4. Execute when ready
text2x query "Final query" -c <conv-id> -p dev-db --execute
```

### Production Workflow

```bash
# High confidence + trace
text2x query "Critical query" -p prod-db \
  --confidence-threshold 0.95 \
  --max-iterations 5 \
  --trace summary
```

### Data Analysis

```bash
# Generate + execute
text2x query "Revenue by category" -p analytics-db --execute

# Extract for external use
text2x query "Complex analysis" -p analytics-db --json | jq -r '.generated_query' > query.sql
```

## Version

Current: **0.1.0**

## Documentation

- Full docs: [CLI.md](./CLI.md)
- Usage guide: [CLI_USAGE.md](./CLI_USAGE.md)
- Features: [CLI_README.md](./CLI_README.md)
