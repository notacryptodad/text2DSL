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
    
    echo "Checking $label containers..."
    if ! docker compose -f "$compose_file" ps 2>/dev/null | grep -q "Up"; then
        echo "Starting $label containers..."
        docker compose -f "$compose_file" up -d
        echo "Waiting for services to be ready..."
        sleep 5
    else
        echo "$label containers already running"
    fi
}

start_infra() {
    check_docker "docker/docker-compose.yml" "Backend infrastructure"
}

start_test_infra() {
    check_docker "docker-compose.test.yml" "Test infrastructure"
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

start_backend() {
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
    sleep 5
    # Get the actual uvicorn process PID
    BACKEND_PID=$(ps aux | grep "[u]vicorn text2x.api.app:app" | awk '{print $2}' | head -1)
    if [ -z "$BACKEND_PID" ]; then
        echo "Failed to start backend. Check logs/backend.log"
        return 1
    fi
    echo $BACKEND_PID > "$BACKEND_PID_FILE"
    echo "Backend started (PID: $BACKEND_PID)"
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
            backend) start_backend ;;
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
    logs)
        logs $2
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs} [backend|frontend|infra|test-infra]"
        echo ""
        echo "Commands:"
        echo "  start [backend|frontend|infra|test-infra] - Start servers/infrastructure"
        echo "  stop [backend|frontend]                    - Stop servers"
        echo "  restart [backend|frontend]                 - Restart servers"
        echo "  status                                     - Show server status"
        echo "  logs [backend|frontend]                    - Tail server logs"
        exit 1
        ;;
esac
