"""Tests for Strands SDK integration with AgentCore."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Test imports
def test_strands_provider_import():
    """Test that Strands LiteLLM provider can be imported."""
    from text2x.agentcore.llm.strands_provider import create_litellm_model, get_default_model
    assert create_litellm_model is not None
    assert get_default_model is not None


def test_strands_agents_import():
    """Test that Strands agents can be imported."""
    from text2x.agentcore.agents.auto_annotation.strands_agent import AutoAnnotationAgent
    from text2x.agentcore.agents.annotation_assistant.strands_agent import AnnotationAssistantAgent
    from text2x.agentcore.agents.query.strands_agent import QueryAgent
    
    assert AutoAnnotationAgent is not None
    assert AnnotationAssistantAgent is not None
    assert QueryAgent is not None


def test_strands_runtime_import():
    """Test that Strands runtime can be imported."""
    from text2x.agentcore.strands_runtime import AgentCore, create_agentcore
    
    assert AgentCore is not None
    assert create_agentcore is not None


def test_package_level_imports():
    """Test that package-level imports work correctly."""
    from text2x.agentcore import (
        StrandsAgentCore,
        create_agentcore,
        create_litellm_model,
        get_default_model,
    )
    from text2x.agentcore.agents.auto_annotation import StrandsAutoAnnotationAgent
    from text2x.agentcore.agents.annotation_assistant import StrandsAnnotationAssistantAgent
    from text2x.agentcore.agents.query import StrandsQueryAgent
    
    assert StrandsAgentCore is not None
    assert create_agentcore is not None
    assert create_litellm_model is not None
    assert get_default_model is not None
    assert StrandsAutoAnnotationAgent is not None
    assert StrandsAnnotationAssistantAgent is not None
    assert StrandsQueryAgent is not None


def test_create_litellm_model():
    """Test creating a LiteLLM model provider."""
    from text2x.agentcore.llm.strands_provider import create_litellm_model
    from text2x.agentcore.config import AgentCoreConfig
    
    config = AgentCoreConfig(
        model="bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
        temperature=0.3,
        max_tokens=4096,
    )
    
    model = create_litellm_model(config)
    
    assert model is not None
    # Check model config
    model_config = model.get_config()
    assert model_config["model_id"] == "bedrock/anthropic.claude-3-sonnet-20240229-v1:0"


class TestAutoAnnotationAgentStrands:
    """Tests for Strands AutoAnnotationAgent."""
    
    def test_agent_initialization(self):
        """Test agent can be initialized with mock model."""
        from text2x.agentcore.agents.auto_annotation.strands_agent import AutoAnnotationAgent
        
        mock_model = MagicMock()
        
        agent = AutoAnnotationAgent(
            model=mock_model,
            name="test_auto_annotation",
        )
        
        assert agent.name == "test_auto_annotation"
        assert agent.agent is not None
    
    def test_agent_system_prompt(self):
        """Test agent has correct system prompt."""
        from text2x.agentcore.agents.auto_annotation.strands_agent import (
            AutoAnnotationAgent,
            AUTO_ANNOTATION_SYSTEM_PROMPT,
        )
        
        mock_model = MagicMock()
        agent = AutoAnnotationAgent(model=mock_model)
        
        assert agent.get_system_prompt() == AUTO_ANNOTATION_SYSTEM_PROMPT
        assert "sample_data" in agent.get_system_prompt()
        assert "column_stats" in agent.get_system_prompt()
        assert "save_annotation" in agent.get_system_prompt()


class TestAnnotationAssistantAgentStrands:
    """Tests for Strands AnnotationAssistantAgent."""
    
    def test_agent_initialization(self):
        """Test agent can be initialized with mock model."""
        from text2x.agentcore.agents.annotation_assistant.strands_agent import AnnotationAssistantAgent
        
        mock_model = MagicMock()
        
        agent = AnnotationAssistantAgent(
            model=mock_model,
            name="test_annotation_assistant",
        )
        
        assert agent.name == "test_annotation_assistant"
        assert agent.agent is not None
    
    def test_agent_system_prompt(self):
        """Test agent has correct system prompt."""
        from text2x.agentcore.agents.annotation_assistant.strands_agent import (
            AnnotationAssistantAgent,
            ANNOTATION_ASSISTANT_SYSTEM_PROMPT,
        )
        
        mock_model = MagicMock()
        agent = AnnotationAssistantAgent(model=mock_model)
        
        assert agent.get_system_prompt() == ANNOTATION_ASSISTANT_SYSTEM_PROMPT
        assert "list_annotations" in agent.get_system_prompt()


class TestQueryAgentStrands:
    """Tests for Strands QueryAgent."""
    
    def test_agent_initialization(self):
        """Test agent can be initialized with mock model."""
        from text2x.agentcore.agents.query.strands_agent import QueryAgent
        
        mock_model = MagicMock()
        
        agent = QueryAgent(
            model=mock_model,
            name="test_query",
        )
        
        assert agent.name == "test_query"
        assert agent.agent is not None
    
    def test_agent_system_prompt_without_schema(self):
        """Test agent system prompt without schema context."""
        from text2x.agentcore.agents.query.strands_agent import QueryAgent, get_query_system_prompt
        
        mock_model = MagicMock()
        agent = QueryAgent(model=mock_model)
        
        prompt = agent.get_system_prompt()
        assert "generate_query" in prompt
        assert "execute_query" in prompt
        assert "validate_query" in prompt
        assert "explain_query" in prompt
    
    def test_agent_system_prompt_with_schema(self):
        """Test agent system prompt with schema context."""
        from text2x.agentcore.agents.query.strands_agent import get_query_system_prompt
        
        schema_context = {
            "tables": [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "integer"},
                        {"name": "name", "type": "varchar"},
                    ]
                }
            ]
        }
        
        prompt = get_query_system_prompt(schema_context)
        assert "users" in prompt
        assert "id" in prompt
        assert "integer" in prompt


class TestStrandsRuntimeCreation:
    """Tests for Strands runtime creation."""
    
    def test_create_runtime_with_strands_flag(self):
        """Test creating runtime with use_strands=True."""
        from text2x.agentcore.strands_runtime import AgentCore
        
        runtime = AgentCore(use_strands=True)
        
        assert runtime.use_strands is True
        assert runtime.is_started is False
    
    def test_create_runtime_with_legacy_flag(self):
        """Test creating runtime with use_strands=False."""
        from text2x.agentcore.strands_runtime import AgentCore
        
        runtime = AgentCore(use_strands=False)
        
        assert runtime.use_strands is False
        assert runtime.is_started is False
    
    def test_create_agentcore_factory(self):
        """Test create_agentcore factory function."""
        from text2x.agentcore.strands_runtime import create_agentcore
        
        runtime = create_agentcore(use_strands=True)
        
        assert runtime is not None
        assert runtime.use_strands is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
