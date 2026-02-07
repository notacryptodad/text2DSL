#!/bin/bash

BACKEND_PID_FILE=".backend.pid"
FRONTEND_PID_FILE=".frontend.pid"
BACKEND_LOG="logs/backend.log"
FRONTEND_LOG="logs/frontend.log"

mkdir -p logs

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "Error: Docker not found"
        return 1
    fi
    
    local compose_file=${1:-"docker/docker-compose.yml"}
    local label=${2:-"Docker"}
    local env_file=${3:-""}
    
    echo "Checking $label containers..."
    
    if [ -n "$env_file" ]; then
        if ! docker compose -f "$compose_file" --env-file "$env_file" ps 2>/dev/null | grep -q "Up"; then
            echo "Starting $label containers..."
            docker compose -f "$compose_file" --env-file "$env_file" up -d
            echo "Waiting for services to be ready..."
            sleep 5
        else
            echo "$label containers already running"
        fi
    else
        if ! docker compose -f "$compose_file" ps 2>/dev/null | grep -q "Up"; then
            echo "Starting $label containers..."
            docker compose -f "$compose_file" up -d
            echo "Waiting for services to be ready..."
            sleep 5
        else
            echo "$label containers already running"
        fi
    fi
}

start_infra() {
    check_docker "docker/docker-compose.yml" "Backend infrastructure"
}

start_test_infra() {
    check_docker "docker-compose.test.yml" "Test infrastructure" "docker/.env.test"
}

run_migrations() {
    echo "Running database migrations..."
    cd /home/user/git/text2DSL
    if ! uv run alembic upgrade head 2>&1; then
        echo "Migration failed. Attempting to merge branches..."
        uv run alembic merge heads -m "merge_branches" 2>/dev/null || true
        uv run alembic upgrade head || {
            echo "Failed to run migrations. Check logs/backend.log"
            return 1
        }
    fi
    echo "Migrations completed"
}

seed_cache() {
    echo "Seeding Redis schema cache..."
    
    # Get auth token
    TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d '{"email": "admin@text2dsl.com", "password": "Admin123!"}' | uv run python -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
    
    if [ -z "$TOKEN" ]; then
        echo "Failed to get auth token"
        return 1
    fi
    
    # Get all workspaces
    WORKSPACES=$(curl -s "http://localhost:8000/api/v1/workspaces" \
        -H "Authorization: Bearer $TOKEN")
    
    # Extract workspace IDs and loop through them
    WS_IDS=$(echo "$WORKSPACES" | uv run python -c "import sys, json; print(' '.join([w['id'] for w in json.load(sys.stdin)]))" 2>/dev/null)
    
    if [ -z "$WS_IDS" ]; then
        echo "No workspaces found"
        return 0
    fi
    
    CACHE_COUNT=0
    for WS_ID in $WS_IDS; do
        echo "Processing workspace: $WS_ID"
        
        # Get providers for this workspace
        PROVIDERS=$(curl -s "http://localhost:8000/api/v1/workspaces/$WS_ID/providers" \
            -H "Authorization: Bearer $TOKEN")
        
        PROVIDER_IDS=$(echo "$PROVIDERS" | uv run python -c "import sys, json; print(' '.join([p['id'] for p in json.load(sys.stdin)]))" 2>/dev/null)
        
        for PROVIDER_ID in $PROVIDER_IDS; do
            echo "  Processing provider: $PROVIDER_ID"
            
            # Get connections for this provider
            CONNECTIONS=$(curl -s "http://localhost:8000/api/v1/workspaces/$WS_ID/providers/$PROVIDER_ID/connections" \
                -H "Authorization: Bearer $TOKEN")
            
            CONN_IDS=$(echo "$CONNECTIONS" | uv run python -c "import sys, json; print(' '.join([c['id'] for c in json.load(sys.stdin)]))" 2>/dev/null)
            
            for CONN_ID in $CONN_IDS; do
                echo "    Refreshing schema cache for connection: $CONN_ID"
                
                RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/workspaces/$WS_ID/providers/$PROVIDER_ID/connections/$CONN_ID/schema/refresh" \
                    -H "Authorization: Bearer $TOKEN")
                
                if echo "$RESPONSE" | grep -q "success\|schema\|tables"; then
                    echo "    ✅ Cached schema for $CONN_ID"
                    CACHE_COUNT=$((CACHE_COUNT + 1))
                else
                    echo "    ⚠️  Failed to cache $CONN_ID"
                fi
            done
        done
    done
    
    echo "🎉 Schema cache seeded for $CACHE_COUNT connections"
}

start_backend() {
    local seed_cache=${1:-false}
    
    if [ -f "$BACKEND_PID_FILE" ] && kill -0 $(cat "$BACKEND_PID_FILE") 2>/dev/null; then
        echo "Backend already running (PID: $(cat $BACKEND_PID_FILE))"
        return
    fi

    if ! command -v uv &> /dev/null; then
        echo "Error: uv not found. Install it from https://github.com/astral-sh/uv"
        return 1
    fi

    check_docker "docker/docker-compose.yml" "Backend infrastructure" || return 1

    run_migrations || return 1

    echo "Starting backend..."
    uv run bash start_server.sh > "$BACKEND_LOG" 2>&1 &
    
    # Wait for uvicorn process to start
    echo "Waiting for uvicorn process..."
    for i in {1..10}; do
        BACKEND_PID=$(ps aux | grep "[u]vicorn.*text2x.api.app" | awk '{print $2}' | head -1)
        if [ -n "$BACKEND_PID" ]; then
            break
        fi
        sleep 1
    done
    
    if [ -z "$BACKEND_PID" ]; then
        echo "Failed to start backend. Check logs/backend.log"
        tail -20 "$BACKEND_LOG"
        return 1
    fi
    echo $BACKEND_PID > "$BACKEND_PID_FILE"
    
    # Wait for backend to be healthy
    echo "Waiting for backend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ Backend started successfully (PID: $BACKEND_PID)"
            
            # Optionally seed cache
            if [ "$seed_cache" = "true" ]; then
                seed_cache
            fi
            return 0
        fi
        sleep 1
    done
    
    # If we get here, backend didn't become healthy
    echo "❌ Backend failed to start properly. Check logs/backend.log"
    tail -20 "$BACKEND_LOG"
    kill $BACKEND_PID 2>/dev/null
    rm "$BACKEND_PID_FILE"
    return 1
}

start_frontend() {
    if [ -f "$FRONTEND_PID_FILE" ] && kill -0 $(cat "$FRONTEND_PID_FILE") 2>/dev/null; then
        echo "Frontend already running (PID: $(cat $FRONTEND_PID_FILE))"
        return
    fi

    echo "Checking frontend dependencies..."
    if [ ! -d "frontend/node_modules" ] || [ ! -f "frontend/node_modules/.package-lock.json" ]; then
        echo "Installing frontend dependencies..."
        cd frontend
        npm install
        cd ..
        if [ $? -ne 0 ]; then
            echo "Failed to install frontend dependencies"
            return 1
        fi
        echo "✓ Dependencies installed"
    else
        echo "✓ Dependencies already installed"
    fi

    echo "Starting frontend..."
    cd frontend
    npm run dev > "../$FRONTEND_LOG" 2>&1 &
    sleep 3
    # Get the actual node/vite process PID
    FRONTEND_PID=$(ps aux | grep "[n]ode.*vite" | awk '{print $2}' | head -1)
    if [ -z "$FRONTEND_PID" ]; then
        echo "Failed to start frontend. Check logs/frontend.log"
        cd ..
        return 1
    fi
    echo $FRONTEND_PID > "../$FRONTEND_PID_FILE"
    cd ..
    echo "Frontend started (PID: $FRONTEND_PID)"
}

stop_backend() {
    if [ -f "$BACKEND_PID_FILE" ]; then
        PID=$(cat "$BACKEND_PID_FILE")
        if kill -0 $PID 2>/dev/null; then
            echo "Stopping backend (PID: $PID)..."
            # Kill the process and its children
            pkill -P $PID 2>/dev/null
            kill $PID 2>/dev/null
            rm "$BACKEND_PID_FILE"
            echo "Backend stopped"
        else
            echo "Backend not running"
            rm "$BACKEND_PID_FILE"
        fi
    else
        echo "Backend not running"
    fi
}

stop_frontend() {
    if [ -f "$FRONTEND_PID_FILE" ]; then
        PID=$(cat "$FRONTEND_PID_FILE")
        if kill -0 $PID 2>/dev/null; then
            echo "Stopping frontend (PID: $PID)..."
            # Kill the process and its children
            pkill -P $PID 2>/dev/null
            kill $PID 2>/dev/null
            rm "$FRONTEND_PID_FILE"
            echo "Frontend stopped"
        else
            echo "Frontend not running"
            rm "$FRONTEND_PID_FILE"
        fi
    else
        echo "Frontend not running"
    fi
}

force_stop_backend() {
    echo "Force stopping backend on port 8000..."
    PID=$(lsof -ti:8000 2>/dev/null)
    if [ -n "$PID" ]; then
        echo "Killing process(es): $PID"
        kill -9 $PID 2>/dev/null
        [ -f "$BACKEND_PID_FILE" ] && rm "$BACKEND_PID_FILE"
        echo "Backend force stopped"
    else
        echo "No process found on port 8000"
    fi
}

force_stop_frontend() {
    echo "Force stopping frontend on port 5173..."
    PID=$(lsof -ti:5173 2>/dev/null)
    if [ -n "$PID" ]; then
        echo "Killing process(es): $PID"
        kill -9 $PID 2>/dev/null
        [ -f "$FRONTEND_PID_FILE" ] && rm "$FRONTEND_PID_FILE"
        echo "Frontend force stopped"
    else
        echo "No process found on port 5173"
    fi
}

status() {
    echo "=== Server Status ==="
    if [ -f "$BACKEND_PID_FILE" ] && kill -0 $(cat "$BACKEND_PID_FILE") 2>/dev/null; then
        echo "Backend: Running (PID: $(cat $BACKEND_PID_FILE))"
    else
        echo "Backend: Stopped"
    fi
    
    if [ -f "$FRONTEND_PID_FILE" ] && kill -0 $(cat "$FRONTEND_PID_FILE") 2>/dev/null; then
        echo "Frontend: Running (PID: $(cat $FRONTEND_PID_FILE))"
    else
        echo "Frontend: Stopped"
    fi
}

logs() {
    case $1 in
        backend)
            tail -f "$BACKEND_LOG"
            ;;
        frontend)
            tail -f "$FRONTEND_LOG"
            ;;
        *)
            echo "Usage: $0 logs [backend|frontend]"
            ;;
    esac
}

case $1 in
    start)
        case $2 in
            backend)
                if [ "$3" = "--seed-cache" ]; then
                    start_backend true
                else
                    start_backend
                fi
                ;;
            backend-with-cache)
                start_backend true
                ;;
            frontend) start_frontend ;;
            infra) start_infra ;;
            test-infra) start_test_infra ;;
            *)
                start_backend
                start_frontend
                ;;
        esac
        ;;
    stop)
        case $2 in
            backend) stop_backend ;;
            frontend) stop_frontend ;;
            *)
                stop_backend
                stop_frontend
                ;;
        esac
        ;;
    force-stop)
        case $2 in
            backend) force_stop_backend ;;
            frontend) force_stop_frontend ;;
            *)
                force_stop_backend
                force_stop_frontend
                ;;
        esac
        ;;
    restart)
        case $2 in
            backend)
                stop_backend
                sleep 1
                start_backend
                ;;
            frontend)
                stop_frontend
                sleep 1
                start_frontend
                ;;
            *)
                stop_backend
                stop_frontend
                sleep 1
                start_backend
                start_frontend
                ;;
        esac
        ;;
    status)
        status
        ;;
    seed-cache)
        seed_cache
        ;;
    logs)
        logs $2
        ;;
    *)
        echo "Usage: $0 {start|stop|force-stop|restart|status|logs|seed-cache} [backend|frontend|infra|test-infra] [options]"
        echo ""
        echo "Commands:"
        echo "  start [backend|frontend|infra|test-infra]        - Start servers/infrastructure"
        echo "  start backend --seed-cache                        - Start backend and populate schema cache"
        echo "  start backend-with-cache                          - Start backend with cache seeding"
        echo "  stop [backend|frontend]                           - Stop servers gracefully"
        echo "  force-stop [backend|frontend]                     - Force kill by port (8000/5173)"
        echo "  restart [backend|frontend]                        - Restart servers"
        echo "  status                                            - Show server status"
        echo "  logs [backend|frontend]                           - Tail server logs"
        echo "  seed-cache                                         - Pre-populate Redis schema cache"
        echo ""
        echo "Options:"
        echo "  --seed-cache    - Pre-populate Redis schema cache (backend only)"
        exit 1
        ;;
esac
