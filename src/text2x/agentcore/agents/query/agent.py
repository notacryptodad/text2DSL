"""Query agent - converts natural language to SQL queries.

This agent provides tools to help users convert natural language questions
into executable SQL queries:
- generate_query: Generate SQL query from natural language
- execute_query: Execute a SQL query and return results
- validate_query: Validate SQL query syntax and semantics
- explain_query: Explain what a SQL query does in natural language

Supports multi-turn chat for iterative query refinement.
"""
import json
import time
import logging
from typing import Dict, Any, List, Optional

from text2x.agentcore.agents.base import AgentCoreBaseAgent
from text2x.providers.base import QueryProvider

logger = logging.getLogger(__name__)


class QueryAgent(AgentCoreBaseAgent):
    """Query agent for natural language to SQL conversion.

    Responsibilities:
    - Convert natural language questions to SQL queries
    - Validate generated queries
    - Execute queries and return results
    - Explain queries in natural language
    - Support multi-turn conversations for query refinement
    """

    def __init__(
        self,
        runtime: "AgentCore",
        name: str,
        provider: Optional[QueryProvider] = None,
    ):
        """Initialize query agent.

        Args:
            runtime: AgentCore runtime instance
            name: Agent name
            provider: Query provider for database access
        """
        super().__init__(runtime, name)

        self.provider = provider

        # Register tools
        self.register_tool("generate_query", self._generate_query)
        self.register_tool("execute_query", self._execute_query)
        self.register_tool("validate_query", self._validate_query)
        self.register_tool("explain_query", self._explain_query)

        logger.info(f"QueryAgent '{name}' initialized with {len(self.tools)} tools")

    def set_provider(self, provider: QueryProvider) -> None:
        """Set the query provider for this agent.

        Args:
            provider: Query provider instance
        """
        self.provider = provider
        logger.debug(f"Provider set for agent '{self.name}'")

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
            - conversation_history: List[Dict] - Full conversation history
        """
        start_time = time.time()

        user_message = input_data["user_message"]
        provider_id = input_data.get("provider_id", "")
        schema_context = input_data.get("schema_context", {})
        enable_execution = input_data.get("enable_execution", False)
        reset_conversation = input_data.get("reset_conversation", False)

        # Reset conversation if requested
        if reset_conversation:
            self.clear_history()

        # Add user message to history
        self.add_message("user", user_message)

        # Build messages for LLM with system prompt and conversation history
        messages = [
            {"role": "system", "content": self.get_system_prompt(schema_context)},
        ]

        # Add conversation history
        messages.extend(self.conversation_history)

        # Call LLM
        response = await self.invoke_llm(messages, temperature=0.2)

        # Parse response for tool calls and extract generated query
        tool_calls = []
        assistant_response = response["content"]
        generated_query = None
        query_explanation = None
        execution_result = None

        # Check if LLM wants to use tools
        tool_use_detected = False
        if "```json" in assistant_response.lower() or "{" in assistant_response:
            try:
                # Extract JSON from response
                json_start = assistant_response.find("{")
                json_end = assistant_response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_content = assistant_response[json_start:json_end]
                    tool_request = json.loads(json_content)

                    # Execute tool if requested
                    if "tool" in tool_request and tool_request["tool"] in self.tools:
                        tool_name = tool_request["tool"]
                        tool_params = tool_request.get("parameters", {})

                        # Add provider_id and schema_context to tool params
                        tool_params["provider_id"] = provider_id
                        tool_params["schema_context"] = schema_context
                        tool_params["enable_execution"] = enable_execution

                        # Execute tool
                        tool_result = await self.tools[tool_name](tool_params)
                        tool_calls.append({
                            "tool": tool_name,
                            "parameters": tool_params,
                            "result": tool_result,
                        })
                        tool_use_detected = True

                        # Extract query and explanation from tool results
                        if tool_name == "generate_query":
                            generated_query = tool_result.get("query")
                            query_explanation = tool_result.get("explanation")
                        elif tool_name == "execute_query":
                            execution_result = tool_result

                        # Get follow-up response from LLM with tool result
                        tool_result_message = (
                            f"\n\nTool '{tool_name}' executed successfully. Result:\n"
                            f"{json.dumps(tool_result, indent=2)}\n\n"
                            f"Please provide a summary for the user."
                        )
                        messages.append({"role": "assistant", "content": assistant_response})
                        messages.append({"role": "user", "content": tool_result_message})

                        follow_up_response = await self.invoke_llm(messages, temperature=0.2)
                        assistant_response = follow_up_response["content"]
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                # Not a tool call, just a regular response
                logger.debug(f"Not a tool call or failed to parse: {e}")

        # If no tool was called but we have a natural language question, auto-generate query
        if not tool_use_detected and not any(
            keyword in user_message.lower()
            for keyword in ["explain", "what does", "validate", "check"]
        ):
            logger.info("Auto-generating query for user question")
            tool_params = {
                "user_question": user_message,
                "provider_id": provider_id,
                "schema_context": schema_context,
                "enable_execution": enable_execution,
            }

            # Generate query
            query_result = await self._generate_query(tool_params)
            tool_calls.append({
                "tool": "generate_query",
                "parameters": tool_params,
                "result": query_result,
            })

            generated_query = query_result.get("query")
            query_explanation = query_result.get("explanation")

            # Execute if requested
            if enable_execution and generated_query and query_result.get("success"):
                exec_params = {
                    "query": generated_query,
                    "provider_id": provider_id,
                    "schema_context": schema_context,
                    "enable_execution": enable_execution,
                }
                execution_result = await self._execute_query(exec_params)
                tool_calls.append({
                    "tool": "execute_query",
                    "parameters": exec_params,
                    "result": execution_result,
                })

            # Build a friendly response
            if query_result.get("success"):
                assistant_response = f"I've generated a SQL query for your question:\n\n```sql\n{generated_query}\n```\n\n"
                if query_explanation:
                    assistant_response += f"**Explanation:** {query_explanation}\n\n"
                if execution_result:
                    if execution_result.get("success"):
                        row_count = execution_result.get("row_count", 0)
                        assistant_response += f"✓ Query executed successfully and returned {row_count} row(s)."
                    else:
                        assistant_response += f"⚠️ Query execution failed: {execution_result.get('error', 'Unknown error')}"
            else:
                assistant_response = f"I couldn't generate a query: {query_result.get('error', 'Unknown error')}"

        # Add assistant response to history
        self.add_message("assistant", assistant_response)

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Processed query request in {duration_ms:.2f}ms, "
            f"tool_calls={len(tool_calls)}, conversation_turns={len(self.conversation_history)}"
        )

        return {
            "response": assistant_response,
            "generated_query": generated_query,
            "query_explanation": query_explanation,
            "execution_result": execution_result,
            "tool_calls": tool_calls,
            "conversation_history": self.get_history(),
        }

    def get_system_prompt(self, schema_context: Dict[str, Any] = None) -> str:
        """Get system prompt for query agent.

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
   Parameters:
   - user_question: string (required) - The natural language question
   - additional_context: string (optional) - Additional context or constraints

2. **execute_query** - Execute a SQL query and return results
   Parameters:
   - query: string (required) - The SQL query to execute

3. **validate_query** - Validate a SQL query for syntax and semantic correctness
   Parameters:
   - query: string (required) - The SQL query to validate

4. **explain_query** - Explain what a SQL query does in natural language
   Parameters:
   - query: string (required) - The SQL query to explain

**How to use tools:**
When you want to use a tool, respond with JSON in this format:
```json
{{
  "tool": "tool_name",
  "parameters": {{
    "param1": "value1",
    "param2": "value2"
  }}
}}
```

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

    async def _generate_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Generate SQL query from natural language.

        Parameters:
            - user_question: Natural language question
            - additional_context: Optional additional context
            - schema_context: Schema information
            - enable_execution: Whether to execute after generation

        Returns:
            Generated query and explanation
        """
        if not self.provider:
            return {"success": False, "error": "Provider not configured"}

        user_question = params.get("user_question")
        additional_context = params.get("additional_context", "")
        schema_context = params.get("schema_context", {})

        if not user_question:
            return {"success": False, "error": "user_question is required"}

        try:
            # Build prompt for query generation
            schema_info = ""
            tables = schema_context.get("tables", [])
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

            prompt = f"""Generate a SQL query for the following question:

Question: {user_question}

{schema_info}

{f"Additional context: {additional_context}" if additional_context else ""}

Provide:
1. The SQL query (use standard SQL syntax)
2. A brief explanation of what the query does

Format your response as JSON:
{{
  "query": "SELECT ... FROM ...",
  "explanation": "This query retrieves..."
}}"""

            messages = [
                {"role": "system", "content": "You are an expert SQL query generator. Always respond with valid JSON containing 'query' and 'explanation' fields."},
                {"role": "user", "content": prompt}
            ]

            response = await self.invoke_llm(messages, temperature=0.1)
            content = response["content"]

            # Parse JSON response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(content[json_start:json_end])
                query = result.get("query", "").strip()
                explanation = result.get("explanation", "").strip()

                # Basic validation
                if not query:
                    return {"success": False, "error": "Failed to generate query"}

                return {
                    "success": True,
                    "query": query,
                    "explanation": explanation,
                }
            else:
                return {"success": False, "error": "Failed to parse LLM response"}

        except Exception as e:
            logger.error(f"Failed to generate query: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to generate query: {str(e)}",
            }

    async def _execute_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Execute a SQL query.

        Parameters:
            - query: SQL query to execute
            - enable_execution: Must be True to actually execute

        Returns:
            Execution result with rows and metadata
        """
        if not self.provider:
            return {"success": False, "error": "Provider not configured"}

        query = params.get("query")
        enable_execution = params.get("enable_execution", False)

        if not query:
            return {"success": False, "error": "query is required"}

        if not enable_execution:
            return {
                "success": False,
                "error": "Query execution is disabled. Enable execution to run queries.",
            }

        try:
            # Execute query
            result = await self.provider.execute_query(query, limit=100)

            if result and result.success:
                return {
                    "success": True,
                    "row_count": result.row_count,
                    "columns": result.columns or [],
                    "rows": result.sample_rows[:100] or [],  # Limit to 100 rows
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

    async def _validate_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Validate a SQL query.

        Parameters:
            - query: SQL query to validate

        Returns:
            Validation result with errors/warnings
        """
        if not self.provider:
            return {"success": False, "error": "Provider not configured"}

        query = params.get("query")

        if not query:
            return {"success": False, "error": "query is required"}

        try:
            # Basic syntax validation
            query_upper = query.upper().strip()

            # Check for dangerous operations
            warnings = []
            if "DROP" in query_upper or "TRUNCATE" in query_upper:
                warnings.append("Query contains potentially dangerous DROP/TRUNCATE operation")

            if "DELETE" in query_upper and "WHERE" not in query_upper:
                warnings.append("DELETE without WHERE clause will affect all rows")

            if "UPDATE" in query_upper and "WHERE" not in query_upper:
                warnings.append("UPDATE without WHERE clause will affect all rows")

            # Try to validate with provider
            if hasattr(self.provider, "validate_syntax"):
                validation_result = await self.provider.validate_syntax(query)
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

    async def _explain_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Explain what a SQL query does.

        Parameters:
            - query: SQL query to explain

        Returns:
            Natural language explanation
        """
        query = params.get("query")

        if not query:
            return {"success": False, "error": "query is required"}

        try:
            prompt = f"""Explain the following SQL query in simple, clear language:

```sql
{query}
```

Describe:
1. What data it retrieves or modifies
2. Which tables it uses
3. Any filtering, sorting, or grouping applied
4. What the results represent

Keep the explanation concise and non-technical where possible."""

            messages = [
                {"role": "system", "content": "You are an expert at explaining SQL queries in simple terms."},
                {"role": "user", "content": prompt}
            ]

            response = await self.invoke_llm(messages, temperature=0.3)
            explanation = response["content"].strip()

            return {
                "success": True,
                "explanation": explanation,
            }

        except Exception as e:
            logger.error(f"Failed to explain query: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to explain query: {str(e)}",
            }
