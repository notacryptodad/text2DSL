"""Annotation assistant agent - interactive helper for schema annotation tasks.

This agent provides conversational assistance for annotating database schemas:
- sample_data: Get sample rows from a table to understand data patterns
- column_stats: Get statistics about column values (distinct count, nulls, etc.)
- save_annotation: Save schema annotations to the database
- list_annotations: List existing annotations for a table or column

Supports multi-turn chat with conversation memory for iterative exploration.
"""
import json
import time
import logging
from typing import Dict, Any, List, Optional

from text2x.agentcore.agents.base import AgentCoreBaseAgent
from text2x.providers.base import QueryProvider
from text2x.repositories.annotation import SchemaAnnotationRepository

logger = logging.getLogger(__name__)


class AnnotationAssistantAgent(AgentCoreBaseAgent):
    """Interactive annotation assistant agent for schema exploration.

    Responsibilities:
    - Provide conversational interface for schema exploration
    - Help users understand database content through sampling and statistics
    - Guide users through the annotation process
    - Maintain conversation context for iterative workflows
    - Track current table/column being discussed
    """

    def __init__(
        self,
        runtime: "AgentCore",
        name: str,
        provider: Optional[QueryProvider] = None,
        annotation_repo: Optional[SchemaAnnotationRepository] = None,
    ):
        """Initialize annotation assistant agent.

        Args:
            runtime: AgentCore runtime instance
            name: Agent name
            provider: Query provider for database access
            annotation_repo: Repository for saving annotations
        """
        super().__init__(runtime, name)

        self.provider = provider
        self.annotation_repo = annotation_repo or SchemaAnnotationRepository()
        self.conversation_context: Dict[str, Any] = {}

        # Register tools
        self.register_tool("sample_data", self._sample_data)
        self.register_tool("column_stats", self._column_stats)
        self.register_tool("save_annotation", self._save_annotation)
        self.register_tool("list_annotations", self._list_annotations)
        self.register_tool("get_table_annotation", self._get_table_annotation)

        logger.info(f"AnnotationAssistantAgent '{name}' initialized with {len(self.tools)} tools")

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
            - message: str - User's message/question
            - conversation_id: str (optional) - Conversation ID for multi-turn
            - context: dict (optional) - Context like selected_table
            - provider_id: str - Provider ID for database access
            - user_id: str - User ID for saving annotations

        Output:
            - response: str - Agent's response
            - conversation_id: str - Conversation ID for multi-turn
            - tool_calls: List[Dict] - Tool calls made (if any)
        """
        start_time = time.time()

        message = input_data.get("message", "")
        conversation_id = input_data.get("conversation_id")
        context = input_data.get("context", {})
        provider_id = input_data.get("provider_id", "")
        user_id = input_data.get("user_id", "system")

        # Update conversation context
        if context:
            self.conversation_context.update(context)

        # Generate conversation_id if not provided
        if not conversation_id:
            conversation_id = f"conv_{int(time.time() * 1000)}"

        # Add user message to history
        self.add_message("user", message)

        # Build messages for LLM
        messages = [
            {"role": "system", "content": self._get_system_prompt_with_context()},
        ]

        # Add conversation history
        messages.extend(self.conversation_history)

        # Call LLM
        response = await self.invoke_llm(messages, temperature=0.3)

        # Parse response for tool calls
        tool_calls = []
        assistant_response = response["content"]

        # Check if LLM wants to use tools
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

                        # Add provider_id and user_id to tool params
                        tool_params["provider_id"] = provider_id
                        tool_params["user_id"] = user_id

                        # Execute tool
                        tool_result = await self.tools[tool_name](tool_params)
                        tool_calls.append({
                            "tool": tool_name,
                            "parameters": tool_params,
                            "result": tool_result,
                        })

                        # Get follow-up response from LLM with tool result
                        tool_result_message = (
                            f"\n\nTool '{tool_name}' executed successfully. Result:\n"
                            f"{json.dumps(tool_result, indent=2)}\n\n"
                            f"Please provide a helpful summary for the user based on this result."
                        )
                        messages.append({"role": "assistant", "content": assistant_response})
                        messages.append({"role": "user", "content": tool_result_message})

                        follow_up_response = await self.invoke_llm(messages, temperature=0.3)
                        assistant_response = follow_up_response["content"]
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                # Not a tool call, just a regular response
                logger.debug(f"Not a tool call or failed to parse: {e}")

        # Add assistant response to history
        self.add_message("assistant", assistant_response)

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Processed chat message in {duration_ms:.2f}ms, "
            f"tool_calls={len(tool_calls)}, conversation_turns={len(self.conversation_history)}"
        )

        return {
            "response": assistant_response,
            "conversation_id": conversation_id,
            "tool_calls": tool_calls,
        }

    def get_system_prompt(self) -> str:
        """Get base system prompt for annotation assistant."""
        return """You are a helpful database schema annotation assistant. Your role is to help users understand their database schemas and create meaningful annotations through interactive conversation.

You have access to the following tools:

1. **sample_data** - Get sample rows from a table
   Parameters:
   - table_name: string (required) - Name of the table
   - limit: integer (optional, default=10) - Number of rows to sample

2. **column_stats** - Get statistics about a column
   Parameters:
   - table_name: string (required) - Name of the table
   - column_name: string (required) - Name of the column

3. **save_annotation** - Save a schema annotation
   Parameters:
   - table_name: string (optional) - For table-level annotations
   - column_name: string (optional) - For column-level annotations (format: "table.column")
   - description: string (required) - Description of the table/column
   - business_terms: array of strings (optional) - Alternative names users might use
   - examples: array of strings (optional) - Example values or use cases
   - relationships: array of strings (optional) - Related tables or concepts
   - date_format: string (optional) - Date/time format if applicable
   - enum_values: array of strings (optional) - Valid enumeration values
   - sensitive: boolean (optional) - Whether data is sensitive (PII)

4. **list_annotations** - List existing annotations
   Parameters:
   - table_name: string (optional) - Filter by table name
   - column_name: string (optional) - Filter by column name

**How to use tools:**
When you want to use a tool, respond with JSON in this format:
```json
{
  "tool": "tool_name",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

**Your responsibilities:**
1. Engage in natural conversation to understand what the user needs
2. Proactively suggest examining data through sampling and statistics
3. Help users create comprehensive annotations by asking clarifying questions
4. Remember context from earlier in the conversation
5. Suggest business terms, identify sensitive data, and recommend relationships
6. Guide users through the annotation process step by step

**Best practices:**
- Be conversational and friendly
- Ask follow-up questions to clarify user intent
- Suggest next steps based on the conversation
- Remember what table or column is being discussed
- Offer to sample data before creating annotations
- Be concise but thorough in your responses"""

    def _get_system_prompt_with_context(self) -> str:
        """Get system prompt with current conversation context.

        Returns:
            System prompt with context information
        """
        base_prompt = self.get_system_prompt()

        if self.conversation_context:
            context_info = "\n\n**Current context:**\n"
            if "selected_table" in self.conversation_context:
                context_info += f"- Currently focused on table: {self.conversation_context['selected_table']}\n"
            base_prompt += context_info

        return base_prompt

    async def _sample_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Get random sample rows from a table.

        Parameters:
            - table_name: Name of the table
            - limit: Number of rows to return (default: 5, max: 50)
            - random: Whether to randomize (default: True)

        Returns:
            Sample rows and column information
        """
        if not self.provider:
            return {"error": "Provider not configured"}

        table_name = params.get("table_name")
        limit = min(params.get("limit", 5), 50)
        use_random = params.get("random", True)

        if not table_name:
            return {"error": "table_name is required"}

        try:
            # Build SELECT query - use TABLESAMPLE for PostgreSQL (fast random sampling)
            # Falls back to ORDER BY RANDOM() for other DBs
            if use_random:
                # Try PostgreSQL's efficient TABLESAMPLE first
                # BERNOULLI samples ~1% of rows randomly, then we LIMIT
                query = f"SELECT * FROM {table_name} TABLESAMPLE BERNOULLI(10) LIMIT {limit}"
            else:
                query = f"SELECT * FROM {table_name} LIMIT {limit}"

            # Execute query
            try:
                result = await self.provider.execute_query(query, limit=limit)
            except Exception:
                # TABLESAMPLE not supported, fall back to ORDER BY RANDOM()
                if use_random:
                    query = f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT {limit}"
                    result = await self.provider.execute_query(query, limit=limit)
                else:
                    raise

            if result and result.success:
                return {
                    "success": True,
                    "table_name": table_name,
                    "row_count": result.row_count,
                    "columns": result.columns or [],
                    "sample_rows": result.sample_rows or [],
                }
            else:
                return {
                    "success": False,
                    "error": result.error if result else "Query execution failed",
                }
        except Exception as e:
            logger.error(f"Failed to sample data: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to sample data: {str(e)}",
            }

    async def _column_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Get statistics about a column.

        Parameters:
            - table_name: Name of the table
            - column_name: Name of the column

        Returns:
            Column statistics (distinct count, null count, sample values)
        """
        if not self.provider:
            return {"error": "Provider not configured"}

        table_name = params.get("table_name")
        column_name = params.get("column_name")

        if not table_name or not column_name:
            return {"error": "table_name and column_name are required"}

        try:
            # Build query to get column statistics
            stats_query = f"""
            SELECT
                COUNT(*) as total_count,
                COUNT(DISTINCT {column_name}) as distinct_count,
                COUNT(*) - COUNT({column_name}) as null_count,
                COUNT({column_name}) * 100.0 / COUNT(*) as non_null_percentage
            FROM {table_name}
            """

            # Execute stats query
            stats_result = await self.provider.execute_query(stats_query, limit=1)

            if not stats_result or not stats_result.success:
                return {
                    "success": False,
                    "error": stats_result.error if stats_result else "Stats query failed",
                }

            stats = stats_result.sample_rows[0] if stats_result.sample_rows else {}

            # Get sample distinct values
            sample_query = f"""
            SELECT DISTINCT {column_name}
            FROM {table_name}
            WHERE {column_name} IS NOT NULL
            LIMIT 10
            """

            sample_result = await self.provider.execute_query(sample_query, limit=10)
            sample_values = []
            if sample_result and sample_result.success and sample_result.sample_rows:
                sample_values = [
                    row[0] if isinstance(row, (list, tuple)) else row.get(column_name)
                    for row in sample_result.sample_rows
                ]

            return {
                "success": True,
                "table_name": table_name,
                "column_name": column_name,
                "total_count": stats.get("total_count", 0),
                "distinct_count": stats.get("distinct_count", 0),
                "null_count": stats.get("null_count", 0),
                "non_null_percentage": float(stats.get("non_null_percentage", 0)),
                "sample_values": sample_values[:10],
            }
        except Exception as e:
            logger.error(f"Failed to get column statistics: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to get column statistics: {str(e)}",
            }

    async def _save_annotation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Save a schema annotation.

        Parameters:
            - provider_id: Provider ID (injected by process method)
            - user_id: User ID (injected by process method)
            - table_name: Table name (for table-level annotations)
            - column_name: Column name (for column-level annotations)
            - description: Description of the table/column
            - business_terms: Alternative names
            - examples: Example values or use cases
            - relationships: Related tables or concepts
            - date_format: Date format if applicable
            - enum_values: Valid enumeration values
            - sensitive: Whether data is sensitive

        Returns:
            Success status and annotation ID
        """
        provider_id = params.get("provider_id")
        user_id = params.get("user_id", "system")
        table_name = params.get("table_name")
        column_name = params.get("column_name")
        description = params.get("description")

        # Validation
        if not description:
            return {"error": "description is required"}

        if not table_name and not column_name:
            return {"error": "Either table_name or column_name must be provided"}

        if table_name and column_name:
            return {"error": "Cannot specify both table_name and column_name"}

        try:
            # Create annotation
            annotation = await self.annotation_repo.create(
                provider_id=provider_id,
                description=description,
                created_by=user_id,
                table_name=table_name,
                column_name=column_name,
                business_terms=params.get("business_terms"),
                examples=params.get("examples"),
                relationships=params.get("relationships"),
                date_format=params.get("date_format"),
                enum_values=params.get("enum_values"),
                sensitive=params.get("sensitive", False),
            )

            return {
                "success": True,
                "annotation_id": str(annotation.id),
                "target": annotation.target,
                "target_type": annotation.target_type,
                "message": f"Successfully saved {annotation.target_type} annotation for {annotation.target}",
            }
        except Exception as e:
            logger.error(f"Failed to save annotation: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to save annotation: {str(e)}",
            }

    async def _list_annotations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: List existing annotations.

        Parameters:
            - provider_id: Provider ID (injected by process method)
            - table_name: Filter by table name (optional)
            - column_name: Filter by column name (optional)

        Returns:
            List of annotations matching the criteria
        """
        provider_id = params.get("provider_id")
        table_name = params.get("table_name")
        column_name = params.get("column_name")

        if not provider_id:
            return {"error": "provider_id is required"}

        try:
            # Get annotations from repository
            annotations = await self.annotation_repo.get_by_provider(provider_id)

            # Filter by table or column if specified
            if table_name:
                annotations = [
                    ann for ann in annotations
                    if ann.table_name == table_name or
                       (ann.column_name and ann.column_name.startswith(f"{table_name}."))
                ]

            if column_name:
                annotations = [
                    ann for ann in annotations
                    if ann.column_name == column_name
                ]

            # Format annotations for response
            formatted_annotations = [
                {
                    "id": str(ann.id),
                    "target": ann.target,
                    "target_type": ann.target_type,
                    "description": ann.description,
                    "business_terms": ann.business_terms,
                    "examples": ann.examples,
                    "relationships": ann.relationships,
                    "date_format": ann.date_format,
                    "enum_values": ann.enum_values,
                    "sensitive": ann.sensitive,
                }
                for ann in annotations
            ]

            return {
                "success": True,
                "count": len(formatted_annotations),
                "annotations": formatted_annotations,
            }
        except Exception as e:
            logger.error(f"Failed to list annotations: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to list annotations: {str(e)}",
            }

    async def _get_table_annotation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Get annotation for a specific table (useful for FK context).

        Parameters:
            - provider_id: Provider ID (injected by process method)
            - table_name: Name of the table to get annotations for

        Returns:
            Table description and column annotations if available
        """
        provider_id = params.get("provider_id")
        table_name = params.get("table_name")

        if not provider_id:
            return {"error": "provider_id is required"}
        if not table_name:
            return {"error": "table_name is required"}

        try:
            # Get annotations from repository
            annotations = await self.annotation_repo.get_by_provider(provider_id)
            
            # Filter for this table
            table_annotations = [
                ann for ann in annotations
                if ann.table_name == table_name or ann.target == table_name
            ]
            
            if not table_annotations:
                return {
                    "success": True,
                    "table_name": table_name,
                    "exists": False,
                    "message": f"No annotations found for table '{table_name}'"
                }
            
            # Find table-level annotation
            table_desc = None
            column_annotations = []
            
            for ann in table_annotations:
                if ann.target_type == "table":
                    table_desc = ann.description
                elif ann.target_type == "column":
                    column_annotations.append({
                        "name": ann.column_name or ann.target.split(".")[-1],
                        "description": ann.description,
                        "sensitive": ann.sensitive,
                        "business_terms": ann.business_terms,
                    })
            
            return {
                "success": True,
                "table_name": table_name,
                "exists": True,
                "table_description": table_desc,
                "columns": column_annotations,
            }
        except Exception as e:
            logger.error(f"Failed to get table annotation: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to get annotation: {str(e)}",
            }
