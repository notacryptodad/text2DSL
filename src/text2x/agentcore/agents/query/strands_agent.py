"""Generic Query Agent - converts natural language to database queries.

Refactored to support multiple query languages (SQL, MongoDB, Splunk) using Strands SDK.

This agent provides tools to help users convert natural language questions
into executable database queries based on the provider type:
- SQL: generate_sql_query, execute_sql_query, validate_sql_query, explain_sql_query
- MongoDB: generate_mongo_query, execute_mongo_query, validate_mongo_query, explain_mongo_query
- Splunk: generate_spl_query, execute_spl_query, validate_spl_query, explain_spl_query

Supports multi-turn chat for iterative query refinement.
"""

import json
import logging
import asyncio
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass

from strands import Agent
from strands.tools import tool

from text2x.providers.base import QueryProvider

logger = logging.getLogger(__name__)

# Capture the main event loop for use from Strands worker threads
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Store the main event loop so tool functions can schedule coroutines on it."""
    global _main_loop
    _main_loop = loop


def _run_async(coro, timeout=120):
    """Run an async coroutine from a sync context, using the main event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    # If we're in the main event loop thread, just run directly (shouldn't happen from tools)
    if loop and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=timeout)

    # We're in a worker thread — schedule on the captured main loop
    if _main_loop and _main_loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, _main_loop)
        return future.result(timeout=timeout)

    # Fallback: no main loop captured, try asyncio.run (may fail with motor/asyncpg)
    logger.warning("[_run_async] No main event loop available, falling back to asyncio.run()")
    return asyncio.run(coro)


@dataclass
class QueryToolContext:
    """Context shared between query tools."""

    provider: Optional[QueryProvider] = None
    provider_id: str = ""
    schema_context: Dict[str, Any] = None
    enable_execution: bool = False
    query_language: str = ""
    event_queue: Optional[asyncio.Queue] = None

    def __post_init__(self):
        if self.schema_context is None:
            self.schema_context = {}


_global_context: Optional[QueryToolContext] = None


def set_query_context(context: QueryToolContext) -> None:
    """Set the global query tool context."""
    global _global_context
    _global_context = context


def get_query_context() -> QueryToolContext:
    """Get the global query tool context."""
    if _global_context is None:
        raise RuntimeError("Query tool context not initialized")
    return _global_context


def _emit_tool_event(ctx: QueryToolContext, tool_name: str, message: str):
    """Push a progress event to the SSE queue if available."""
    if ctx.event_queue and _main_loop:
        _main_loop.call_soon_threadsafe(
            ctx.event_queue.put_nowait,
            {"tool": tool_name, "message": message},
        )


def get_mongo_schema_info(schema_context: Dict[str, Any]) -> str:
    """Get MongoDB-style schema info from context."""
    schema_info = ""
    collections = schema_context.get("collections", [])
    tables = schema_context.get("tables", [])

    if collections:
        schema_info = "Available collections:\n"
        for coll in collections:
            coll_name = coll.get("name", "unknown")
            schema_info += f"\n{coll_name}:\n"
            for col in coll.get("columns", []):
                col_name = col.get("name", "unknown")
                col_type = col.get("type", "unknown")
                schema_info += f"  - {col_name} ({col_type})\n"

    if tables and not collections:
        schema_info = "Available tables (MongoDB collections):\n"
        for table in tables:
            table_name = table.get("name", "unknown")
            columns = table.get("columns", [])
            schema_info += f"\n{table_name}:\n"
            for col in columns:
                col_name = col.get("name", "unknown")
                col_type = col.get("type", "unknown")
                schema_info += f"  - {col_name} ({col_type})\n"

    return schema_info


def get_sql_schema_info(schema_context: Dict[str, Any]) -> str:
    """Get SQL-style schema info from context."""
    schema_info = ""
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
    return schema_info


def get_system_prompt(schema_context: Dict[str, Any], query_language: str) -> str:
    """Get system prompt based on query language."""

    if query_language == "MongoDB Query":
        schema_info = get_mongo_schema_info(schema_context)
        return f"""You are an expert MongoDB query generation assistant. Your role is to help users convert natural language questions into accurate MongoDB aggregation pipelines and queries.

You have access to the following tools:

1. **generate_mongo_query** - Generate a MongoDB query/aggregation pipeline from natural language
   - user_question (required): The natural language question
   - additional_context (optional): Additional context or constraints

2. **execute_mongo_query** - Execute a MongoDB query and return results
   - query (required): MongoDB query as JSON string with format: {{"collection": "name", "operation": "find|aggregate|...", "filter": {{...}}, "pipeline": [...]}}

3. **validate_mongo_query** - Validate MongoDB query syntax
   - query (required): MongoDB query as JSON string

4. **explain_mongo_query** - Explain what a MongoDB query does in natural language
   - query (required): MongoDB query as JSON string

**MongoDB Query Format:**
- Use `find` operation for simple queries with filter, projection, sort
- Use `aggregate` operation for complex pipelines with $match, $group, $lookup, etc.
- Always specify the collection name
- Use proper MongoDB operators: $match, $group, $sort, $limit, $skip, $project, $unwind, $lookup, etc.

**Your responsibilities:**
1. Understand user's natural language questions and convert them to MongoDB queries
2. Generate accurate, efficient aggregation pipelines
3. Provide clear explanations of each query
4. Validate queries for correctness before execution
5. Help users refine queries through iterative conversation
6. Ask clarifying questions when requirements are ambiguous{schema_info}

**Response format:**
When responding to user questions:
1. Acknowledge the question
2. Generate the MongoDB query in JSON format
3. Explain what the query does
4. Note any assumptions or limitations
5. Offer to refine or modify the query if needed

Example query format:
```json
{{
  "collection": "users",
  "operation": "aggregate",
  "pipeline": [
    {{"$match": {{"status": "active"}}}},
    {{"$group": {{"_id": "$country", "count": {{"$sum": 1}}}}}},
    {{"$sort": {{"count": -1}}}}
  ]
}}
```

Start by greeting the user and asking how you can help them query their MongoDB database."""

    elif query_language == "SPL":
        return """You are an expert Splunk SPL (Search Processing Language) query generation assistant.

You have access to tools for generating, executing, validating, and explaining Splunk queries.

**SPL Basics:**
- Use `search` command for filtering
- Use `stats`, `chart`, `timechart` for aggregation
- Use `table`, `fields` for formatting
- Use `|` pipe to chain commands

**Your responsibilities:**
1. Convert natural language to accurate SPL queries
2. Use appropriate time ranges
3. Optimize for performance
4. Explain query logic clearly

Start by greeting the user and asking how can help them search their Splunk data."""

    else:
        schema_info = get_sql_schema_info(schema_context)
        return f"""You are an expert SQL query generation assistant. Your role is to help users convert natural language questions into accurate, efficient SQL queries.

You have access to the following tools:

1. **generate_sql_query** - Generate a SQL query from natural language
   - user_question (required): The natural language question
   - additional_context (optional): Additional context or constraints

2. **execute_sql_query** - Execute a SQL query and return results
   - query (required): The SQL query to execute

3. **validate_sql_query** - Validate a SQL query for syntax and semantic correctness
   - query (required): The SQL query to validate

4. **explain_sql_query** - Explain what a SQL query does in natural language
   - query (required): The SQL query to explain

**Your responsibilities:**
1. Understand user's natural language questions and convert them to SQL
2. Generate accurate, efficient, and safe SQL queries
3. Provide clear explanations of what each query does
4. Validate queries for correctness before execution
5. Help users refine queries through iterative conversation
6. Ask clarifying questions when requirements are ambiguous{schema_info}

**Best practices:**
- Always explain the generated query in simple terms
- Use proper SQL formatting and indentation
- Avoid dangerous operations (DROP, TRUNCATE, DELETE without WHERE) unless explicitly requested
- Consider performance implications (use indexes, avoid SELECT *, add LIMIT for large results)
- Validate column and table names against the schema
- Ask for clarification if the question is ambiguous

**Response format:**
When responding to user questions:
1. Acknowledge the question
2. Generate the SQL query
3. Explain what the query does
4. Note any assumptions or limitations
5. Offer to refine or modify the query if needed

Start by greeting the user and asking how you can help them query their database."""


SQL_TOOLS = []
MONGODB_TOOLS = []
SPL_TOOLS = []


def create_sql_tools():
    """Create SQL-specific tools."""
    global SQL_TOOLS

    @tool
    def generate_sql_query(user_question: str, additional_context: str = "") -> dict:
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
            schema_info = get_sql_schema_info(ctx.schema_context)
            prompt = f"""Generate a SQL query for: {user_question}

{schema_info}

{f"Additional context: {additional_context}" if additional_context else ""}

Return the SQL query that best answers this question."""
            return {
                "success": True,
                "query": f"-- Generated query for: {user_question}\n-- Please provide the SQL query",
                "explanation": f"Query to answer: {user_question}",
                "needs_generation": True,
                "schema_context": schema_info,
            }
        except Exception as e:
            logger.error(f"Failed to generate SQL query: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to generate query: {str(e)}",
            }

    @tool
    def execute_sql_query(query: str) -> dict:
        """Execute a SQL query and return results.

        Args:
            query: The SQL query to execute

        Returns:
            Dictionary with execution results
        """
        logger.info(f"[execute_sql_query] Called with query length={len(query) if query else 0}")
        ctx = get_query_context()
        _emit_tool_event(ctx, "execute_sql_query", "Executing SQL query...")

        if not ctx.provider:
            logger.warning("[execute_sql_query] Provider not configured")
            return {"success": False, "error": "Provider not configured"}

        if not query:
            logger.warning("[execute_sql_query] Empty query")
            return {"success": False, "error": "query is required"}

        if not ctx.enable_execution:
            logger.info("[execute_sql_query] Execution disabled")
            return {
                "success": False,
                "error": "Query execution is disabled. Enable execution to run queries.",
            }

        try:
            import json
            import asyncio

            parsed_query = json.loads(query) if isinstance(query, str) else query
            logger.info(f"[execute_sql_query] Parsed query OK, provider={type(ctx.provider).__name__}")

            async def execute_async():
                return await ctx.provider.execute_query(query, limit=100)

            logger.info(f"[execute_sql_query] Running async via _run_async, thread={threading.current_thread().name}")
            result = _run_async(execute_async())

            logger.info(f"[execute_sql_query] Result: success={result.success if result else None}, rows={result.row_count if result and result.success else 0}")

            if result and result.success:
                return {
                    "success": True,
                    "row_count": result.row_count,
                    "columns": result.columns or [],
                    "rows": result.sample_rows[:100] or [],
                    "execution_time_ms": getattr(result, "execution_time_ms", 0),
                }
            else:
                error_msg = result.error if result else "Query execution failed"
                logger.warning(f"[execute_sql_query] Query failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                }
        except json.JSONDecodeError as e:
            logger.error(f"[execute_sql_query] JSON decode error: {e}")
            return {
                "success": False,
                "error": f"Invalid JSON format: {str(e)}",
            }
        except Exception as e:
            logger.error(f"[execute_sql_query] Exception: {type(e).__name__}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to execute query: {str(e)}",
            }

    @tool
    def validate_sql_query(query: str) -> dict:
        """Validate a SQL query for syntax and safety.

        Args:
            query: The SQL query to validate

        Returns:
            Dictionary with validation results
        """
        ctx = get_query_context()
        _emit_tool_event(ctx, "validate_sql_query", "Validating SQL query...")

        if not query:
            return {"success": False, "error": "query is required"}

        try:
            query_upper = query.upper().strip()
            warnings = []
            if "DROP" in query_upper or "TRUNCATE" in query_upper:
                warnings.append("Query contains potentially dangerous DROP/TRUNCATE operation")
            if "DELETE" in query_upper and "WHERE" not in query_upper:
                warnings.append("DELETE without WHERE clause will affect all rows")
            if "UPDATE" in query_upper and "WHERE" not in query_upper:
                warnings.append("UPDATE without WHERE clause will affect all rows")

            if ctx.provider and hasattr(ctx.provider, "validate_syntax"):
                logger.info(f"[validate_sql_query] Running provider validation, thread={threading.current_thread().name}")

                async def validate_async():
                    return await ctx.provider.validate_syntax(query)

                validation_result = _run_async(validate_async())

                logger.info(f"[validate_sql_query] Validation result: valid={validation_result.valid}")

                if not validation_result.valid:
                    return {
                        "success": False,
                        "valid": False,
                        "errors": [validation_result.error]
                        if validation_result.error
                        else ["Invalid query"],
                        "warnings": warnings,
                    }

            return {
                "success": True,
                "valid": True,
                "errors": [],
                "warnings": warnings,
            }
        except Exception as e:
            logger.error(f"Failed to validate SQL query: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to validate query: {str(e)}",
            }

            return {
                "success": True,
                "valid": True,
                "errors": [],
                "warnings": warnings,
            }
        except Exception as e:
            logger.error(f"Failed to validate SQL query: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to validate query: {str(e)}",
            }

    @tool
    def explain_sql_query(query: str) -> dict:
        """Explain what a SQL query does in natural language.

        Args:
            query: The SQL query to explain

        Returns:
            Dictionary with the explanation
        """
        if not query:
            return {"success": False, "error": "query is required"}

        try:
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
            logger.error(f"Failed to explain SQL query: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to explain query: {str(e)}",
            }

    SQL_TOOLS = [generate_sql_query, execute_sql_query, validate_sql_query, explain_sql_query]


def create_mongo_tools():
    """Create MongoDB-specific tools."""
    global MONGODB_TOOLS

    @tool
    def generate_mongo_query(user_question: str, additional_context: str = "") -> dict:
        """Generate a MongoDB query/aggregation from a natural language question.

        Args:
            user_question: The natural language question to convert to MongoDB query
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
            schema_info = get_mongo_schema_info(ctx.schema_context)
            prompt = f"""Generate a MongoDB query for: {user_question}

{schema_info}

{f"Additional context: {additional_context}" if additional_context else ""}

Return the MongoDB query that best answers this question. Use JSON format with collection name, operation (find/aggregate), and appropriate parameters."""
            return {
                "success": True,
                "query": f"{{'collection': '...', 'operation': 'aggregate', 'pipeline': [...]}}",
                "explanation": f"Query to answer: {user_question}",
                "needs_generation": True,
                "schema_context": schema_info,
            }
        except Exception as e:
            logger.error(f"Failed to generate MongoDB query: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to generate query: {str(e)}",
            }

    @tool
    def execute_mongo_query(query: str) -> dict:
        """Execute a MongoDB query and return results.

        Args:
            query: MongoDB query as JSON string

        Returns:
            Dictionary with execution results
        """
        logger.info(f"[execute_mongo_query] Called with query length={len(query) if query else 0}")
        ctx = get_query_context()
        _emit_tool_event(ctx, "execute_mongo_query", "Executing MongoDB query...")

        if not ctx.provider:
            logger.warning("[execute_mongo_query] Provider not configured")
            return {"success": False, "error": "Provider not configured"}

        if not query:
            logger.warning("[execute_mongo_query] Empty query")
            return {"success": False, "error": "query is required"}

        if not ctx.enable_execution:
            logger.info("[execute_mongo_query] Execution disabled")
            return {
                "success": False,
                "error": "Query execution is disabled. Enable execution to run queries.",
            }

        try:
            import json
            import asyncio

            parsed_query = json.loads(query) if isinstance(query, str) else query
            logger.info(f"[execute_mongo_query] Parsed query OK, provider={type(ctx.provider).__name__}")

            async def execute_async():
                return await ctx.provider.execute_query(query, limit=100)

            logger.info(f"[execute_mongo_query] Running async via _run_async, thread={threading.current_thread().name}")
            result = _run_async(execute_async())

            logger.info(f"[execute_mongo_query] Result: success={result.success if result else None}, rows={result.row_count if result and result.success else 0}")

            if result and result.success:
                return {
                    "success": True,
                    "row_count": result.row_count,
                    "columns": result.columns or [],
                    "rows": result.sample_rows[:100] or [],
                    "execution_time_ms": getattr(result, "execution_time_ms", 0),
                }
            else:
                error_msg = result.error if result else "Query execution failed"
                logger.warning(f"[execute_mongo_query] Query failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                }
        except json.JSONDecodeError as e:
            logger.error(f"[execute_mongo_query] JSON decode error: {e}")
            return {
                "success": False,
                "error": f"Invalid JSON format: {str(e)}",
            }
        except Exception as e:
            logger.error(f"[execute_mongo_query] Exception: {type(e).__name__}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to execute query: {str(e)}",
            }

    @tool
    def validate_mongo_query(query: str) -> dict:
        """Validate MongoDB query syntax.

        Args:
            query: MongoDB query as JSON string

        Returns:
            Dictionary with validation results
        """
        ctx = get_query_context()

        if not query:
            return {"success": False, "error": "query is required"}

        try:
            import json

            parsed_query = json.loads(query) if isinstance(query, str) else query

            if not isinstance(parsed_query, dict):
                return {"success": False, "error": "Query must be a JSON object"}

            if "collection" not in parsed_query:
                return {"success": False, "error": "Query must specify a 'collection' field"}

            valid_operations = ["find", "find_one", "aggregate", "count_documents", "distinct"]
            operation = parsed_query.get("operation", "find")
            if operation not in valid_operations:
                return {"success": False, "error": f"Invalid operation: {operation}"}

            return {
                "success": True,
                "valid": True,
                "errors": [],
                "warnings": [],
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Failed to validate MongoDB query: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Validation error: {str(e)}",
            }

    @tool
    def explain_mongo_query(query: str) -> dict:
        """Explain what a MongoDB query does in natural language.

        Args:
            query: MongoDB query as JSON string

        Returns:
            Dictionary with the explanation
        """
        if not query:
            return {"success": False, "error": "query is required"}

        try:
            import json

            parsed_query = json.loads(query) if isinstance(query, str) else query

            operation = parsed_query.get("operation", "find")
            collection = parsed_query.get("collection", "unknown")
            pipeline = parsed_query.get("pipeline", [])
            filter_query = parsed_query.get("filter", {})

            parts = []
            parts.append(f"This is a MongoDB {operation} operation")

            if operation == "aggregate":
                parts.append(f"on collection '{collection}'")
                if pipeline:
                    stages = [list(stage.keys())[0] if stage else "" for stage in pipeline if stage]
                    parts.append(f"with aggregation stages: {', '.join(stages)}")
            else:
                parts.append(f"on collection '{collection}'")
                if filter_query:
                    parts.append(f"filtering documents matching: {filter_query}")

            explanation = ". ".join(parts) + "."

            return {
                "success": True,
                "explanation": explanation,
                "query": query,
            }
        except Exception as e:
            logger.error(f"Failed to explain MongoDB query: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to explain query: {str(e)}",
            }

    MONGODB_TOOLS = [
        generate_mongo_query,
        execute_mongo_query,
        validate_mongo_query,
        explain_mongo_query,
    ]


create_sql_tools()
create_mongo_tools()


class QueryAgent:
    """Generic query agent supporting multiple query languages (SQL, MongoDB, Splunk).

    Converts natural language questions into appropriate database queries based on provider type.
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
        self._query_language = "SQL"
        self._agent: Optional[Agent] = None

        self._update_agent()

        logger.info(f"QueryAgent '{name}' initialized for {self._query_language}")

    def _get_tools_for_language(self, query_language: str):
        """Get tools appropriate for the query language."""
        if query_language == "MongoDB Query":
            return MONGODB_TOOLS
        else:
            return SQL_TOOLS

    def _update_agent(self):
        """Recreate the agent with current settings."""
        tools = self._get_tools_for_language(self._query_language)
        self._agent = Agent(
            model=self._model,
            system_prompt=get_system_prompt(self._schema_context, self._query_language),
            tools=tools,
            name=self.name,
            description=f"Query agent for {self._query_language}",
        )

    def set_provider(self, provider: QueryProvider) -> None:
        """Set the query provider for this agent.

        Args:
            provider: Query provider instance
        """
        self.provider = provider
        self._query_language = (
            provider.get_query_language() if hasattr(provider, "get_query_language") else "SQL"
        )
        logger.debug(f"Provider set for agent '{self.name}': {self._query_language}")
        self._update_agent()

    def _update_schema_context(self, schema_context: Dict[str, Any]) -> None:
        """Update schema context and recreate agent with new system prompt."""
        if schema_context != self._schema_context:
            self._schema_context = schema_context
            self._update_agent()

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
            - generated_query: str - Generated query (if any)
            - query_explanation: str - Explanation of what the query does
            - execution_result: dict - Query execution result (if executed)
            - tool_calls: List[Dict] - Tool calls made (if any)
        """
        user_message = input_data["user_message"]
        provider_id = input_data.get("provider_id", "")
        schema_context = input_data.get("schema_context", {})
        enable_execution = input_data.get("enable_execution", False)
        reset_conversation = input_data.get("reset_conversation", False)

        self._update_schema_context(schema_context)

        ctx = QueryToolContext(
            provider=self.provider,
            provider_id=provider_id,
            schema_context=schema_context,
            enable_execution=enable_execution,
            query_language=self._query_language,
            event_queue=input_data.get("event_queue"),
        )
        set_query_context(ctx)

        if reset_conversation:
            self._update_agent()

        result = await asyncio.to_thread(self._agent, user_message)

        response_text = str(result)

        tool_calls = []
        generated_query = None
        query_explanation = None
        execution_result = None

        if hasattr(result, "messages"):
            for msg in result.messages:
                if hasattr(msg, "tool_use"):
                    tool_name = (
                        msg.tool_use.name if hasattr(msg.tool_use, "name") else str(msg.tool_use)
                    )
                    tool_calls.append(
                        {
                            "tool": tool_name,
                            "result": "executed",
                        }
                    )

        if "```" in response_text:
            try:
                import re

                code_blocks = re.findall(r"```[\w]*\n([\s\S]*?)```", response_text, re.IGNORECASE)
                if code_blocks:
                    generated_query = code_blocks[0].strip()
            except Exception:
                pass

        if self._query_language == "MongoDB Query":
            try:
                import json

                if "```json" in response_text.lower():
                    start = response_text.lower().find("```json") + 7
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
            "query_language": self._query_language,
        }

    def get_system_prompt(self, schema_context: Dict[str, Any] = None) -> str:
        """Get system prompt for query agent."""
        return get_system_prompt(schema_context or self._schema_context, self._query_language)
