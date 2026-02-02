"""Custom tools for Strands query generation agent.

These tools provide schema lookup and SQL validation capabilities
that the agent can use to generate accurate queries.
"""
import re
import sqlparse
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from strands import tool


# Global registry for schema providers (set by StrandsQueryAgent)
_schema_registry: Dict[str, Any] = {}


def register_schema_provider(provider_id: str, provider: Any) -> None:
    """Register a schema provider for tool access."""
    _schema_registry[provider_id] = provider


def get_registered_provider(provider_id: str) -> Optional[Any]:
    """Get a registered schema provider."""
    return _schema_registry.get(provider_id)


def clear_schema_registry() -> None:
    """Clear all registered schema providers."""
    _schema_registry.clear()


@tool
def get_schema_info(
    provider_id: str,
    table_names: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Get database schema information for query generation.
    
    Retrieves table structures, column definitions, and relationships
    from the specified provider. Use this to understand the database
    schema before generating SQL queries.
    
    Args:
        provider_id: The ID of the data provider to query schema from.
        table_names: Optional list of specific tables to get info for.
                    If None, returns all available tables.
    
    Returns:
        Dictionary containing:
        - tables: List of table definitions with columns
        - relationships: Foreign key relationships between tables
        - provider_type: Type of the provider (SQL, NoSQL, etc.)
    """
    provider = get_registered_provider(provider_id)
    
    if provider is None:
        return {
            "error": f"Provider '{provider_id}' not registered",
            "available_providers": list(_schema_registry.keys())
        }
    
    try:
        # Try to get schema synchronously (for tool use)
        # The provider may have a sync method or we need to run async
        import asyncio
        
        # Check if there's an event loop already running
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, we can't use run_until_complete
            # Return a placeholder - the agent should handle this
            return {
                "error": "Cannot get schema in async context synchronously",
                "hint": "Schema should be pre-fetched before agent invocation"
            }
        except RuntimeError:
            # No running loop, we can create one
            pass
        
        async def _get_schema():
            return await provider.get_schema()
        
        schema = asyncio.run(_get_schema())
        
        # Format schema for the agent
        result = {
            "tables": [],
            "relationships": [],
            "provider_type": provider.get_query_language() if hasattr(provider, 'get_query_language') else "unknown",
            "provider_id": provider_id
        }
        
        if hasattr(schema, 'tables') and schema.tables:
            for table in schema.tables:
                if table_names and hasattr(table, 'name') and table.name not in table_names:
                    continue
                    
                table_info = {
                    "name": table.name if hasattr(table, 'name') else str(table),
                    "columns": []
                }
                
                if hasattr(table, 'columns'):
                    for col in table.columns:
                        if isinstance(col, dict):
                            table_info["columns"].append({
                                "name": col.get('name', ''),
                                "type": col.get('type', ''),
                                "nullable": col.get('nullable', True),
                                "description": col.get('description')
                            })
                        elif hasattr(col, 'name'):
                            table_info["columns"].append({
                                "name": col.name,
                                "type": getattr(col, 'type', ''),
                                "nullable": getattr(col, 'nullable', True),
                                "description": getattr(col, 'description', None)
                            })
                
                if hasattr(table, 'description'):
                    table_info["description"] = table.description
                    
                result["tables"].append(table_info)
        
        return result
        
    except Exception as e:
        return {
            "error": f"Failed to get schema: {str(e)}",
            "provider_id": provider_id
        }


@tool
def validate_sql_syntax(
    sql_query: str,
    dialect: str = "generic"
) -> Dict[str, Any]:
    """Validate SQL query syntax and structure.
    
    Checks the SQL query for syntax errors, common issues, and
    provides feedback for improvement. Does NOT execute the query.
    
    Args:
        sql_query: The SQL query to validate.
        dialect: SQL dialect to validate against (generic, postgresql, mysql, etc.)
    
    Returns:
        Dictionary containing:
        - valid: Boolean indicating if query is syntactically valid
        - issues: List of any issues found
        - formatted_query: Properly formatted version of the query
        - suggestions: Suggestions for improvement
    """
    result = {
        "valid": True,
        "issues": [],
        "suggestions": [],
        "formatted_query": "",
        "statement_types": []
    }
    
    if not sql_query or not sql_query.strip():
        result["valid"] = False
        result["issues"].append("Empty query provided")
        return result
    
    try:
        # Parse and format the query
        parsed = sqlparse.parse(sql_query)
        
        if not parsed:
            result["valid"] = False
            result["issues"].append("Could not parse SQL query")
            return result
        
        # Format the query
        result["formatted_query"] = sqlparse.format(
            sql_query,
            reindent=True,
            keyword_case='upper',
            identifier_case='lower'
        )
        
        # Analyze each statement
        for statement in parsed:
            stmt_type = statement.get_type()
            result["statement_types"].append(stmt_type)
            
            # Check for common issues
            sql_upper = sql_query.upper()
            
            # SELECT * warning
            if "SELECT *" in sql_upper or "SELECT  *" in sql_upper:
                result["suggestions"].append(
                    "Consider specifying column names instead of SELECT * for better performance and clarity"
                )
            
            # Missing WHERE clause in UPDATE/DELETE
            if stmt_type in ('UPDATE', 'DELETE') and 'WHERE' not in sql_upper:
                result["issues"].append(
                    f"Warning: {stmt_type} statement without WHERE clause will affect all rows"
                )
            
            # Check for unbalanced parentheses
            open_parens = sql_query.count('(')
            close_parens = sql_query.count(')')
            if open_parens != close_parens:
                result["valid"] = False
                result["issues"].append(
                    f"Unbalanced parentheses: {open_parens} opening, {close_parens} closing"
                )
            
            # Check for unterminated strings
            single_quotes = sql_query.count("'") - sql_query.count("\\'") * 2
            if single_quotes % 2 != 0:
                result["valid"] = False
                result["issues"].append("Possible unterminated string literal (unbalanced single quotes)")
            
            # Check for obvious syntax patterns that indicate problems
            problematic_patterns = [
                (r'SELECT\s+FROM', "Missing columns between SELECT and FROM"),
                (r'FROM\s+WHERE', "Missing table name between FROM and WHERE"),
                (r'WHERE\s+AND', "Missing condition before AND"),
                (r'WHERE\s+OR', "Missing condition before OR"),
                (r',,', "Double comma detected"),
                (r'JOIN\s+ON\s+ON', "Duplicate ON keyword"),
            ]
            
            for pattern, message in problematic_patterns:
                if re.search(pattern, sql_upper):
                    result["valid"] = False
                    result["issues"].append(message)
        
        # Dialect-specific checks
        if dialect == "postgresql":
            # PostgreSQL specific validations
            if "LIMIT" in sql_upper and "OFFSET" in sql_upper:
                # Check LIMIT comes before OFFSET
                limit_pos = sql_upper.find("LIMIT")
                offset_pos = sql_upper.find("OFFSET")
                if offset_pos < limit_pos:
                    result["suggestions"].append(
                        "In PostgreSQL, LIMIT should come before OFFSET"
                    )
        
        return result
        
    except Exception as e:
        result["valid"] = False
        result["issues"].append(f"Parse error: {str(e)}")
        return result


@tool
def get_sample_data(
    provider_id: str,
    table_name: str,
    limit: int = 5
) -> Dict[str, Any]:
    """Get sample data from a table to understand its content.
    
    Retrieves a few sample rows from the specified table to help
    understand the data patterns and values. Useful for generating
    accurate WHERE clauses and understanding data types.
    
    Args:
        provider_id: The ID of the data provider.
        table_name: Name of the table to sample.
        limit: Maximum number of rows to return (default 5, max 10).
    
    Returns:
        Dictionary containing:
        - rows: Sample data rows
        - column_names: List of column names
        - row_count: Number of rows returned
    """
    provider = get_registered_provider(provider_id)
    
    if provider is None:
        return {
            "error": f"Provider '{provider_id}' not registered",
            "available_providers": list(_schema_registry.keys())
        }
    
    # Limit to max 10 rows for safety
    limit = min(limit, 10)
    
    try:
        import asyncio
        
        # Check for running event loop
        try:
            loop = asyncio.get_running_loop()
            return {
                "error": "Cannot execute query in async context synchronously",
                "hint": "Sample data should be pre-fetched if needed"
            }
        except RuntimeError:
            pass
        
        async def _get_sample():
            # Construct a simple SELECT query
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            return await provider.execute_query(query)
        
        result = asyncio.run(_get_sample())
        
        # Format the result
        if hasattr(result, 'rows'):
            return {
                "rows": result.rows[:limit] if result.rows else [],
                "column_names": result.columns if hasattr(result, 'columns') else [],
                "row_count": len(result.rows) if result.rows else 0,
                "table_name": table_name
            }
        else:
            return {
                "rows": [],
                "column_names": [],
                "row_count": 0,
                "table_name": table_name,
                "note": "Query executed but no structured result returned"
            }
            
    except Exception as e:
        return {
            "error": f"Failed to get sample data: {str(e)}",
            "table_name": table_name
        }
