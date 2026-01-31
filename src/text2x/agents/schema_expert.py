"""Schema Expert Agent - retrieves and enriches schema context"""
import time
from typing import Dict, Any, List, Optional
from text2x.agents.base import BaseAgent, LLMConfig, LLMMessage
from text2x.models import SchemaContext, TableInfo, Relationship, JoinPath, ColumnInfo
from text2x.providers.base import QueryProvider


class SchemaExpertAgent(BaseAgent):
    """
    Schema Expert Agent
    
    Responsibilities:
    - Retrieve relevant schema information from provider
    - Map natural language terms to schema elements
    - Identify relevant tables and relationships
    - Enrich context with annotations
    """
    
    def __init__(self, llm_config: LLMConfig, provider: QueryProvider):
        super().__init__(llm_config, agent_name="SchemaExpertAgent")
        self.provider = provider
        self.schema_cache: Optional[Any] = None
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user query and return schema context
        
        Input:
            - user_query: str
            - annotations: Dict[str, str] (optional)
        
        Output:
            - schema_context: SchemaContext
        """
        start_time = time.time()
        user_query = input_data["user_query"]
        annotations = input_data.get("annotations", {})
        
        # Step 1: Get full schema (cached or retrieved)
        schema_def = await self._get_or_cache_schema()
        
        # Step 2: Identify relevant tables using LLM
        relevant_tables = await self._identify_relevant_tables(user_query, schema_def)
        
        # Step 3: Extract relationships between identified tables
        relationships = self._extract_relationships(relevant_tables, schema_def)
        
        # Step 4: Suggest join paths
        suggested_joins = await self._suggest_joins(relevant_tables, relationships, user_query)
        
        # Step 5: Build schema context
        schema_context = SchemaContext(
            relevant_tables=relevant_tables,
            relationships=relationships,
            annotations=annotations,
            suggested_joins=suggested_joins,
            provider_id=self.provider.get_provider_id(),
            query_language=self.provider.get_query_language()
        )
        
        duration_ms = (time.time() - start_time) * 1000
        self.add_trace(
            step="retrieve_schema_context",
            input_data={"user_query": user_query},
            output_data={
                "tables_found": len(relevant_tables),
                "relationships": len(relationships),
                "joins": len(suggested_joins)
            },
            duration_ms=duration_ms
        )
        
        return {"schema_context": schema_context}
    
    async def _get_or_cache_schema(self) -> Any:
        """Get schema from cache or provider"""
        if self.schema_cache is None:
            self.schema_cache = await self.provider.get_schema()
        return self.schema_cache
    
    async def _identify_relevant_tables(
        self,
        user_query: str,
        schema_def: Any
    ) -> List[TableInfo]:
        """Use LLM to identify relevant tables from schema"""
        # Convert schema to readable format
        schema_str = self._format_schema_for_llm(schema_def)
        
        messages = [
            LLMMessage(role="system", content=self.build_system_prompt()),
            LLMMessage(
                role="user",
                content=f"""Given the following database schema and user query, identify the relevant tables needed to answer the query.

Schema:
{schema_str}

User Query: {user_query}

Return ONLY a JSON array of table names that are relevant. Consider:
1. Tables directly mentioned or implied in the query
2. Tables needed for joins to connect relevant data
3. Tables containing fields referenced in the query

Format: ["table1", "table2", ...]"""
            )
        ]
        
        response = await self.invoke_llm(messages, temperature=0.0)
        
        # Parse table names from response
        import json
        try:
            # Try to extract JSON array from response
            content = response.content.strip()
            if not content.startswith("["):
                # Try to find JSON array in the text
                start = content.find("[")
                end = content.rfind("]") + 1
                if start >= 0 and end > start:
                    content = content[start:end]
            
            table_names = json.loads(content)
        except:
            # Fallback: extract table names manually
            table_names = []
            if hasattr(schema_def, 'tables') and schema_def.tables:
                for table in schema_def.tables:
                    if hasattr(table, 'name') and table.name.lower() in response.content.lower():
                        table_names.append(table.name)
        
        # Get full table info for identified tables
        relevant_tables = []
        if hasattr(schema_def, 'tables') and schema_def.tables:
            for table in schema_def.tables:
                if hasattr(table, 'name') and table.name in table_names:
                    # Convert to our TableInfo format
                    columns = []
                    if hasattr(table, 'columns'):
                        for col in table.columns:
                            if isinstance(col, dict):
                                columns.append(ColumnInfo(
                                    name=col.get('name', ''),
                                    type=col.get('type', ''),
                                    nullable=col.get('nullable', True),
                                    description=col.get('description')
                                ))
                            else:
                                columns.append(col)
                    
                    relevant_tables.append(TableInfo(
                        name=table.name if hasattr(table, 'name') else str(table),
                        columns=columns,
                        description=getattr(table, 'description', None)
                    ))
        
        return relevant_tables
    
    def _format_schema_for_llm(self, schema_def: Any) -> str:
        """Format schema definition for LLM consumption"""
        lines = []
        
        if hasattr(schema_def, 'tables') and schema_def.tables:
            for table in schema_def.tables:
                table_name = table.name if hasattr(table, 'name') else str(table)
                lines.append(f"\nTable: {table_name}")
                
                if hasattr(table, 'columns') and table.columns:
                    for col in table.columns:
                        if isinstance(col, dict):
                            col_name = col.get('name', '')
                            col_type = col.get('type', '')
                            lines.append(f"  - {col_name} ({col_type})")
                        elif hasattr(col, 'name'):
                            col_type = getattr(col, 'type', '')
                            lines.append(f"  - {col.name} ({col_type})")
        
        return "\n".join(lines) if lines else "No schema information available"
    
    def _extract_relationships(
        self,
        relevant_tables: List[TableInfo],
        schema_def: Any
    ) -> List[Relationship]:
        """Extract relationships between relevant tables"""
        relationships = []
        table_names = {t.name for t in relevant_tables}
        
        # This is a simplified implementation
        # In a real system, we'd parse foreign key constraints from schema_def
        # For now, return empty list - can be enhanced based on provider capabilities
        
        return relationships
    
    async def _suggest_joins(
        self,
        relevant_tables: List[TableInfo],
        relationships: List[Relationship],
        user_query: str
    ) -> List[JoinPath]:
        """Suggest join paths using LLM"""
        if len(relevant_tables) <= 1:
            return []
        
        table_names = [t.name for t in relevant_tables]
        
        messages = [
            LLMMessage(role="system", content=self.build_system_prompt()),
            LLMMessage(
                role="user",
                content=f"""Given these tables: {', '.join(table_names)}

For the query: "{user_query}"

Suggest the most likely join relationships. Return a JSON array of objects with:
{{"from_table": "table1", "from_column": "id", "to_table": "table2", "to_column": "table1_id"}}

If you're not confident about specific column names, make reasonable assumptions based on common naming conventions (e.g., table_id, id).
Return ONLY the JSON array, no other text."""
            )
        ]
        
        response = await self.invoke_llm(messages, temperature=0.0)
        
        # Parse suggested joins
        import json
        suggested_joins = []
        
        try:
            content = response.content.strip()
            if not content.startswith("["):
                start = content.find("[")
                end = content.rfind("]") + 1
                if start >= 0 and end > start:
                    content = content[start:end]
            
            joins_data = json.loads(content)
            
            for join_data in joins_data:
                rel = Relationship(
                    from_table=join_data["from_table"],
                    from_column=join_data["from_column"],
                    to_table=join_data["to_table"],
                    to_column=join_data["to_column"]
                )
                
                join_path = JoinPath(
                    tables=[rel.from_table, rel.to_table],
                    relationships=[rel],
                    suggested_join_clause=f"{rel.from_table}.{rel.from_column} = {rel.to_table}.{rel.to_column}"
                )
                suggested_joins.append(join_path)
        except:
            pass  # Return empty list if parsing fails
        
        return suggested_joins
