# Text2DSL

A multi-agent system that converts natural language queries into executable queries (SQL, NoSQL, Splunk SPL, etc.) with >=95% accuracy through iterative refinement, RAG-powered examples, and expert feedback loops.

## Features

- **Multi-Agent Architecture**: Orchestrator, Schema Expert, Query Builder, Validator, and RAG Retrieval agents
- **Pluggable Providers**: SQL (PostgreSQL, MySQL), NoSQL (MongoDB), Splunk SPL, and custom plugins
- **RAG-Powered**: OpenSearch-backed example retrieval for improved accuracy
- **Expert Review Loop**: Continuous learning from human expert corrections
- **Full Observability**: Reasoning traces, metrics, and audit logs

## Quick Start

```bash
# Install dependencies
make install

# Start infrastructure (PostgreSQL, Redis, OpenSearch)
make docker-up

# Run the API server
uvicorn src.text2x.api.main:app --reload
```

## Architecture

See [design.md](./design.md) for the complete architecture documentation.

## Project Structure

```
text2dsl/
├── src/text2x/
│   ├── agents/          # Agent implementations
│   ├── providers/       # Query provider plugins
│   ├── api/             # FastAPI endpoints
│   └── utils/           # LLM client, helpers
├── tests/               # Test suite
├── docs/                # Documentation
└── design.md            # Architecture design
```

## Development

```bash
# Install dev dependencies
make dev

# Run tests
make test

# Lint and format
make lint
make format
```

## License

MIT
