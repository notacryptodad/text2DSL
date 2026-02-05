# Legacy Code Removal Summary

## Overview
Removed all legacy agent code paths from the agentcore module. The system now exclusively uses Strands SDK for all agent implementations.

## Files Removed

### Legacy Agent Implementations
- `src/text2x/agentcore/agents/base.py` - Base class for legacy agents
- `src/text2x/agentcore/agents/query/agent.py` - Legacy query agent
- `src/text2x/agentcore/agents/auto_annotation/agent.py` - Legacy auto-annotation agent
- `src/text2x/agentcore/agents/annotation_assistant/agent.py` - Legacy annotation assistant agent

### Legacy Runtime & Client
- `src/text2x/agentcore/llm/client.py` - Legacy LLM client wrapper
- `src/text2x/agentcore/strands_runtime.py` - Old runtime with dual-mode support

## Files Modified

### Runtime
- **`src/text2x/agentcore/runtime.py`** (recreated)
  - Removed `use_strands` flag (always uses Strands now)
  - Removed legacy agent loading code
  - Simplified to only support Strands SDK agents
  - Removed `LLMClient` dependency

### Module Exports
- **`src/text2x/agentcore/__init__.py`**
  - Removed `StrandsAgentCore` alias (now just `AgentCore`)
  - Removed `LLMClient` export
  - Removed `AgentCoreBaseAgent` export
  - Simplified imports

- **`src/text2x/agentcore/llm/__init__.py`**
  - Removed `LLMClient` export
  - Only exports Strands model providers

- **`src/text2x/agentcore/agents/__init__.py`**
  - Only exports Strands agent implementations

- **`src/text2x/agentcore/agents/query/__init__.py`**
  - Removed legacy `QueryAgent` import
  - Only exports Strands `QueryAgent`

- **`src/text2x/agentcore/agents/auto_annotation/__init__.py`**
  - Only exports Strands `AutoAnnotationAgent`

- **`src/text2x/agentcore/agents/annotation_assistant/__init__.py`**
  - Only exports Strands `AnnotationAssistantAgent`

### Tests
- **`tests/agentcore/test_strands_integration.py`**
  - Removed `test_create_runtime_with_legacy_flag` test
  - Updated `test_create_runtime_with_strands_flag` to `test_create_runtime`
  - Updated imports to use new runtime module

## API Changes

### Before
```python
from text2x.agentcore import AgentCore, StrandsAgentCore, create_agentcore

# Could create with legacy or Strands
runtime = create_agentcore(use_strands=True)  # Strands
runtime = create_agentcore(use_strands=False)  # Legacy
```

### After
```python
from text2x.agentcore import AgentCore, create_agentcore

# Always uses Strands SDK
runtime = create_agentcore()  # No flag needed
```

## Benefits

1. **Simplified codebase** - Removed ~1500 lines of legacy code
2. **Single implementation** - No more dual-mode complexity
3. **Better maintainability** - Only one agent system to maintain
4. **Clearer architecture** - Strands SDK is the standard
5. **Reduced confusion** - No more choosing between legacy/Strands

## Migration Notes

If any external code was using:
- `use_strands=False` → Remove the flag, Strands is now default and only option
- `LLMClient` from agentcore → Use `create_litellm_model()` instead
- `AgentCoreBaseAgent` → Use Strands SDK's `Agent` base class
- Legacy agent imports → Update to use Strands agent implementations

## Testing

All syntax checks pass. The system now:
- ✅ Only uses Strands SDK agents
- ✅ Only uses `LiteLLMModel` from Strands
- ✅ Simplified runtime without dual-mode support
- ✅ Cleaner module structure
