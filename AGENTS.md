# Local Development Setup

This guide explains how to properly start the Text2DSL local development environment.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.12+ (use `python3` command) with `uv` package manager
- Node.js 18+ and npm
- PostgreSQL client tools (optional, for manual DB access)

## Quick Start

### 1. Start Infrastructure

The project requires Docker containers for PostgreSQL, Redis, OpenSearch, and test databases.

```bash
# Start backend infrastructure (PostgreSQL, Redis, OpenSearch)
./manage.sh start infra

# Start test infrastructure (isolated test databases)
./manage.sh start test-infra
```

**Note**: The test PostgreSQL database (`text2dsl-postgres-test` on port 5433) is automatically seeded with an e-commerce schema (customers, products, orders, order_items) on startup.

### 2. Start Backend and Frontend

```bash
# Start both backend and frontend servers in background
./manage.sh start

# Or start individually
./manage.sh start backend   # Backend API on port 8000
./manage.sh start frontend  # Frontend dev server on port 5173
```

The backend uses `uv` to manage the Python virtual environment automatically.

### 3. Default Admin Credentials

After starting the backend, use these credentials to log in:

- **Email**: `admin@text2dsl.com`
- **Password**: `Admin123!`

These credentials are automatically created by the seed script during backend startup.

## Management Script Commands

The `manage.sh` script provides convenient commands for managing the development environment:

### Starting Services

```bash
./manage.sh start              # Start both backend and frontend
./manage.sh start backend      # Start only backend
./manage.sh start backend --seed-cache  # Start backend and populate Redis schema cache
./manage.sh start frontend     # Start only frontend
./manage.sh start infra        # Start backend infrastructure containers
./manage.sh start test-infra   # Start test infrastructure containers
```

### Stopping Services

```bash
./manage.sh stop               # Stop both backend and frontend
./manage.sh stop backend       # Stop only backend
./manage.sh stop frontend      # Stop only frontend
./manage.sh force-stop backend # Force kill backend (port 8000)
./manage.sh force-stop frontend # Force kill frontend (port 5173)
```

### Restarting Services

```bash
./manage.sh restart            # Restart both servers
./manage.sh restart backend    # Restart only backend
./manage.sh restart frontend   # Restart only frontend
```

### Checking Status

```bash
./manage.sh status             # Show running status of all servers
```

### Viewing Logs

```bash
./manage.sh logs backend       # Tail backend logs
./manage.sh logs frontend      # Tail frontend logs
```

### Cache Management

```bash
./manage.sh seed-cache         # Pre-populate Redis schema cache for all connections
```

Logs are stored in:
- `logs/backend.log` - Backend API logs
- `logs/frontend.log` - Frontend dev server logs

## Infrastructure Details

### Backend Infrastructure (Main)

Started with `./manage.sh start infra`:

- **PostgreSQL**: `localhost:5432` - Main application database
- **Redis**: `localhost:6379` - Caching and session storage
- **OpenSearch**: `localhost:9200` - RAG and search functionality

### Test Infrastructure (Isolated)

Started with `./manage.sh start test-infra`:

- **PostgreSQL**: `localhost:5433` - Test database with seeded e-commerce data
- **MongoDB**: `localhost:27018` - NoSQL provider testing
- **Redis**: `localhost:6380` - Test cache
- **OpenSearch**: `localhost:9201` - Test search

The test PostgreSQL database is automatically seeded with sample data on container startup via `/docker/postgres-test/seed.sql`.

## Manual Setup (Alternative)

If you prefer to start services manually:

### Backend

```bash
# Start infrastructure
docker compose -f docker/docker-compose.yml up -d

# Run migrations and seed admin
uv run alembic upgrade head
uv run python src/text2x/scripts/seed_admin.py

# Start API server
uv run uvicorn text2x.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Test Infrastructure

```bash
docker compose -f docker-compose.test.yml up -d
```

## Stopping Everything

```bash
# Stop servers
./manage.sh stop

# Stop Docker containers
docker compose -f docker/docker-compose.yml down
docker compose -f docker-compose.test.yml down
```

## Troubleshooting

### Backend won't start
- Check if Docker containers are running: `docker ps | grep text2dsl`
- Check backend logs: `./manage.sh logs backend`
- Ensure `.env` file is configured correctly

### Frontend won't start
- Check if port 5173 is available
- Check frontend logs: `./manage.sh logs frontend`
- Try `cd frontend && npm install` to reinstall dependencies

### Database connection errors
- Verify PostgreSQL container is healthy: `docker ps`
- Check connection settings in `.env`
- Ensure migrations are applied: `uv run alembic upgrade head`

### Test database has no tables
- The test database should auto-seed on startup
- If needed, manually seed: `bash docker/postgres-test/seed.sh`

## Development Workflow

1. Start infrastructure: `./manage.sh start infra test-infra`
2. Start servers: `./manage.sh start`
3. Access the application:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
4. Make changes (servers auto-reload)
5. Check logs: `./manage.sh logs backend` or `./manage.sh logs frontend`
6. Stop when done: `./manage.sh stop`

## Environment Configuration

Key environment variables in `.env` (create from `.env.example` in project root):

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `OPENSEARCH_HOST` - OpenSearch host
- `LLM_PROVIDER` - LLM provider (openai, bedrock, etc.)
- `LLM_MODEL` - Model to use for agents
- `AWS_REGION` - AWS region for Bedrock (if using)

See `.env.example` for all available configuration options.
