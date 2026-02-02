# Integration Tests

This folder contains **real integration tests** that require full infrastructure:

## Requirements

- PostgreSQL with test database (Docker)
- OpenSearch with RAG index (Docker)
- Backend API running (uvicorn)
- Real Bedrock access (for AI tests)

## Running

```bash
# Start infrastructure
cd ~/text2DSL && make docker-up

# Seed test data
python scripts/seed_test_data.py

# Run integration tests only
npx playwright test e2e/integration/ --reporter=list

# Run with real AI (slower, non-deterministic)
REAL_AI=true npx playwright test e2e/integration/ --reporter=list
```

## Test Categories

| File | Description | AI Required |
|------|-------------|-------------|
| `admin-setup.integration.spec.js` | Workspace/Provider/Connection CRUD | No |
| `schema-retrieval.integration.spec.js` | Real schema from test DB | No |
| `query-generation.integration.spec.js` | Full query flow | Yes |
| `rag-search.integration.spec.js` | Vector similarity search | No |
| `annotation-flow.integration.spec.js` | Schema annotation with DB | Optional |

## Environment Variables

```bash
TEST_DB_HOST=localhost
TEST_DB_PORT=5432
TEST_DB_NAME=text2dsl_test
TEST_DB_USER=postgres
TEST_DB_PASS=postgres
OPENSEARCH_URL=http://localhost:9200
REAL_AI=false  # Set to true for AI tests
```

## vs Unit/Mock Tests

| Aspect | e2e/*.spec.js | e2e/integration/*.spec.js |
|--------|---------------|---------------------------|
| Speed | Fast (~30s) | Slower (~2-5min) |
| Infrastructure | None/Mocked | Full Docker stack |
| AI Calls | Mocked | Real (optional) |
| Deterministic | Yes | Mostly (AI varies) |
| CI/CD | Every commit | Nightly/Manual |
