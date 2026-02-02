"""Query agent - converts natural language to SQL queries.

Refactored to use Strands SDK with LiteLLM for model calls.

This agent provides tools to help users convert natural language questions
into executable SQL queries:
- generate_query: Generate SQL query from natural language
- execute_query: Execute a SQL query and return results
- validate_query: Validate SQL query syntax and semantics
- explain_query: Explain what a SQL query does in natural language

Supports multi-turn chat for iterative query refinement.
"""
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from strands import Agent
from strands.tools import tool

from text2x.providers.base import QueryProvider

logger = logging.getLogger(__name__)


# Tool context dataclass to share state between tools
@dataclass
class QueryToolContext:
    """Context shared between query tools."""
    provider: Optional[QueryProvider] = None
    provider_id: str = ""
    schema_context: Dict[str, Any] = None
    enable_execution: bool = False

    def __post_init__(self):
        if self.schema_context is None:
            self.schema_context = {}


# Global context
_query_context: Optional[QueryToolContext] = None


def set_query_context(context: QueryToolContext) -> None:
    """Set the global query tool context."""
    global _query_context
    _query_context = context


def get_query_context() -> QueryToolContext:
    """Get the global query tool context."""
    if _query_context is None:
        raise RuntimeError("Query tool context not initialized")
    return _query_context


# Define tools as standalone functions with @tool decorator

@tool
def generate_query(user_question: str, additional_context: str = "") -> dict:
    """Generate a SQL query from a natural language question.

    Args:
        user_question: The natural language question to convert to SQL
        additional_context: Optional additional context or constraints

    Returns:
        Dictionary with generated query and explanation
    """
    ctx = get_query_context()

    if not ctx.provider:
        return {"success": False, "error": "Provider not configured"}

    if not user_question:
        return {"success": False, "error": "user_question is required"}

    try:
        # Build schema info from context
        schema_info = ""
        tables = ctx.schema_context.get("tables", [])
        if tables:
            schema_info = "Available tables:\n"
            for table in tables:
                table_name = table.get("name", "unknown")
                columns = table.get("columns", [])
                schema_info += f"\n{table_name}:\n"
                for col in columns:
                    col_name = col.get("name", "unknown")
                    col_type = col.get("type", "unknown")
                    schema_info += f"  - {col_name} ({col_type})\n"

        # For tool-based generation, we use a simple template approach
        # The actual query generation happens via the LLM agent loop
        prompt = f"""Generate a SQL query for: {user_question}
        
{schema_info}

{f"Additional context: {additional_context}" if additional_context else ""}

Return the query that best answers this question."""

        # Since we're in a tool, we return a template for simple cases
        # Complex generation happens via the agent's natural conversation
        return {
            "success": True,
            "query": f"-- Generated query for: {user_question}\n-- Please provide the SQL query",
            "explanation": f"Query to answer: {user_question}",
            "needs_generation": True,
            "schema_context": schema_info,
        }
    except Exception as e:
        logger.error(f"Failed to generate query: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to generate query: {str(e)}",
        }


@tool
def execute_query(query: str) -> dict:
    """Execute a SQL query and return results.

    Args:
        query: The SQL query to execute

    Returns:
        Dictionary with execution results
    """
    ctx = get_query_context()

    if not ctx.provider:
        return {"success": False, "error": "Provider not configured"}

    if not query:
        return {"success": False, "error": "query is required"}

    if not ctx.enable_execution:
        return {
            "success": False,
            "error": "Query execution is disabled. Enable execution to run queries.",
        }

    try:
        import asyncio

        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run,
                    ctx.provider.execute_query(query, limit=100)
                ).result()
        else:
            result = asyncio.run(ctx.provider.execute_query(query, limit=100))

        if result and result.success:
            return {
                "success": True,
                "row_count": result.row_count,
                "columns": result.columns or [],
                "rows": result.sample_rows[:100] or [],
                "execution_time_ms": getattr(result, "execution_time_ms", 0),
            }
        else:
            return {
                "success": False,
                "error": result.error if result else "Query execution failed",
            }
    except Exception as e:
        logger.error(f"Failed to execute query: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to execute query: {str(e)}",
        }


@tool
def validate_query(query: str) -> dict:
    """Validate a SQL query for syntax and safety.

    Args:
        query: The SQL query to validate

    Returns:
        Dictionary with validation results
    """
    ctx = get_query_context()

    if not query:
        return {"success": False, "error": "query is required"}

    try:
        query_upper = query.upper().strip()

        # Check for dangerous operations
        warnings = []
        if "DROP" in query_upper or "TRUNCATE" in query_upper:
            warnings.append("Query contains potentially dangerous DROP/TRUNCATE operation")

        if "DELETE" in query_upper and "WHERE" not in query_upper:
            warnings.append("DELETE without WHERE clause will affect all rows")

        if "UPDATE" in query_upper and "WHERE" not in query_upper:
            warnings.append("UPDATE without WHERE clause will affect all rows")

        # Try to validate with provider if available
        if ctx.provider and hasattr(ctx.provider, "validate_syntax"):
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    validation_result = pool.submit(
                        asyncio.run,
                        ctx.provider.validate_syntax(query)
                    ).result()
            else:
                validation_result = asyncio.run(ctx.provider.validate_syntax(query))

            if not validation_result.valid:
                return {
                    "success": False,
                    "valid": False,
                    "errors": [validation_result.error] if validation_result.error else ["Invalid query"],
                    "warnings": warnings,
                }

        return {
            "success": True,
            "valid": True,
            "errors": [],
            "warnings": warnings,
        }

    except Exception as e:
        logger.error(f"Failed to validate query: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to validate query: {str(e)}",
        }


@tool
def explain_query(query: str) -> dict:
    """Explain what a SQL query does in natural language.

    Args:
        query: The SQL query to explain

    Returns:
        Dictionary with the explanation
    """
    if not query:
        return {"success": False, "error": "query is required"}

    try:
        # Parse the query to provide a basic explanation
        query_upper = query.upper().strip()

        parts = []

        if query_upper.startswith("SELECT"):
            parts.append("This is a SELECT query that retrieves data")
        elif query_upper.startswith("INSERT"):
            parts.append("This is an INSERT query that adds new data")
        elif query_upper.startswith("UPDATE"):
            parts.append("This is an UPDATE query that modifies existing data")
        elif query_upper.startswith("DELETE"):
            parts.append("This is a DELETE query that removes data")
        else:
            parts.append("This query performs a database operation")

        if "FROM" in query_upper:
            parts.append("from one or more tables")

        if "WHERE" in query_upper:
            parts.append("with filtering conditions")

        if "JOIN" in query_upper:
            parts.append("joining multiple tables together")

        if "GROUP BY" in query_upper:
            parts.append("grouping results")

        if "ORDER BY" in query_upper:
            parts.append("with ordered results")

        if "LIMIT" in query_upper:
            parts.append("with a limited number of results")

        explanation = " ".join(parts) + "."

        return {
            "success": True,
            "explanation": explanation,
            "query": query,
        }

    except Exception as e:
        logger.error(f"Failed to explain query: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to explain query: {str(e)}",
        }


def get_query_system_prompt(schema_context: Dict[str, Any] = None) -> str:
    """Get system prompt for query agent with optional schema context.

    Args:
        schema_context: Optional schema context with tables and columns

    Returns:
        System prompt string
    """
    schema_info = ""
    if schema_context:
        tables = schema_context.get("tables", [])
        if tables:
            schema_info = "\n\n**Available Database Schema:**\n"
            for table in tables:
                table_name = table.get("name", "unknown")
                columns = table.get("columns", [])
                schema_info += f"\n- Table: `{table_name}`\n"
                if columns:
                    schema_info += "  Columns:\n"
                    for col in columns:
                        col_name = col.get("name", "unknown")
                        col_type = col.get("type", "unknown")
                        schema_info += f"    - `{col_name}` ({col_type})\n"

    return f"""You are an expert SQL query generation assistant. Your role is to help users convert natural language questions into accurate, efficient SQL queries.

You have access to the following tools:

1. **generate_query** - Generate a SQL query from natural language
   - user_question (required): The natural language question
   - additional_context (optional): Additional context or constraints

2. **execute_query** - Execute a SQL query and return results
   - query (required): The SQL query to execute

3. **validate_query** - Validate a SQL query for syntax and semantic correctness
   - query (required): The SQL query to validate

4. **explain_query** - Explain what a SQL query does in natural language
   - query (required): The SQL query to explain

**Your responsibilities:**
1. Understand user's natural language questions and convert them to SQL
2. Generate accurate, efficient, and safe SQL queries
3. Provide clear explanations of what each query does
4. Validate queries for correctness before execution
5. Help users refine queries through iterative conversation
6. Ask clarifying questions when requirements are ambiguous

**Best practices:**
- Always explain the generated query in simple terms
- Use proper SQL formatting and indentation
- Avoid dangerous operations (DROP, TRUNCATE, DELETE without WHERE) unless explicitly requested
- Consider performance implications (use indexes, avoid SELECT *, add LIMIT for large results)
- Validate column and table names against the schema
- Ask for clarification if the question is ambiguous{schema_info}

**Response format:**
When responding to user questions:
1. Acknowledge the question
2. Generate the SQL query
3. Explain what the query does
4. Note any assumptions or limitations
5. Offer to refine or modify the query if needed

Start by greeting the user and asking how you can help them query their database."""


class QueryAgent:
    """Query agent using Strands SDK with LiteLLM.

    Converts natural language questions into SQL queries.
    """

    def __init__(
        self,
        model,
        provider: Optional[QueryProvider] = None,
        name: str = "query",
    ):
        """Initialize query agent.

        Args:
            model: Strands model provider (e.g., LiteLLMModel)
            provider: Query provider for database access
            name: Agent name
        """
        self.name = name
        self.provider = provider
        self._model = model
        self._schema_context: Dict[str, Any] = {}

        # Create Strands Agent with tools
        self.agent = Agent(
            model=model,
            system_prompt=get_query_system_prompt(),
            tools=[generate_query, execute_query, validate_query, explain_query],
            name=name,
            description="Query agent for natural language to SQL conversion",
        )

        logger.info(f"QueryAgent '{name}' initialized with Strands SDK")

    def set_provider(self, provider: QueryProvider) -> None:
        """Set the query provider for this agent.

        Args:
            provider: Query provider instance
        """
        self.provider = provider
        logger.debug(f"Provider set for agent '{self.name}'")

    def _update_schema_context(self, schema_context: Dict[str, Any]) -> None:
        """Update schema context and recreate agent with new system prompt."""
        if schema_context != self._schema_context:
            self._schema_context = schema_context
            self.agent = Agent(
                model=self._model,
                system_prompt=get_query_system_prompt(schema_context),
                tools=[generate_query, execute_query, validate_query, explain_query],
                name=self.name,
                description="Query agent for natural language to SQL conversion",
            )

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process user input and return response.

        Input:
            - user_message: str - User's natural language question
            - provider_id: str - Provider ID for context
            - schema_context: dict - Optional schema context (tables, columns)
            - enable_execution: bool - Whether to execute the query (default: False)
            - reset_conversation: bool - Reset conversation history

        Output:
            - response: str - Agent's response
            - generated_query: str - Generated SQL query (if any)
            - query_explanation: str - Explanation of what the query does
            - execution_result: dict - Query execution result (if executed)
            - tool_calls: List[Dict] - Tool calls made (if any)
        """
        user_message = input_data["user_message"]
        provider_id = input_data.get("provider_id", "")
        schema_context = input_data.get("schema_context", {})
        enable_execution = input_data.get("enable_execution", False)
        reset_conversation = input_data.get("reset_conversation", False)

        # Update schema context if changed
        self._update_schema_context(schema_context)

        # Set up tool context
        ctx = QueryToolContext(
            provider=self.provider,
            provider_id=provider_id,
            schema_context=schema_context,
            enable_execution=enable_execution,
        )
        set_query_context(ctx)

        # Reset conversation if requested
        if reset_conversation:
            self.agent = Agent(
                model=self._model,
                system_prompt=get_query_system_prompt(schema_context),
                tools=[generate_query, execute_query, validate_query, explain_query],
                name=self.name,
                description="Query agent for natural language to SQL conversion",
            )

        # Invoke the Strands agent
        result = self.agent(user_message)

        # Extract response
        response_text = str(result)

        # Extract tool calls and results
        tool_calls = []
        generated_query = None
        query_explanation = None
        execution_result = None

        if hasattr(result, 'messages'):
            for msg in result.messages:
                if hasattr(msg, 'tool_use'):
                    tool_name = msg.tool_use.name if hasattr(msg.tool_use, 'name') else str(msg.tool_use)
                    tool_calls.append({
                        "tool": tool_name,
                        "result": "executed",
                    })

        # Try to extract SQL query from response
        if "```sql" in response_text.lower():
            try:
                start = response_text.lower().find("```sql") + 6
                end = response_text.find("```", start)
                if end > start:
                    generated_query = response_text[start:end].strip()
            except Exception:
                pass

        return {
            "response": response_text,
            "generated_query": generated_query,
            "query_explanation": query_explanation,
            "execution_result": execution_result,
            "tool_calls": tool_calls,
        }

    def get_system_prompt(self, schema_context: Dict[str, Any] = None) -> str:
        """Get system prompt for query agent."""
        return get_query_system_prompt(schema_context)
