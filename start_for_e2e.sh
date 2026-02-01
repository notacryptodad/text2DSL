#!/bin/bash
set -e

# Start backend server
echo "Starting backend server..."
python -m uvicorn text2x.api.app:app --host 0.0.0.0 --port 8000 --log-level error 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        exit 0
    fi
    sleep 1
done

echo "❌ Backend failed to start"
exit 1
