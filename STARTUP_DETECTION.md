# Backend Startup Detection Enhancement

## Changes Made

Updated `manage.sh` `start_backend()` function to:

1. **Wait for uvicorn process** with retry loop (up to 10 seconds)
2. **Check health endpoint** to verify successful startup (up to 30 seconds)
3. **Show error logs** if startup fails
4. **Clean up** PID file and kill process on failure

## New Startup Flow

```bash
Starting backend...
Waiting for uvicorn process...     # Waits for PID
Waiting for backend to be ready... # Checks /health endpoint
✅ Backend started successfully (PID: 665201)
```

## Error Handling

If backend fails to start:
- Shows last 20 lines of logs
- Kills the failed process
- Removes PID file
- Returns error code

## Example Output

### Success:
```
✅ Backend started successfully (PID: 665201)
```

### Failure:
```
❌ Backend failed to start properly. Check logs/backend.log
[Last 20 lines of error logs shown]
```

## Health Check

The script now polls `http://localhost:8000/health` for up to 30 seconds to ensure:
- API server is responding
- All services (database, redis, opensearch) are healthy
- Application startup completed without errors

## Benefits

1. ✅ Detects startup failures immediately
2. ✅ Shows relevant error logs automatically
3. ✅ Prevents false "started" messages
4. ✅ Cleans up failed processes
5. ✅ Returns proper exit codes for scripting
