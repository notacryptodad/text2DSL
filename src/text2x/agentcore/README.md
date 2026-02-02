# AgentCore

AgentCore is a unified runtime for hosting LLM-powered agents in text2DSL. It provides a clean, scalable architecture that supports both local (in-process) and remote (HTTP) deployment modes.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  AgentCore Runtime                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Agent Registry                      │    │
│  │  "auto_annotation" → AutoAnnotationAgent        │    │
│  │  "annotation_assistant" → AnnotationAssistant   │    │
│  │  "query" → QueryAgent                           │    │
│  └─────────────────────────────────────────────────┘    │
│                         │                                │
│              ┌──────────▼──────────┐                    │
│              │  Shared LLM Client  │                    │
│              │  (LiteLLM/Bedrock)  │                    │
│              └─────────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

## Available Agents

| Agent | Description | Use Case |
|-------|-------------|----------|
| `auto_annotation` | Auto-generate schema annotations | Bulk annotation of tables |
| `annotation_assistant` | Interactive annotation chat | Guided annotation with Q&A |
| `query` | Natural language to SQL | Query generation from text |

## Quick Start

### Using the Client

```python
from text2x.agentcore import get_agentcore_client

# Get the default client (uses environment configuration)
client = get_agentcore_client()

# List available agents
agents = await client.list_agents()
# [AgentInfo(name='auto_annotation', status='active'), ...]

# Invoke an agent
result = await client.invoke("query", {
    "user_message": "Show me all users",
    "provider_id": "your-provider-id"
})

# Chat with an agent (multi-turn)
response = await client.chat(
    "annotation_assistant",
    message="Help me annotate the users table",
    conversation_id="conv-123"  # Optional, for continuing conversations
)
```

### Direct Runtime Access (Local Mode Only)

```python
from text2x.api.state import app_state

# Get the runtime
runtime = app_state.agentcore

# List agents
agent_names = runtime.list_agents()

# Get a specific agent
agent = runtime.get_agent("query")

# Invoke directly
result = await agent.process({"user_message": "Show all users"})
```

## Configuration

AgentCore can run in two modes:

### Local Mode (Default)

Agents run in-process with the backend. Best for:
- Development
- Single-instance deployments
- Low latency requirements

```bash
# Default - no configuration needed
AGENTCORE_MODE=local
```

### Remote Mode

Agents run as a separate service, accessed via HTTP. Best for:
- Production deployments
- Independent scaling
- Multi-instance backends

```bash
AGENTCORE_MODE=remote
AGENTCORE_URL=https://agentcore.example.com/api/v1/agentcore
AGENTCORE_API_KEY=your-api-key  # Optional
AGENTCORE_TIMEOUT=120  # Request timeout in seconds
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTCORE_MODE` | `local` | `local` or `remote` |
| `AGENTCORE_URL` | - | Base URL for remote AgentCore service |
| `AGENTCORE_API_KEY` | - | API key for remote authentication |
| `AGENTCORE_TIMEOUT` | `120` | Request timeout in seconds |

## API Endpoints

When running, AgentCore exposes these endpoints:

```
GET  /api/v1/agentcore/                    # List all agents
POST /api/v1/agentcore/{agent}/invoke      # Invoke an agent
POST /api/v1/agentcore/{agent}/chat        # Chat with an agent
GET  /api/v1/agentcore/{agent}/status      # Get agent status
```

### Example: Invoke Query Agent

```bash
curl -X POST http://localhost:8000/api/v1/agentcore/query/invoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "input_data": {
      "user_message": "Show me all active users",
      "provider_id": "your-provider-id"
    }
  }'
```

### Example: Chat with Annotation Assistant

```bash
curl -X POST http://localhost:8000/api/v1/agentcore/annotation_assistant/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "message": "What columns does the users table have?",
    "conversation_id": "optional-for-multi-turn"
  }'
```

## Client API Reference

### AgentCoreClient

```python
from text2x.agentcore import AgentCoreClient, AgentCoreMode

# Create client with explicit configuration
client = AgentCoreClient(
    mode=AgentCoreMode.LOCAL,  # or AgentCoreMode.REMOTE
    base_url="https://...",     # Required for remote mode
    api_key="...",              # Optional
    timeout=120.0               # Request timeout
)

# Or use factory function (reads from environment)
from text2x.agentcore import create_agentcore_client
client = create_agentcore_client()

# Or use singleton (recommended)
from text2x.agentcore import get_agentcore_client
client = get_agentcore_client()
```

### Methods

#### `list_agents() -> List[AgentInfo]`
List all available agents.

```python
agents = await client.list_agents()
for agent in agents:
    print(f"{agent.name}: {agent.status}")
```

#### `invoke(agent_name, input_data) -> Dict`
Invoke an agent with input data.

```python
result = await client.invoke("query", {
    "user_message": "Show all users",
    "provider_id": "..."
})
```

#### `chat(agent_name, message, conversation_id?, context?) -> Dict`
Send a chat message to an agent.

```python
response = await client.chat(
    "annotation_assistant",
    message="Help me understand this table",
    conversation_id="conv-123"
)
print(response["response"])
print(response["conversation_id"])  # Use for follow-up messages
```

#### `get_agent_status(agent_name) -> Dict`
Get status of a specific agent.

```python
status = await client.get_agent_status("query")
```

#### `close()`
Close the client and release resources.

```python
await client.close()

# Or use as context manager
async with AgentCoreClient(mode="local") as client:
    result = await client.invoke("query", {...})
```

## Deployment

### Local Deployment (Development)

```bash
# Start backend with AgentCore embedded
cd ~/text2DSL
source .venv/bin/activate
PYTHONPATH=src uvicorn text2x.api.app:app --host 0.0.0.0 --port 8000
```

### Remote Deployment (Production)

1. **Deploy AgentCore Service**
```bash
# AgentCore can run standalone
PYTHONPATH=src python -m text2x.agentcore.standalone --port 9000
```

2. **Configure Backend to Use Remote AgentCore**
```bash
AGENTCORE_MODE=remote
AGENTCORE_URL=http://agentcore-service:9000/api/v1/agentcore
```

3. **Scale Independently**
```yaml
# Kubernetes example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentcore
spec:
  replicas: 3  # Scale agents independently
  ...
```

## Adding New Agents

1. Create agent directory:
```
src/text2x/agentcore/agents/your_agent/
├── __init__.py
├── agent.py
└── tools.py  # Optional
```

2. Implement the agent:
```python
# agent.py
from text2x.agentcore.agents.base import AgentCoreBaseAgent

class YourAgent(AgentCoreBaseAgent):
    def __init__(self, runtime, name: str = "your_agent"):
        super().__init__(runtime, name)
        # Define tools
        self.tools = {
            "your_tool": self._your_tool,
        }
    
    def get_system_prompt(self) -> str:
        return "You are a helpful agent..."
    
    async def process(self, input_data: dict) -> dict:
        # Implement processing logic
        ...
    
    async def _your_tool(self, params: dict) -> dict:
        # Implement tool
        ...
```

3. Register in `app.py`:
```python
from text2x.agentcore.agents.your_agent import YourAgent

# In initialize_agentcore()
agent = YourAgent(runtime)
runtime.register(agent)
```

## Troubleshooting

### Agent not found
```
ValueError: Agent 'xyz' not found
```
Check that the agent is registered in `initialize_agentcore()` in `app.py`.

### Connection refused (remote mode)
```
httpx.ConnectError: Connection refused
```
Verify `AGENTCORE_URL` is correct and the AgentCore service is running.

### LLM timeout
```
RuntimeError: LiteLLM invocation failed: timeout
```
Increase `AGENTCORE_TIMEOUT` or check Bedrock connectivity.

## See Also

- [LiteLLM Client](../llm/README.md) - LLM integration
- [API Routes](../api/README.md) - REST API documentation
- [Providers](../providers/README.md) - Database providers
