.PHONY: install dev test test-up test-down lint format docker-up docker-down clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

# Backend infrastructure (for running the API server)
docker-up:
	docker compose up -d

docker-down:
	docker compose down

# Test infrastructure (isolated containers for tests)
test-up:
	docker compose -f docker-compose.test.yml up -d
	@echo "Waiting for containers to be healthy..."
	@sleep 5

test-down:
	docker compose -f docker-compose.test.yml down -v

# Run tests (requires test containers running)
test:
	pytest tests/ -v

# Run tests with automatic container lifecycle
test-full: test-up
	pytest tests/ -v || true
	$(MAKE) test-down

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
