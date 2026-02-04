# Text2DSL

A multi-agent system that converts natural language queries into executable queries (SQL, NoSQL, Splunk SPL, etc.) with >=95% accuracy through iterative refinement, RAG-powered examples, and expert feedback loops.

## Features

- **Multi-Agent Architecture**: Orchestrator, Schema Expert, Query Builder, Validator, and RAG Retrieval agents
- **Pluggable Providers**: SQL (PostgreSQL, MySQL), NoSQL (MongoDB), Splunk SPL, and custom plugins
- **RAG-Powered**: OpenSearch-backed example retrieval for improved accuracy
- **Expert Review Loop**: Continuous learning from human expert corrections
- **Full Observability**: Reasoning traces, metrics, and audit logs
- **Modern Web UI**: React-based chat interface with real-time WebSocket streaming

## Quick Start

### Backend

```bash
# Install dependencies
make install

# Start infrastructure (PostgreSQL, Redis, OpenSearch)
make docker-up

# Run the API server
make run-dev
```

The backend will be available at `http://localhost:8000`.

### Frontend

```bash
# Navigate to frontend directory
cd frontend

# Run setup script (installs dependencies)
./setup.sh

# Or manually install
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

See [frontend/README.md](./frontend/README.md) for detailed frontend documentation.

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
├── frontend/            # React web UI
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── hooks/       # Custom hooks (WebSocket)
│   │   └── styles/      # CSS styles
│   ├── package.json     # Frontend dependencies
│   └── README.md        # Frontend documentation
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
