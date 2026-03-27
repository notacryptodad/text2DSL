#!/bin/bash
uv run alembic upgrade head
uv run python src/text2x/scripts/seed_admin.py
uv run python src/text2x/scripts/seed_workspace.py
uv run uvicorn src.text2x.api.app:app --host 0.0.0.0 --port 8000
