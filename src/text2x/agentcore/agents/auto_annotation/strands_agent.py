"""Auto-annotation agent - assists experts in annotating database schemas.

Refactored to use Strands SDK with LiteLLM for model calls.

This agent provides tools to help experts understand and annotate database schemas:
- sample_data: Get sample rows from a table to understand data patterns
- column_stats: Get statistics about column values (distinct count, nulls, etc.)
- save_annotation: Save schema annotations to the database

Supports multi-turn chat for interactive schema exploration and annotation.
"""
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from strands import Agent
from strands.tools import tool

from text2x.providers.base import QueryProvider
from text2x.repositories.annotation import SchemaAnnotationRepository

logger = logging.getLogger(__name__)


# Tool context dataclass to share state between tools
@dataclass
class AnnotationToolContext:
    """Context shared between annotation tools."""
    provider: Optional[QueryProvider] = None
    annotation_repo: Optional[SchemaAnnotationRepository] = None
    provider_id: str = ""
    user_id: str = "system"


# Global context (will be set by the agent wrapper)
_tool_context: Optional[AnnotationToolContext] = None


def set_tool_context(context: AnnotationToolContext) -> None:
    """Set the global tool context."""
    global _tool_context
    _tool_context = context


def get_tool_context() -> AnnotationToolContext:
    """Get the global tool context."""
    if _tool_context is None:
        raise RuntimeError("Tool context not initialized")
    return _tool_context


# Define tools as standalone functions with @tool decorator

@tool
def sample_data(table_name: str, limit: int = 10) -> dict:
    """Get sample rows from a table to understand data patterns.

    Args:
        table_name: Name of the table to sample
        limit: Number of rows to return (default: 10, max: 100)

    Returns:
        Dictionary with sample rows and column information
    """
    ctx = get_tool_context()

    if not ctx.provider:
        return {"error": "Provider not configured"}

    if not table_name:
        return {"error": "table_name is required"}

    limit = min(limit, 100)

    try:
        import asyncio
        # Build SELECT query with limit
        query = f"SELECT * FROM {table_name} LIMIT {limit}"

        # Execute query (synchronously wrapping async)
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run,
                    ctx.provider.execute_query(query, limit=limit)
                ).result()
        else:
            result = asyncio.run(ctx.provider.execute_query(query, limit=limit))

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
def column_stats(table_name: str, column_name: str) -> dict:
    """Get statistics about a column including distinct count, nulls, and sample values.

    Args:
        table_name: Name of the table
        column_name: Name of the column

    Returns:
        Dictionary with column statistics
    """
    ctx = get_tool_context()

    if not ctx.provider:
        return {"error": "Provider not configured"}

    if not table_name or not column_name:
        return {"error": "table_name and column_name are required"}

    try:
        import asyncio

        # Build query to get column statistics
        stats_query = f"""
        SELECT
            COUNT(*) as total_count,
            COUNT(DISTINCT {column_name}) as distinct_count,
            COUNT(*) - COUNT({column_name}) as null_count,
            COUNT({column_name}) * 100.0 / COUNT(*) as non_null_percentage
        FROM {table_name}
        """

        # Execute synchronously
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                stats_result = pool.submit(
                    asyncio.run,
                    ctx.provider.execute_query(stats_query, limit=1)
                ).result()
        else:
            stats_result = asyncio.run(ctx.provider.execute_query(stats_query, limit=1))

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

        if asyncio.get_event_loop().is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                sample_result = pool.submit(
                    asyncio.run,
                    ctx.provider.execute_query(sample_query, limit=10)
                ).result()
        else:
            sample_result = asyncio.run(ctx.provider.execute_query(sample_query, limit=10))

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
def save_annotation(
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
    ctx = get_tool_context()

    # Validation
    if not description:
        return {"error": "description is required"}

    if not table_name and not column_name:
        return {"error": "Either table_name or column_name must be provided"}

    if table_name and column_name:
        return {"error": "Cannot specify both table_name and column_name"}

    try:
        import asyncio

        # Create annotation
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                annotation = pool.submit(
                    asyncio.run,
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
                ).result()
        else:
            annotation = asyncio.run(ctx.annotation_repo.create(
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
            ))

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


# System prompt for the annotation agent
AUTO_ANNOTATION_SYSTEM_PROMPT = """You are an expert database schema annotation assistant. Your role is to help database experts and domain experts create meaningful annotations for database schemas.

You have access to the following tools:

1. **sample_data** - Get sample rows from a table
   - table_name (required): Name of the table
   - limit (optional, default=10): Number of rows to sample

2. **column_stats** - Get statistics about a column
   - table_name (required): Name of the table
   - column_name (required): Name of the column

3. **save_annotation** - Save a schema annotation
   - description (required): Description of the table/column
   - table_name (optional): For table-level annotations
   - column_name (optional): For column-level annotations (format: "table.column")
   - business_terms (optional): Alternative names users might use
   - examples (optional): Example values or use cases
   - relationships (optional): Related tables or concepts
   - date_format (optional): Date/time format if applicable
   - enum_values (optional): Valid enumeration values
   - sensitive (optional): Whether data is sensitive (PII)

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


class AutoAnnotationAgent:
    """Auto-annotation agent using Strands SDK with LiteLLM.

    This agent helps experts understand database schema through data sampling and statistics,
    guides them in creating meaningful annotations, and saves annotations to the database.
    """

    def __init__(
        self,
        model,
        provider: Optional[QueryProvider] = None,
        annotation_repo: Optional[SchemaAnnotationRepository] = None,
        name: str = "auto_annotation",
    ):
        """Initialize auto-annotation agent.

        Args:
            model: Strands model provider (e.g., LiteLLMModel)
            provider: Query provider for database access
            annotation_repo: Repository for saving annotations
            name: Agent name
        """
        self.name = name
        self.provider = provider
        self.annotation_repo = annotation_repo or SchemaAnnotationRepository()

        # Create Strands Agent with tools
        self.agent = Agent(
            model=model,
            system_prompt=AUTO_ANNOTATION_SYSTEM_PROMPT,
            tools=[sample_data, column_stats, save_annotation],
            name=name,
            description="Auto-annotation agent for schema understanding and annotation",
        )

        logger.info(f"AutoAnnotationAgent '{name}' initialized with Strands SDK")

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
            - user_message: str - User's message/question
            - provider_id: str - Provider ID for context
            - user_id: str - User ID for saving annotations
            - reset_conversation: bool - Reset conversation history

        Output:
            - response: str - Agent's response
            - tool_calls: List[Dict] - Tool calls made (if any)
        """
        user_message = input_data["user_message"]
        provider_id = input_data.get("provider_id", "")
        user_id = input_data.get("user_id", "system")
        reset_conversation = input_data.get("reset_conversation", False)

        # Set up tool context
        context = AnnotationToolContext(
            provider=self.provider,
            annotation_repo=self.annotation_repo,
            provider_id=provider_id,
            user_id=user_id,
        )
        set_tool_context(context)

        # Reset conversation if requested
        if reset_conversation:
            # Create a new agent instance to reset conversation
            self.agent = Agent(
                model=self.agent.model,
                system_prompt=AUTO_ANNOTATION_SYSTEM_PROMPT,
                tools=[sample_data, column_stats, save_annotation],
                name=self.name,
                description="Auto-annotation agent for schema understanding and annotation",
            )

        # Invoke the Strands agent
        result = self.agent(user_message)

        # Extract response and tool calls
        response_text = str(result)

        # Get tool calls from agent messages if available
        tool_calls = []
        if hasattr(result, 'messages'):
            for msg in result.messages:
                if hasattr(msg, 'tool_use'):
                    tool_calls.append({
                        "tool": msg.tool_use.name if hasattr(msg.tool_use, 'name') else str(msg.tool_use),
                        "result": "executed",
                    })

        return {
            "response": response_text,
            "tool_calls": tool_calls,
        }

    def get_system_prompt(self) -> str:
        """Get system prompt for annotation agent."""
        return AUTO_ANNOTATION_SYSTEM_PROMPT
