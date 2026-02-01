"""Annotation Agent - assists experts in annotating database schemas.

This agent provides tools to help experts understand and annotate database schemas:
- sample_data: Get sample rows from a table to understand data patterns
- column_stats: Get statistics about column values (distinct count, nulls, etc.)
- save_annotation: Save schema annotations to the database

Supports multi-turn chat for interactive schema exploration and annotation.
"""
import json
import time
from typing import Dict, Any, List, Optional, Callable
from text2x.agents.base import BaseAgent, LLMConfig, LLMMessage
from text2x.providers.base import QueryProvider
from text2x.repositories.annotation import SchemaAnnotationRepository


class AnnotationAgent(BaseAgent):
    """
    Annotation Agent

    Responsibilities:
    - Help experts understand database schema through data sampling and statistics
    - Guide experts in creating meaningful annotations
    - Save annotations to the database
    - Support multi-turn conversations for iterative schema exploration
    """

    def __init__(
        self,
        llm_config: LLMConfig,
        provider: QueryProvider,
        annotation_repo: Optional[SchemaAnnotationRepository] = None
    ):
        super().__init__(llm_config, agent_name="AnnotationAgent")
        self.provider = provider
        self.annotation_repo = annotation_repo or SchemaAnnotationRepository()

        # Conversation history for multi-turn chat
        self.conversation_history: List[Dict[str, str]] = []

        # Available tools
        self.tools = {
            "sample_data": self._sample_data,
            "column_stats": self._column_stats,
            "save_annotation": self._save_annotation,
        }

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user input and return response.

        Input:
            - user_message: str - User's message/question
            - provider_id: str - Provider ID for context
            - user_id: str - User ID for saving annotations
            - reset_conversation: bool - Reset conversation history

        Output:
            - response: str - Agent's response
            - tool_calls: List[Dict] - Tool calls made (if any)
            - conversation_history: List[Dict] - Full conversation history
        """
        start_time = time.time()

        user_message = input_data["user_message"]
        provider_id = input_data.get("provider_id", "")
        user_id = input_data.get("user_id", "system")
        reset_conversation = input_data.get("reset_conversation", False)

        # Reset conversation if requested
        if reset_conversation:
            self.conversation_history = []

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Build messages for LLM with system prompt and conversation history
        messages = [
            LLMMessage(role="system", content=self._build_annotation_system_prompt()),
        ]

        # Add conversation history
        for msg in self.conversation_history:
            messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

        # Call LLM
        response = await self.invoke_llm(messages, temperature=0.3)

        # Parse response for tool calls
        tool_calls = []
        assistant_response = response.content

        # Check if LLM wants to use tools
        # LLM should respond with JSON if it wants to use tools
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

                        # Add provider_id and user_id to tool params
                        tool_params["provider_id"] = provider_id
                        tool_params["user_id"] = user_id

                        # Execute tool
                        tool_result = await self.tools[tool_name](tool_params)
                        tool_calls.append({
                            "tool": tool_name,
                            "parameters": tool_params,
                            "result": tool_result
                        })
                        tool_use_detected = True

                        # Get follow-up response from LLM with tool result
                        tool_result_message = f"\n\nTool '{tool_name}' executed successfully. Result:\n{json.dumps(tool_result, indent=2)}\n\nPlease provide a summary and next steps for the user."
                        messages.append(LLMMessage(role="assistant", content=assistant_response))
                        messages.append(LLMMessage(role="user", content=tool_result_message))

                        follow_up_response = await self.invoke_llm(messages, temperature=0.3)
                        assistant_response = follow_up_response.content
            except (json.JSONDecodeError, KeyError, IndexError):
                # Not a tool call, just a regular response
                pass

        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_response
        })

        duration_ms = (time.time() - start_time) * 1000
        self.add_trace(
            step="process_annotation_request",
            input_data={"user_message": user_message, "provider_id": provider_id},
            output_data={
                "tool_calls_count": len(tool_calls),
                "conversation_turns": len(self.conversation_history)
            },
            duration_ms=duration_ms
        )

        return {
            "response": assistant_response,
            "tool_calls": tool_calls,
            "conversation_history": self.conversation_history
        }

    def _build_annotation_system_prompt(self) -> str:
        """Build system prompt for annotation agent."""
        return """You are an expert database schema annotation assistant. Your role is to help database experts and domain experts create meaningful annotations for database schemas.

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
1. Help users understand database tables and columns by sampling data and showing statistics
2. Guide users in creating comprehensive, accurate annotations
3. Suggest business terms based on data patterns
4. Identify potentially sensitive data and recommend marking it as sensitive
5. Suggest relationships between tables based on column names and data patterns
6. Support iterative exploration - users can ask follow-up questions

**Best practices:**
- Always sample data before creating annotations to understand the content
- Look for patterns in data to suggest business terms
- Check for null values and data quality issues
- Identify date formats, enumerations, and other special data types
- Ask clarifying questions if the user's intent is unclear
- Be concise but informative in your responses

Start by greeting the user and asking how you can help them annotate their schema."""

    async def _sample_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: Get sample rows from a table.

        Parameters:
            - table_name: Name of the table
            - limit: Number of rows to return (default: 10, max: 100)

        Returns:
            Sample rows and column information
        """
        table_name = params.get("table_name")
        limit = min(params.get("limit", 10), 100)

        if not table_name:
            return {"error": "table_name is required"}

        try:
            # Build SELECT query with limit
            query = f"SELECT * FROM {table_name} LIMIT {limit}"

            # Execute query
            result = await self.provider.execute_query(query, limit=limit)

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
                    "error": result.error if result else "Query execution failed"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to sample data: {str(e)}"
            }

    async def _column_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: Get statistics about a column.

        Parameters:
            - table_name: Name of the table
            - column_name: Name of the column

        Returns:
            Column statistics (distinct count, null count, sample values)
        """
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
                    "error": stats_result.error if stats_result else "Stats query failed"
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
                sample_values = [row[0] if isinstance(row, (list, tuple)) else row.get(column_name)
                               for row in sample_result.sample_rows]

            return {
                "success": True,
                "table_name": table_name,
                "column_name": column_name,
                "total_count": stats.get("total_count", 0),
                "distinct_count": stats.get("distinct_count", 0),
                "null_count": stats.get("null_count", 0),
                "non_null_percentage": float(stats.get("non_null_percentage", 0)),
                "sample_values": sample_values[:10]
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get column statistics: {str(e)}"
            }

    async def _save_annotation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: Save a schema annotation.

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
                sensitive=params.get("sensitive", False)
            )

            return {
                "success": True,
                "annotation_id": str(annotation.id),
                "target": annotation.target,
                "target_type": annotation.target_type,
                "message": f"Successfully saved {annotation.target_type} annotation for {annotation.target}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to save annotation: {str(e)}"
            }

    def reset_conversation(self) -> None:
        """Reset conversation history."""
        self.conversation_history = []

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get current conversation history."""
        return self.conversation_history
