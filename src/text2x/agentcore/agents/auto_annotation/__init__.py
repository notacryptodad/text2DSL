"""Auto-annotation agent for AgentCore."""
from text2x.agentcore.agents.auto_annotation.agent import AutoAnnotationAgent
from text2x.agentcore.agents.auto_annotation.strands_agent import (
    AutoAnnotationAgent as StrandsAutoAnnotationAgent,
)

__all__ = ["AutoAnnotationAgent", "StrandsAutoAnnotationAgent"]
