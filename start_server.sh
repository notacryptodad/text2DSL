#!/bin/bash
# Start the Text2DSL API server

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Seed default admin
echo "Seeding default admin..."
python src/text2x/scripts/seed_admin.py

# Start server (self-registration disabled by default, admin creates users)
echo "Starting API server..."
python -m uvicorn text2x.api.app:app --host 0.0.0.0 --port 8000 --reload
