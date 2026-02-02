"""Strands-based Query Generation Agent.

This module provides a query generation agent using the Strands SDK,
which enables agentic tool use for schema lookup and SQL validation.
"""
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import boto3

from strands import Agent
from strands.models import BedrockModel

from .tools import (
    get_schema_info,
    validate_sql_syntax,
    get_sample_data,
    register_schema_provider,
    clear_schema_registry,
)


# Default model for query generation - uses cross-region inference
DEFAULT_MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
DEFAULT_REGION = os.getenv("AWS_REGION", "us-east-1")


@dataclass
class QueryGenerationResult:
    """Result from query generation."""
    sql_query: str
    explanation: str
    confidence: float = 0.0
    tables_used: List[str] = field(default_factory=list)
    validation_notes: List[str] = field(default_factory=list)
    raw_response: Optional[str] = None


class StrandsQueryAgent:
    """Query generation agent using Strands SDK.
    
    This agent uses Strands' tool-use capabilities to:
    1. Look up database schema information
    2. Generate SQL queries based on natural language
    3. Validate the generated SQL
    4. Provide explanations for the generated queries
    
    Example:
        ```python
        from text2x.agents.strands import StrandsQueryAgent
        from text2x.providers.sql import SQLProvider
        
        # Create provider
        provider = SQLProvider(connection_string="...")
        
        # Create agent
        agent = StrandsQueryAgent(provider)
        
        # Generate query
        result = agent.generate_query("Show all users who signed up last month")
        print(result.sql_query)
        print(result.explanation)
        ```
    """
    
    def __init__(
        self,
        provider: Optional[Any] = None,
        provider_id: str = "default",
        model_id: str = DEFAULT_MODEL_ID,
        region: str = DEFAULT_REGION,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        """Initialize the Strands query agent.
        
        Args:
            provider: Optional QueryProvider for schema lookup.
            provider_id: ID to use for the provider in tool registry.
            model_id: Bedrock model ID to use.
            region: AWS region for Bedrock.
            temperature: Model temperature (lower = more deterministic).
            max_tokens: Maximum tokens in response.
        """
        self.provider = provider
        self.provider_id = provider_id
        self.model_id = model_id
        self.region = region
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Register provider for tool access
        if provider:
            register_schema_provider(provider_id, provider)
        
        # Create the Bedrock model
        self._model = self._create_model()
        
        # Create the Strands agent with tools
        self._agent = self._create_agent()
    
    def _create_model(self) -> BedrockModel:
        """Create the Bedrock model for the agent."""
        # Create boto session with region
        session = boto3.Session(region_name=self.region)
        
        return BedrockModel(
            boto_session=session,
            model_id=self.model_id,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
    
    def _create_agent(self) -> Agent:
        """Create the Strands agent with tools."""
        # Define tools the agent can use
        tools = [
            get_schema_info,
            validate_sql_syntax,
            get_sample_data,
        ]
        
        # System prompt for query generation
        system_prompt = self._build_system_prompt()
        
        return Agent(
            model=self._model,
            tools=tools,
            system_prompt=system_prompt,
        )
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the query generation agent."""
        return """You are an expert SQL query generator. Your role is to convert natural language questions into accurate, efficient SQL queries.

## Your Workflow

1. **Understand the Request**: Analyze the user's natural language query to understand what data they need.

2. **Look Up Schema**: Use the `get_schema_info` tool to understand the database structure, tables, and columns available.

3. **Generate SQL**: Based on the schema and user request, generate an appropriate SQL query.

4. **Validate**: Use the `validate_sql_syntax` tool to check your generated SQL for syntax errors.

5. **Explain**: Provide a clear explanation of what the query does and why you made certain choices.

## Response Format

Always respond with:

1. **SQL Query**: The generated SQL query, formatted properly.
2. **Explanation**: A clear explanation of:
   - What the query does
   - Which tables and columns are used
   - Any joins or conditions applied
   - Why you made specific choices

## Guidelines

- Always verify table and column names exist in the schema before using them
- Use appropriate JOINs when data spans multiple tables
- Include meaningful aliases for better readability
- Add comments for complex queries
- Consider performance (avoid SELECT * when specific columns are needed)
- Handle edge cases (NULL values, empty results)

## Tools Available

- `get_schema_info`: Get database schema (tables, columns, relationships)
- `validate_sql_syntax`: Validate SQL syntax and get formatting suggestions
- `get_sample_data`: Get sample rows from a table to understand data patterns

Always use these tools to ensure accuracy. Do not guess table or column names."""
    
    def generate_query(
        self,
        natural_language_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> QueryGenerationResult:
        """Generate SQL from natural language query.
        
        Args:
            natural_language_query: The user's question in natural language.
            context: Optional additional context (table hints, filters, etc.)
        
        Returns:
            QueryGenerationResult with SQL query and explanation.
        """
        # Build the prompt
        prompt = self._build_prompt(natural_language_query, context)
        
        # Invoke the agent
        response = self._agent(prompt)
        
        # Parse the response
        return self._parse_response(response, natural_language_query)
    
    def _build_prompt(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the prompt for the agent."""
        prompt_parts = [
            f"Generate a SQL query for the following request:\n\n{query}"
        ]
        
        if self.provider_id:
            prompt_parts.append(f"\nUse provider_id: '{self.provider_id}' when calling schema tools.")
        
        if context:
            if "table_hints" in context:
                prompt_parts.append(f"\nRelevant tables to consider: {', '.join(context['table_hints'])}")
            if "filters" in context:
                prompt_parts.append(f"\nApply these filters: {context['filters']}")
            if "additional_context" in context:
                prompt_parts.append(f"\nAdditional context: {context['additional_context']}")
        
        return "\n".join(prompt_parts)
    
    def _parse_response(
        self,
        response: Any,
        original_query: str
    ) -> QueryGenerationResult:
        """Parse the agent's response into a structured result."""
        # Get the response text
        if hasattr(response, 'message') and hasattr(response.message, 'content'):
            # Handle Strands response structure
            content = response.message.content
            if isinstance(content, list):
                # Extract text from content blocks
                raw_text = ""
                for block in content:
                    if hasattr(block, 'text'):
                        raw_text += block.text
                    elif isinstance(block, dict) and 'text' in block:
                        raw_text += block['text']
            else:
                raw_text = str(content)
        else:
            raw_text = str(response)
        
        # Extract SQL query from response
        sql_query = self._extract_sql(raw_text)
        
        # Extract explanation
        explanation = self._extract_explanation(raw_text, sql_query)
        
        # Extract tables mentioned
        tables_used = self._extract_tables(raw_text)
        
        return QueryGenerationResult(
            sql_query=sql_query,
            explanation=explanation,
            tables_used=tables_used,
            raw_response=raw_text,
            confidence=0.85 if sql_query else 0.0,  # Basic confidence
        )
    
    def _extract_sql(self, text: str) -> str:
        """Extract SQL query from response text."""
        import re
        
        # Try to find SQL in code blocks first
        sql_block_pattern = r'```sql\s*(.*?)\s*```'
        matches = re.findall(sql_block_pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()
        
        # Try generic code blocks
        code_block_pattern = r'```\s*(SELECT.*?)\s*```'
        matches = re.findall(code_block_pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()
        
        # Look for SQL keywords pattern outside code blocks
        sql_pattern = r'(SELECT\s+.*?(?:;|$))'
        matches = re.findall(sql_pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip().rstrip(';') + ';'
        
        return ""
    
    def _extract_explanation(self, text: str, sql_query: str) -> str:
        """Extract explanation from response text."""
        # Remove the SQL from text to get explanation
        explanation = text
        if sql_query:
            explanation = text.replace(sql_query, "")
        
        # Remove code block markers
        import re
        explanation = re.sub(r'```(?:sql)?\s*```', '', explanation)
        explanation = re.sub(r'```(?:sql)?', '', explanation)
        explanation = re.sub(r'```', '', explanation)
        
        # Clean up
        explanation = explanation.strip()
        
        # If explanation is too long, try to find a summary section
        if len(explanation) > 2000:
            # Look for explanation section
            sections = re.split(r'\n\s*(?:Explanation|What this query does|Summary)[:.]?\s*\n', 
                               explanation, flags=re.IGNORECASE)
            if len(sections) > 1:
                explanation = sections[-1].strip()
        
        return explanation if explanation else "SQL query generated based on the request."
    
    def _extract_tables(self, text: str) -> List[str]:
        """Extract table names mentioned in the response."""
        import re
        
        tables = set()
        
        # Look for FROM and JOIN clauses
        from_pattern = r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        join_pattern = r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        
        tables.update(re.findall(from_pattern, text, re.IGNORECASE))
        tables.update(re.findall(join_pattern, text, re.IGNORECASE))
        
        return list(tables)
    
    def set_provider(self, provider: Any, provider_id: Optional[str] = None) -> None:
        """Update the provider for schema lookup.
        
        Args:
            provider: The new QueryProvider.
            provider_id: Optional new provider ID.
        """
        if provider_id:
            self.provider_id = provider_id
        self.provider = provider
        register_schema_provider(self.provider_id, provider)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        clear_schema_registry()


def create_query_agent(
    provider: Optional[Any] = None,
    provider_id: str = "default",
    model_id: str = DEFAULT_MODEL_ID,
    region: str = DEFAULT_REGION,
    **kwargs
) -> StrandsQueryAgent:
    """Factory function to create a StrandsQueryAgent.
    
    Args:
        provider: Optional QueryProvider for schema lookup.
        provider_id: ID to use for the provider in tool registry.
        model_id: Bedrock model ID to use.
        region: AWS region for Bedrock.
        **kwargs: Additional arguments passed to StrandsQueryAgent.
    
    Returns:
        Configured StrandsQueryAgent instance.
    
    Example:
        ```python
        from text2x.agents.strands import create_query_agent
        
        agent = create_query_agent(
            provider=my_provider,
            temperature=0.2
        )
        result = agent.generate_query("Show all active users")
        ```
    """
    return StrandsQueryAgent(
        provider=provider,
        provider_id=provider_id,
        model_id=model_id,
        region=region,
        **kwargs
    )
