"""Base Agent class with LLM integration"""
import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx

# Import domain model ReasoningTrace (not the DB model)
import sys
from pathlib import Path
import importlib.util

_models_file = Path(__file__).parent.parent / "models.py"
spec = importlib.util.spec_from_file_location("text2x_domain_models", _models_file)
if spec and spec.loader:
    _domain_models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_domain_models)
    ReasoningTrace = _domain_models.ReasoningTrace
else:
    # Fallback if dynamic import fails
    from text2x.models import ReasoningTrace


@dataclass
class LLMConfig:
    """Configuration for LLM client"""
    model: str = "gpt-4o"
    api_base: str = "https://api.openai.com/v1"
    api_key: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: float = 120.0


@dataclass
class LLMMessage:
    """Single message in LLM conversation"""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """Response from LLM"""
    content: str
    tokens_used: int
    model: str
    finish_reason: str


class LLMClient:
    """OpenAI-compatible LLM client"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)
    
    async def invoke(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Invoke LLM with messages"""
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens
        
        headers = {
            "Content-Type": "application/json",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        payload = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temp,
            "max_tokens": max_tok,
        }
        
        try:
            response = await self.client.post(
                f"{self.config.api_base}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            choice = data["choices"][0]
            return LLMResponse(
                content=choice["message"]["content"],
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                model=data["model"],
                finish_reason=choice["finish_reason"]
            )
        except Exception as e:
            raise RuntimeError(f"LLM invocation failed: {str(e)}") from e
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, llm_config: LLMConfig, agent_name: Optional[str] = None):
        self.llm_config = llm_config
        self.llm_client = LLMClient(llm_config)
        self.agent_name = agent_name or self.__class__.__name__
        self.reasoning_traces: List[ReasoningTrace] = []
    
    async def invoke_llm(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 3
    ) -> LLMResponse:
        """Invoke LLM with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                return await self.llm_client.invoke(messages, temperature, max_tokens)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                await asyncio.sleep(wait_time)
        
        raise RuntimeError("Max retries exceeded")
    
    def add_trace(
        self,
        step: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        duration_ms: float
    ) -> None:
        """Add reasoning trace entry"""
        trace = ReasoningTrace(
            agent_name=self.agent_name,
            step=step,
            timestamp=datetime.utcnow(),
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration_ms
        )
        self.reasoning_traces.append(trace)
    
    def get_traces(self) -> List[ReasoningTrace]:
        """Get all reasoning traces"""
        return self.reasoning_traces
    
    def clear_traces(self) -> None:
        """Clear reasoning traces"""
        self.reasoning_traces = []
    
    def build_system_prompt(self) -> str:
        """Build system prompt for this agent"""
        return f"""You are the {self.agent_name} in a multi-agent system for converting natural language queries to executable queries.
Your role is to provide accurate, concise, and well-reasoned responses.
Always think step-by-step and explain your reasoning."""
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return output. Must be implemented by subclasses."""
        pass
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.llm_client.close()
