"""Helper functions to build rich context for annotation agent."""

import json
import logging
from typing import Any, Dict, Optional

from text2x.providers.base import QueryProvider
from text2x.repositories.annotation import SchemaAnnotationRepository

logger = logging.getLogger(__name__)


async def build_annotation_context(
    provider: QueryProvider,
    table_name: str,
    connection_id: str,
    annotation_repo: Optional[SchemaAnnotationRepository] = None,
) -> Dict[str, Any]:
    """Build comprehensive context for annotation agent.

    Fetches:
    - Table schema (columns, types, PKs)
    - Foreign key relationships (outgoing and incoming)
    - Sample data (5 random rows)
    - Row count estimate
    - Existing annotations (if any)

    Args:
        provider: Database query provider
        table_name: Name of table to annotate
        connection_id: Connection ID for annotation lookup
        annotation_repo: Repository for fetching existing annotations

    Returns:
        dict with: columns, foreign_keys_out, foreign_keys_in,
                   sample_data, row_estimate, existing_annotations
    """
    context = {
        "table_name": table_name,
        "columns": [],
        "foreign_keys_out": [],
        "foreign_keys_in": [],
        "sample_data": {},
        "row_estimate": None,
        "existing_annotations": None,
    }

    # 1. Get table schema
    try:
        schema = await provider.get_schema()
        logger.info(f"Schema for connection {connection_id}: {len(schema.tables)} tables found")
        for table in schema.tables:
            logger.info(f"  Table: {table.name}, columns: {len(table.columns)}")

        for table in schema.tables:
            if table.name == table_name:
                logger.info(f"Found table {table_name} with {len(table.columns)} columns")
                context["columns"] = [
                    {
                        "name": col.name,
                        "type": str(col.type),
                        "nullable": col.nullable,
                        "is_pk": col.primary_key,
                        "default": str(col.default) if col.default else None,
                    }
                    for col in table.columns
                ]
                # ForeignKeyInfo is a dataclass with: constrained_columns, referred_table, referred_columns
                context["foreign_keys_out"] = [
                    {
                        "column": fk.constrained_columns[0] if fk.constrained_columns else None,
                        "references_table": fk.referred_table,
                        "references_column": fk.referred_columns[0]
                        if hasattr(fk, "referred_columns") and fk.referred_columns
                        else None,
                    }
                    for fk in (table.foreign_keys or [])
                ]
                break

        # Find incoming FKs (tables that reference this one)
        for table in schema.tables:
            if table.name != table_name:
                for fk in table.foreign_keys or []:
                    if fk.referred_table == table_name:
                        context["foreign_keys_in"].append(
                            {
                                "from_table": table.name,
                                "from_column": fk.constrained_columns[0]
                                if fk.constrained_columns
                                else None,
                                "to_column": fk.referred_columns[0]
                                if hasattr(fk, "referred_columns") and fk.referred_columns
                                else None,
                            }
                        )
    except Exception as e:
        logger.warning(f"Failed to get schema: {e}")
        context["schema_error"] = str(e)

    # 2. Get sample data (random 5 rows)
    try:
        # Use simple LIMIT query first - TABLESAMPLE can be unreliable on small tables
        query = f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT 5"
        result = await provider.execute_query(query, limit=5)
        logger.info(
            f"Sample query result for {table_name}: success={result.success if result else 'None'}, cols={result.columns if result else 'None'}, rows={len(result.sample_rows) if result and result.sample_rows else 0}"
        )
        if result and result.success:
            context["sample_data"] = {
                "columns": result.columns or [],
                "rows": result.sample_rows or [],
            }
    except Exception as e:
        logger.warning(f"Sample query failed: {e}")
        context["sample_error"] = str(e)

    # 3. Get row count estimate (PostgreSQL-specific)
    try:
        query = f"SELECT reltuples::bigint FROM pg_class WHERE relname = '{table_name}'"
        result = await provider.execute_query(query, limit=1)
        if result and result.success and result.sample_rows:
            context["row_estimate"] = result.sample_rows[0][0]
    except Exception:
        pass  # Not critical

    # 4. Get existing annotations
    if annotation_repo:
        try:
            existing = await annotation_repo.get_by_table(connection_id, table_name)
            if existing:
                context["existing_annotations"] = {
                    "table_description": existing.description,
                    "columns": [
                        {"name": c.name, "description": c.description}
                        for c in (existing.columns or [])
                    ],
                }
        except Exception as e:
            logger.debug(f"No existing annotations: {e}")

    return context


def format_context_as_prompt(context: Dict[str, Any]) -> str:
    """Format context dictionary into a human-readable prompt string.

    Args:
        context: Context dict from build_annotation_context()

    Returns:
        Formatted string for LLM prompt
    """
    lines = []
    lines.append(f"## Table: {context['table_name']}")

    row_est = context.get("row_estimate")
    if row_est:
        lines.append(f"Estimated rows: ~{row_est:,}")
    lines.append("")

    # Columns with types
    lines.append("## Schema")
    for col in context.get("columns", []):
        pk = " [PK]" if col.get("is_pk") else ""
        nullable = "" if col.get("nullable") else " NOT NULL"
        default = f" DEFAULT {col['default']}" if col.get("default") else ""
        lines.append(f"  • {col['name']}: {col['type']}{pk}{nullable}{default}")
    lines.append("")

    # Foreign Keys
    fk_out = context.get("foreign_keys_out", [])
    fk_in = context.get("foreign_keys_in", [])

    if fk_out or fk_in:
        lines.append("## Relationships")
        for fk in fk_out:
            lines.append(
                f"  → {context['table_name']}.{fk['column']} references {fk['references_table']}.{fk['references_column']}"
            )
        for fk in fk_in:
            lines.append(
                f"  ← {fk['from_table']}.{fk['from_column']} references {context['table_name']}.{fk['to_column']}"
            )
        lines.append("")

    # Sample Data
    sample = context.get("sample_data", {})
    if sample.get("rows"):
        lines.append("## Sample Data (5 random rows)")
        cols = sample.get("columns", [])

        # Format as simple table
        lines.append(f"Columns: {', '.join(cols)}")
        lines.append("")
        for i, row in enumerate(sample.get("rows", [])[:5], 1):
            row_str = ", ".join(
                f"{cols[j]}={str(v)[:50]}" for j, v in enumerate(row) if j < len(cols)
            )
            lines.append(f"  Row {i}: {row_str}")
        lines.append("")

    # Existing Annotations
    existing = context.get("existing_annotations")
    if existing:
        lines.append("## Existing Annotations (previous version)")
        lines.append(f"Table description: {existing.get('table_description', 'None')}")
        for col in existing.get("columns", []):
            lines.append(f"  • {col['name']}: {col['description']}")
        lines.append("")
    else:
        lines.append("## Existing Annotations: None")
        lines.append("")

    return "\n".join(lines)


async def get_related_table_annotation(
    connection_id: str, table_name: str, annotation_repo: SchemaAnnotationRepository
) -> Optional[Dict[str, Any]]:
    """Get annotation for a related table (for FK context).

    Args:
        connection_id: Connection ID
        table_name: Name of related table
        annotation_repo: Annotation repository

    Returns:
        Dict with table description and column annotations, or None
    """
    try:
        existing = await annotation_repo.get_by_table(connection_id, table_name)
        if existing:
            return {
                "table_name": table_name,
                "table_description": existing.description,
                "columns": [
                    {"name": c.name, "description": c.description} for c in (existing.columns or [])
                ],
            }
    except Exception:
        pass
    return None
