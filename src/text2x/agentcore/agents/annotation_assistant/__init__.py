"""Annotation assistant agent for AgentCore."""
from text2x.agentcore.agents.annotation_assistant.agent import AnnotationAssistantAgent
from text2x.agentcore.agents.annotation_assistant.strands_agent import (
    AnnotationAssistantAgent as StrandsAnnotationAssistantAgent,
)

__all__ = ["AnnotationAssistantAgent", "StrandsAnnotationAssistantAgent"]
