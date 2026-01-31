"""LLM Client for Text2X"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class LLMConfig:
    provider: str  # "bedrock" or "litellm"
    model: str
    temperature: float = 0.1
    max_tokens: int = 4096
    region: str = "us-east-1"
    api_base: str = ""

@dataclass
class LLMResponse:
    content: str
    tokens_used: int
    model: str

class LLMClient:
    """Unified LLM client supporting Bedrock and LiteLLM"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    async def invoke(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Invoke LLM with messages"""
        # Implementation depends on provider
        raise NotImplementedError()
