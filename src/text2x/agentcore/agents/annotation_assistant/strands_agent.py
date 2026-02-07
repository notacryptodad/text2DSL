"""Annotation assistant agent - interactive helper for schema annotation tasks.

Refactored to use Strands SDK with LiteLLM for model calls.

This agent provides conversational assistance for annotating database schemas:
- sample_data: Get sample rows from a table to understand data patterns
- column_stats: Get statistics about column values (distinct count, nulls, etc.)
- save_annotation: Save schema annotations to the database
- list_annotations: List existing annotations for a table or column

Supports multi-turn chat with conversation memory for iterative exploration.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from strands import Agent
from strands.tools import tool

from text2x.providers.base import QueryProvider
from text2x.repositories.annotation import SchemaAnnotationRepository

logger = logging.getLogger(__name__)


# Tool context dataclass to share state between tools
@dataclass
class AssistantToolContext:
    """Context shared between annotation assistant tools."""

    provider: Optional[QueryProvider] = None
    annotation_repo: Optional[SchemaAnnotationRepository] = None
    provider_id: str = ""
    user_id: str = "system"
    selected_table: Optional[str] = None


# Global context
_assistant_context: Optional[AssistantToolContext] = None


def set_assistant_context(context: AssistantToolContext) -> None:
    """Set the global assistant tool context."""
    global _assistant_context
    _assistant_context = context


def get_assistant_context() -> AssistantToolContext:
    """Get the global assistant tool context."""
    if _assistant_context is None:
        raise RuntimeError("Assistant tool context not initialized")
    return _assistant_context


# Define tools as standalone functions with @tool decorator


@tool
def assistant_sample_data(table_name: str, limit: int = 10) -> dict:
    """Get sample rows from a table to understand data patterns.

    Args:
        table_name: Name of the table to sample
        limit: Number of rows to return (default: 10, max: 100)

    Returns:
        Dictionary with sample rows and column information
    """
    ctx = get_assistant_context()

    if not ctx.provider:
        return {"error": "Provider not configured"}

    if not table_name:
        return {"error": "table_name is required"}

    limit = min(limit, 100)

    try:
        import asyncio

        query = f"SELECT * FROM {table_name} LIMIT {limit}"

        try:
            result = asyncio.run(ctx.provider.execute_query(query, limit=limit))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(ctx.provider.execute_query(query, limit=limit))
            finally:
                loop.close()

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


@tool
def assistant_column_stats(table_name: str, column_name: str) -> dict:
    """Get statistics about a column including distinct count, nulls, and sample values.

    Args:
        table_name: Name of the table
        column_name: Name of the column

    Returns:
        Dictionary with column statistics
    """
    ctx = get_assistant_context()

    if not ctx.provider:
        return {"error": "Provider not configured"}

    if not table_name or not column_name:
        return {"error": "table_name and column_name are required"}

    try:
        import asyncio

        stats_query = f"""
        SELECT
            COUNT(*) as total_count,
            COUNT(DISTINCT {column_name}) as distinct_count,
            COUNT(*) - COUNT({column_name}) as null_count,
            COUNT({column_name}) * 100.0 / COUNT(*) as non_null_percentage
        FROM {table_name}
        """

        try:
            stats_result = asyncio.run(ctx.provider.execute_query(stats_query, limit=1))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                stats_result = loop.run_until_complete(
                    ctx.provider.execute_query(stats_query, limit=1)
                )
            finally:
                loop.close()

        if not stats_result or not stats_result.success:
            return {
                "success": False,
                "error": stats_result.error if stats_result else "Stats query failed",
            }

        stats = stats_result.sample_rows[0] if stats_result.sample_rows else {}

        sample_query = f"""
        SELECT DISTINCT {column_name}
        FROM {table_name}
        WHERE {column_name} IS NOT NULL
        LIMIT 10
        """

        try:
            sample_result = asyncio.run(ctx.provider.execute_query(sample_query, limit=10))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                sample_result = loop.run_until_complete(
                    ctx.provider.execute_query(sample_query, limit=10)
                )
            finally:
                loop.close()

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


@tool
def assistant_save_annotation(
    description: str,
    table_name: Optional[str] = None,
    column_name: Optional[str] = None,
    business_terms: Optional[list] = None,
    examples: Optional[list] = None,
    relationships: Optional[list] = None,
    date_format: Optional[str] = None,
    enum_values: Optional[list] = None,
    sensitive: bool = False,
) -> dict:
    """Save a schema annotation for a table or column.

    Args:
        description: Description of the table/column
        table_name: Table name (for table-level annotations)
        column_name: Column name (for column-level annotations, format: "table.column")
        business_terms: Alternative names users might use
        examples: Example values or use cases
        relationships: Related tables or concepts
        date_format: Date/time format if applicable
        enum_values: Valid enumeration values
        sensitive: Whether data is sensitive (PII)

    Returns:
        Dictionary with success status and annotation ID
    """
    ctx = get_assistant_context()

    if not description:
        return {"error": "description is required"}

    if not table_name and not column_name:
        return {"error": "Either table_name or column_name must be provided"}

    if table_name and column_name:
        return {"error": "Cannot specify both table_name and column_name"}

    try:
        import asyncio

        def save_annotation_sync():
            return asyncio.run(
                ctx.annotation_repo.create(
                    provider_id=ctx.provider_id,
                    description=description,
                    created_by=ctx.user_id,
                    table_name=table_name,
                    column_name=column_name,
                    business_terms=business_terms,
                    examples=examples,
                    relationships=relationships,
                    date_format=date_format,
                    enum_values=enum_values,
                    sensitive=sensitive,
                )
            )

        try:
            annotation = save_annotation_sync()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                annotation = loop.run_until_complete(
                    ctx.annotation_repo.create(
                        provider_id=ctx.provider_id,
                        description=description,
                        created_by=ctx.user_id,
                        table_name=table_name,
                        column_name=column_name,
                        business_terms=business_terms,
                        examples=examples,
                        relationships=relationships,
                        date_format=date_format,
                        enum_values=enum_values,
                        sensitive=sensitive,
                    )
                )
            finally:
                loop.close()

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


@tool
def list_annotations(
    table_name: Optional[str] = None,
    column_name: Optional[str] = None,
) -> dict:
    """List existing annotations for a table or column.

    Args:
        table_name: Filter by table name (optional)
        column_name: Filter by column name (optional)

    Returns:
        Dictionary with list of annotations
    """
    ctx = get_assistant_context()

    if not ctx.provider_id:
        return {"error": "provider_id is required"}

    try:
        import asyncio

        def get_annotations_sync():
            return asyncio.run(ctx.annotation_repo.get_by_provider(ctx.provider_id))

        try:
            annotations = get_annotations_sync()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                annotations = loop.run_until_complete(
                    ctx.annotation_repo.get_by_provider(ctx.provider_id)
                )
            finally:
                loop.close()

        # Filter by table or column if specified
        if table_name:
            annotations = [
                ann
                for ann in annotations
                if ann.table_name == table_name
                or (ann.column_name and ann.column_name.startswith(f"{table_name}."))
            ]

        if column_name:
            annotations = [ann for ann in annotations if ann.column_name == column_name]

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


# System prompt for the annotation assistant
ANNOTATION_ASSISTANT_SYSTEM_PROMPT = """You are a helpful database schema annotation assistant. Your role is to help users understand their database schemas and create meaningful annotations through interactive conversation.

You have access to the following tools:

1. **assistant_sample_data** - Get sample rows from a table
   - table_name (required): Name of the table
   - limit (optional, default=10): Number of rows to sample

2. **assistant_column_stats** - Get statistics about a column
   - table_name (required): Name of the table
   - column_name (required): Name of the column

3. **assistant_save_annotation** - Save a schema annotation
   - description (required): Description of the table/column
   - table_name (optional): For table-level annotations
   - column_name (optional): For column-level annotations
   - business_terms (optional): Alternative names users might use
   - examples (optional): Example values or use cases
   - relationships (optional): Related tables or concepts
   - date_format (optional): Date/time format if applicable
   - enum_values (optional): Valid enumeration values
   - sensitive (optional): Whether data is sensitive (PII)

4. **list_annotations** - List existing annotations
   - table_name (optional): Filter by table name
   - column_name (optional): Filter by column name

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


class AnnotationAssistantAgent:
    """Interactive annotation assistant using Strands SDK with LiteLLM.

    Provides conversational interface for schema exploration and annotation.
    """

    def __init__(
        self,
        model,
        provider: Optional[QueryProvider] = None,
        annotation_repo: Optional[SchemaAnnotationRepository] = None,
        name: str = "annotation_assistant",
    ):
        """Initialize annotation assistant agent.

        Args:
            model: Strands model provider (e.g., LiteLLMModel)
            provider: Query provider for database access
            annotation_repo: Repository for saving annotations
            name: Agent name
        """
        self.name = name
        self.provider = provider
        self.annotation_repo = annotation_repo or SchemaAnnotationRepository()
        self.conversation_context: Dict[str, Any] = {}

        # Create Strands Agent with tools
        self.agent = Agent(
            model=model,
            system_prompt=ANNOTATION_ASSISTANT_SYSTEM_PROMPT,
            tools=[
                assistant_sample_data,
                assistant_column_stats,
                assistant_save_annotation,
                list_annotations,
            ],
            name=name,
            description="Interactive annotation assistant for schema exploration",
        )

        logger.info(f"AnnotationAssistantAgent '{name}' initialized with Strands SDK")

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
        import time

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

        # Set up tool context
        ctx = AssistantToolContext(
            provider=self.provider,
            annotation_repo=self.annotation_repo,
            provider_id=provider_id,
            user_id=user_id,
            selected_table=self.conversation_context.get("selected_table"),
        )
        set_assistant_context(ctx)

        # Invoke the Strands agent
        result = self.agent(message)

        # Extract response and tool calls
        response_text = str(result)

        tool_calls = []
        if hasattr(result, "messages"):
            for msg in result.messages:
                if hasattr(msg, "tool_use"):
                    tool_calls.append(
                        {
                            "tool": msg.tool_use.name
                            if hasattr(msg.tool_use, "name")
                            else str(msg.tool_use),
                            "result": "executed",
                        }
                    )

        return {
            "response": response_text,
            "conversation_id": conversation_id,
            "tool_calls": tool_calls,
        }

    def get_system_prompt(self) -> str:
        """Get system prompt for annotation assistant."""
        return ANNOTATION_ASSISTANT_SYSTEM_PROMPT
