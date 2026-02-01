"""Test configuration for integration tests.

Uses separate test containers on different ports to avoid conflicts with
backend development infrastructure.
"""
import os

# Test container ports (match docker-compose.test.yml)
TEST_POSTGRES_PORT = int(os.getenv("TEST_POSTGRES_PORT", "5433"))
TEST_MONGODB_PORT = int(os.getenv("TEST_MONGODB_PORT", "27018"))
TEST_OPENSEARCH_PORT = int(os.getenv("TEST_OPENSEARCH_PORT", "9201"))
TEST_REDIS_PORT = int(os.getenv("TEST_REDIS_PORT", "6380"))

# Test database configurations
TEST_POSTGRES_CONFIG = {
    "host": os.getenv("TEST_POSTGRES_HOST", "localhost"),
    "port": TEST_POSTGRES_PORT,
    "database": "text2x",
    "username": "text2x",
    "password": "text2x",
    "dialect": "postgresql",
}

TEST_MONGODB_CONFIG = {
    "connection_string": f"mongodb://localhost:{TEST_MONGODB_PORT}",
    "database": "text2x_test",
}

TEST_OPENSEARCH_CONFIG = {
    "host": os.getenv("TEST_OPENSEARCH_HOST", "localhost"),
    "port": TEST_OPENSEARCH_PORT,
}

TEST_REDIS_CONFIG = {
    "host": os.getenv("TEST_REDIS_HOST", "localhost"),
    "port": TEST_REDIS_PORT,
}
