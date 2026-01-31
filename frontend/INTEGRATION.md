# Frontend-Backend Integration Guide

This document explains how the Text2DSL frontend integrates with the backend API.

## Architecture Overview

```
┌─────────────────┐         WebSocket          ┌─────────────────┐
│                 │ ←─────────────────────────→ │                 │
│  React Frontend │                             │  FastAPI Backend│
│  (Port 3000)    │         REST API            │  (Port 8000)    │
│                 │ ←─────────────────────────→ │                 │
└─────────────────┘                             └─────────────────┘
```

## WebSocket Communication

### Connection

The frontend connects to the WebSocket endpoint:

```
ws://localhost:8000/ws/query
```

In development, Vite proxies this through:

```
ws://localhost:3000/ws/query → ws://localhost:8000/ws/query
```

### Message Format

#### Client → Server (Query Request)

```json
{
  "provider_id": "sql-postgres",
  "query": "Show me all users who signed up last month",
  "conversation_id": "uuid-or-null",
  "options": {
    "trace_level": "summary",
    "max_iterations": 3,
    "confidence_threshold": 0.85,
    "enable_execution": false
  }
}
```

#### Server → Client (Events)

**Progress Event:**
```json
{
  "type": "progress",
  "data": {
    "stage": "schema_retrieval",
    "message": "Retrieving database schema...",
    "progress": 0.2,
    "conversation_id": "uuid",
    "turn_id": "uuid"
  },
  "trace": {
    "agent": "SchemaExpert",
    "action": "retrieving_schema",
    "details": {"tables_found": 5}
  }
}
```

**Result Event:**
```json
{
  "type": "result",
  "data": {
    "stage": "completed",
    "message": "Query processing completed",
    "progress": 1.0,
    "result": {
      "conversation_id": "uuid",
      "turn_id": "uuid",
      "generated_query": "SELECT * FROM users WHERE created_at >= ...",
      "confidence_score": 0.92,
      "validation_status": "valid",
      "validation_result": {
        "status": "valid",
        "errors": [],
        "warnings": [],
        "suggestions": ["Consider adding LIMIT clause"]
      },
      "execution_result": {
        "success": true,
        "row_count": 150,
        "execution_time_ms": 45
      },
      "reasoning_trace": {
        "orchestrator_latency_ms": 1300,
        "total_tokens_input": 3000,
        "total_tokens_output": 1000,
        "total_cost_usd": 0.012
      },
      "needs_clarification": false,
      "clarification_questions": [],
      "iterations": 1
    }
  }
}
```

**Error Event:**
```json
{
  "type": "error",
  "data": {
    "error": "processing_error",
    "message": "Failed to process query",
    "details": {
      "error": "Database connection timeout"
    }
  }
}
```

**Clarification Event:**
```json
{
  "type": "clarification",
  "data": {
    "questions": [
      "Which time period are you interested in?",
      "Should I include inactive users?"
    ]
  }
}
```

### Processing Stages

The frontend tracks these stages during query processing:

1. `started` - Query processing initiated
2. `schema_retrieval` - Fetching database schema
3. `rag_search` - Searching for similar examples
4. `query_generation` - Generating the query
5. `validation` - Validating the query
6. `execution` - Executing the query (if enabled)
7. `completed` - Processing finished

## REST API Integration

While the primary interface uses WebSocket for real-time updates, the backend also provides REST endpoints that could be integrated:

### Available Endpoints

```
GET  /health                           - Health check
GET  /api/v1/providers                 - List available providers
GET  /api/v1/providers/{id}/schema     - Get provider schema
GET  /api/v1/conversations/{id}        - Get conversation details
GET  /api/v1/conversations/{id}/turns  - Get conversation history
POST /api/v1/query                     - Submit query (non-streaming)
```

### Example: Fetching Providers

```javascript
const response = await fetch('http://localhost:8000/api/v1/providers')
const providers = await response.json()
```

## CORS Configuration

The backend must be configured to allow requests from the frontend:

```python
# In backend/src/text2x/api/app.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Development Setup

### 1. Start Backend

```bash
cd /home/ubuntu/text2DSL
make run-dev
```

The backend will be available at `http://localhost:8000`.

### 2. Start Frontend

```bash
cd /home/ubuntu/text2DSL/frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### 3. Test Connection

1. Open `http://localhost:3000` in your browser
2. Check the connection indicator (should be green)
3. Try sending a query

## Production Deployment

### Option 1: Separate Deployment

Deploy frontend and backend separately:

**Frontend (Static Hosting):**
```bash
npm run build
# Deploy dist/ to Netlify, Vercel, S3, etc.
```

**Backend (Container/VM):**
```bash
docker-compose up -d
```

Update `vite.config.js` to point to production backend.

### Option 2: Combined Deployment

Serve frontend from backend:

```python
# In backend/src/text2x/api/app.py
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

Build process:
```bash
# Build frontend
cd frontend && npm run build

# Build and run backend
cd .. && docker-compose up -d
```

## Troubleshooting

### WebSocket Connection Fails

**Symptoms:**
- Connection indicator stays yellow/red
- "Connecting..." message persists

**Solutions:**
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check WebSocket endpoint: `wscat -c ws://localhost:8000/ws/query`
3. Review browser console for errors
4. Check backend logs for connection issues

### CORS Errors

**Symptoms:**
- Network errors in browser console
- "Access-Control-Allow-Origin" errors

**Solutions:**
1. Verify CORS middleware is configured in backend
2. Check `allow_origins` includes frontend URL
3. Restart backend after configuration changes

### Query Processing Hangs

**Symptoms:**
- Progress indicator stops
- No result or error received

**Solutions:**
1. Check backend logs for errors
2. Verify provider configuration
3. Check LLM service availability
4. Increase timeout values if needed

## Testing

### Manual Testing

Use browser developer tools to inspect WebSocket messages:

1. Open DevTools → Network → WS
2. Send a query from the UI
3. Inspect messages sent/received

### Automated Testing

Test WebSocket integration with a simple script:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/query')

ws.onopen = () => {
  ws.send(JSON.stringify({
    provider_id: 'sql-postgres',
    query: 'Show me all users',
    options: { trace_level: 'none' }
  }))
}

ws.onmessage = (event) => {
  console.log('Received:', JSON.parse(event.data))
}
```

## Security Considerations

### Production Checklist

- [ ] Use WSS (WebSocket Secure) in production
- [ ] Implement authentication/authorization
- [ ] Rate limit WebSocket connections
- [ ] Validate all user inputs
- [ ] Sanitize query results before display
- [ ] Use environment variables for sensitive config
- [ ] Enable HTTPS for REST API
- [ ] Implement CSP headers
- [ ] Add request size limits

### Authentication Flow (Future Enhancement)

```
1. User logs in via REST API
2. Backend returns JWT token
3. Frontend includes token in WebSocket connection
4. Backend validates token before processing queries
```

## Performance Optimization

### Frontend

- Implement query result pagination
- Add query caching
- Debounce input for auto-complete
- Lazy load conversation history
- Optimize re-renders with React.memo

### Backend

- Enable response compression
- Implement query result streaming
- Cache schema information
- Use connection pooling
- Implement rate limiting

## Monitoring

### Metrics to Track

- WebSocket connection success rate
- Average query processing time
- Query success/failure rate
- User engagement (queries per session)
- Error rates by type

### Logging

Frontend logs to console (dev) and service (prod):
```javascript
console.log('Query sent:', query)
console.error('WebSocket error:', error)
```

Backend logs to stdout/file:
```python
logger.info(f"WebSocket query processing started: {request}")
logger.error(f"Error processing query: {error}")
```

## Future Enhancements

1. **Query History**: Save and recall previous queries
2. **Query Builder UI**: Visual query construction
3. **Result Export**: Download results as CSV/JSON
4. **Collaborative Sessions**: Share conversations
5. **Voice Input**: Speech-to-query
6. **Query Templates**: Predefined query patterns
7. **Analytics Dashboard**: Usage statistics
8. **Multi-language Support**: Internationalization
