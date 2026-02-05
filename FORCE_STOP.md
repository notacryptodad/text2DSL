# Force Stop Feature Added to manage.sh

## New Command

```bash
./manage.sh force-stop [backend|frontend]
```

## What It Does

Kills processes by port number instead of PID file:
- **Backend**: Kills any process listening on port **8000**
- **Frontend**: Kills any process listening on port **5173**

## Usage Examples

```bash
# Force stop backend only
./manage.sh force-stop backend

# Force stop frontend only
./manage.sh force-stop frontend

# Force stop both
./manage.sh force-stop
```

## When to Use

Use `force-stop` when:
- Regular `stop` command doesn't work
- PID files are out of sync
- Port is already in use error
- Processes are orphaned

## Difference from Regular Stop

| Command | Method | Use Case |
|---------|--------|----------|
| `stop` | Uses PID file, graceful kill | Normal shutdown |
| `force-stop` | Finds by port, force kill (-9) | Stuck processes |

## Implementation

Uses `lsof -ti:PORT` to find processes by port, then kills with `kill -9`.

## Fixed Issues

1. ✅ Backend PID detection pattern updated to match actual uvicorn command
2. ✅ Force stop cleans up PID files
3. ✅ Handles multiple processes on same port

## Complete Command List

```bash
./manage.sh start [backend|frontend|infra|test-infra]
./manage.sh stop [backend|frontend]
./manage.sh force-stop [backend|frontend]  # NEW
./manage.sh restart [backend|frontend]
./manage.sh status
./manage.sh logs [backend|frontend]
```
