"""SQL Provider Implementation for Text2X"""
import asyncio
import time
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

import sqlparse
from sqlalchemy import create_engine, inspect, text, pool, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, TimeoutError as SQLTimeoutError

from .base import (
    QueryProvider,
    ProviderCapability,
    SchemaDefinition,
    ValidationResult,
    ExecutionResult,
    TableInfo,
    ColumnInfo,
    IndexInfo,
    ForeignKeyInfo,
    Relationship,
    ProviderConfig,
)


@dataclass
class SQLConnectionConfig:
    """Configuration for SQL database connection"""
    host: str
    port: int
    database: str
    username: str
    password: str
    dialect: str = "postgresql"  # postgresql, mysql, sqlite, etc.
    driver: Optional[str] = None  # psycopg2, asyncpg, pymysql, etc.
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def get_connection_string(self) -> str:
        """Build SQLAlchemy connection string"""
        driver_suffix = f"+{self.driver}" if self.driver else ""
        base = f"{self.dialect}{driver_suffix}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        
        if self.extra_params:
            params = "&".join(f"{k}={v}" for k, v in self.extra_params.items())
            base += f"?{params}"
        
        return base


class SQLProvider(QueryProvider):
    """SQL Provider for PostgreSQL, MySQL, and other SQL databases"""
    
    def __init__(self, config: SQLConnectionConfig, provider_config: Optional[ProviderConfig] = None):
        """
        Initialize SQL Provider
        
        Args:
            config: SQL connection configuration
            provider_config: General provider configuration
        """
        self.config = config
        self.provider_config = provider_config or ProviderConfig(provider_type="sql")
        
        # Create engine with connection pooling
        self.engine = create_engine(
            config.get_connection_string(),
            poolclass=pool.QueuePool,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            echo=config.echo,
            # Set statement timeout at connection level
            connect_args={
                "connect_timeout": self.provider_config.timeout_seconds,
            }
        )
        
        # Set statement timeout for PostgreSQL
        if config.dialect == "postgresql":
            @event.listens_for(self.engine, "connect")
            def set_timeout(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute(f"SET statement_timeout = {self.provider_config.timeout_seconds * 1000}")
                cursor.close()
        
        self._inspector = None
    
    def get_provider_id(self) -> str:
        """Unique identifier for this provider"""
        return f"sql_{self.config.dialect}"
    
    def get_query_language(self) -> str:
        """Query language supported by this provider"""
        return "SQL"
    
    def get_capabilities(self) -> List[ProviderCapability]:
        """List of capabilities this provider supports"""
        return [
            ProviderCapability.SCHEMA_INTROSPECTION,
            ProviderCapability.QUERY_VALIDATION,
            ProviderCapability.QUERY_EXECUTION,
            ProviderCapability.QUERY_EXPLANATION,
        ]
    
    async def get_schema(self) -> SchemaDefinition:
        """
        Retrieve the complete database schema
        
        Returns:
            SchemaDefinition with tables, columns, indexes, and relationships
        """
        # Use asyncio.to_thread to run blocking SQLAlchemy code in thread pool
        return await asyncio.to_thread(self._get_schema_sync)
    
    def _get_schema_sync(self) -> SchemaDefinition:
        """Synchronous schema introspection"""
        inspector = inspect(self.engine)
        tables = []
        relationships = []
        
        # Get all table names
        table_names = inspector.get_table_names()
        
        for table_name in table_names:
            # Get columns
            columns = []
            pk_columns = inspector.get_pk_constraint(table_name).get("constrained_columns", [])
            
            for col in inspector.get_columns(table_name):
                col_info = ColumnInfo(
                    name=col["name"],
                    type=str(col["type"]),
                    nullable=col.get("nullable", True),
                    default=str(col.get("default")) if col.get("default") else None,
                    primary_key=col["name"] in pk_columns,
                    autoincrement=col.get("autoincrement", False),
                    comment=col.get("comment"),
                )
                columns.append(col_info)
            
            # Get indexes
            indexes = []
            for idx in inspector.get_indexes(table_name):
                idx_info = IndexInfo(
                    name=idx["name"],
                    columns=idx["column_names"],
                    unique=idx.get("unique", False),
                    type=idx.get("type"),
                )
                indexes.append(idx_info)
            
            # Get foreign keys
            foreign_keys = []
            for fk in inspector.get_foreign_keys(table_name):
                fk_info = ForeignKeyInfo(
                    name=fk.get("name"),
                    constrained_columns=fk["constrained_columns"],
                    referred_schema=fk.get("referred_schema"),
                    referred_table=fk["referred_table"],
                    referred_columns=fk["referred_columns"],
                    on_delete=fk.get("options", {}).get("ondelete"),
                    on_update=fk.get("options", {}).get("onupdate"),
                )
                foreign_keys.append(fk_info)
                
                # Build relationship (many-to-one from FK table)
                relationship = Relationship(
                    from_table=table_name,
                    to_table=fk["referred_table"],
                    from_columns=fk["constrained_columns"],
                    to_columns=fk["referred_columns"],
                    relationship_type="many-to-one",
                )
                relationships.append(relationship)
                
                # Build reverse relationship (one-to-many from referred table)
                reverse_relationship = Relationship(
                    from_table=fk["referred_table"],
                    to_table=table_name,
                    from_columns=fk["referred_columns"],
                    to_columns=fk["constrained_columns"],
                    relationship_type="one-to-many",
                )
                relationships.append(reverse_relationship)
            
            # Get table comment
            try:
                table_comment = inspector.get_table_comment(table_name).get("text")
            except (AttributeError, NotImplementedError):
                table_comment = None
            
            # Try to get row count (optional, might be slow)
            row_count = None
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    row_count = result.scalar()
            except Exception:
                pass  # Row count is optional
            
            table_info = TableInfo(
                name=table_name,
                columns=columns,
                indexes=indexes,
                foreign_keys=foreign_keys,
                primary_key=pk_columns if pk_columns else None,
                comment=table_comment,
                row_count=row_count,
            )
            tables.append(table_info)
        
        return SchemaDefinition(
            tables=tables,
            relationships=relationships,
            metadata={
                "dialect": self.config.dialect,
                "database": self.config.database,
                "table_count": len(tables),
            }
        )
    
    async def validate_syntax(self, query: str) -> ValidationResult:
        """
        Validate SQL query syntax
        
        Args:
            query: SQL query to validate
            
        Returns:
            ValidationResult with validation status and any errors
        """
        start_time = time.time()
        
        try:
            # Parse the query using sqlparse
            parsed = sqlparse.parse(query)
            
            if not parsed:
                return ValidationResult(
                    valid=False,
                    error="Empty or invalid query",
                    validation_time_ms=(time.time() - start_time) * 1000,
                )
            
            # Check for multiple statements
            if len(parsed) > 1:
                return ValidationResult(
                    valid=False,
                    error="Multiple statements not allowed",
                    validation_time_ms=(time.time() - start_time) * 1000,
                )
            
            statement = parsed[0]
            warnings = []
            
            # Check for dangerous operations
            query_upper = query.upper()
            if any(kw in query_upper for kw in ["DROP", "TRUNCATE", "DELETE FROM", "UPDATE"]):
                if "WHERE" not in query_upper and "DROP" not in query_upper:
                    warnings.append("Potentially dangerous operation without WHERE clause")
            
            # Try to prepare the statement (syntax check without execution)
            try:
                await asyncio.to_thread(self._validate_with_database, query)
            except Exception as e:
                return ValidationResult(
                    valid=False,
                    error=f"Database validation failed: {str(e)}",
                    validation_time_ms=(time.time() - start_time) * 1000,
                )
            
            return ValidationResult(
                valid=True,
                warnings=warnings,
                parsed_query=statement,
                validation_time_ms=(time.time() - start_time) * 1000,
            )
            
        except Exception as e:
            return ValidationResult(
                valid=False,
                error=f"Syntax validation failed: {str(e)}",
                validation_time_ms=(time.time() - start_time) * 1000,
            )
    
    def _validate_with_database(self, query: str) -> None:
        """Validate query syntax with database (synchronous)"""
        with self.engine.connect() as conn:
            # Use EXPLAIN to validate without executing
            if self.config.dialect == "postgresql":
                conn.execute(text(f"EXPLAIN {query}"))
            else:
                # For other dialects, just prepare the statement
                conn.execute(text(query).execution_options(compiled_cache=None))
    
    async def execute_query(self, query: str, limit: Optional[int] = None) -> ExecutionResult:
        """
        Execute SQL query and return results
        
        Args:
            query: SQL query to execute
            limit: Maximum number of rows to return
            
        Returns:
            ExecutionResult with query results
        """
        if limit is None:
            limit = self.provider_config.max_rows
        
        start_time = time.time()
        
        try:
            # Add LIMIT clause if not present
            safe_query = self._ensure_limit(query, limit)
            
            # Execute query in thread pool
            result = await asyncio.to_thread(self._execute_query_sync, safe_query)
            
            execution_time_ms = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time_ms
            
            return result
            
        except SQLTimeoutError:
            return ExecutionResult(
                success=False,
                error=f"Query execution timeout after {self.provider_config.timeout_seconds}s",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except SQLAlchemyError as e:
            return ExecutionResult(
                success=False,
                error=f"Database error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
    
    def _execute_query_sync(self, query: str) -> ExecutionResult:
        """Execute query synchronously"""
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            
            # Check if this is a SELECT query
            if result.returns_rows:
                rows = result.fetchall()
                columns = list(result.keys())
                
                # Convert rows to list of dicts for easier handling
                sample_rows = [dict(zip(columns, row)) for row in rows[:10]]
                
                return ExecutionResult(
                    success=True,
                    row_count=len(rows),
                    columns=columns,
                    sample_rows=sample_rows,
                )
            else:
                # For INSERT/UPDATE/DELETE
                return ExecutionResult(
                    success=True,
                    affected_rows=result.rowcount,
                )
    
    async def explain_query(self, query: str) -> Optional[str]:
        """
        Get query execution plan
        
        Args:
            query: SQL query to explain
            
        Returns:
            Query execution plan as string
        """
        try:
            return await asyncio.to_thread(self._explain_query_sync, query)
        except Exception as e:
            return f"Error getting query plan: {str(e)}"
    
    def _explain_query_sync(self, query: str) -> str:
        """Get query execution plan synchronously"""
        with self.engine.connect() as conn:
            if self.config.dialect == "postgresql":
                result = conn.execute(text(f"EXPLAIN ANALYZE {query}"))
                return "\n".join(row[0] for row in result.fetchall())
            elif self.config.dialect == "mysql":
                result = conn.execute(text(f"EXPLAIN {query}"))
                rows = result.fetchall()
                columns = result.keys()
                return "\n".join(str(dict(zip(columns, row))) for row in rows)
            else:
                return f"EXPLAIN not supported for {self.config.dialect}"
    
    def _ensure_limit(self, query: str, limit: int) -> str:
        """
        Ensure query has a LIMIT clause
        
        Args:
            query: Original SQL query
            limit: Maximum number of rows
            
        Returns:
            Query with LIMIT clause added if not present
        """
        query = query.strip().rstrip(";")
        query_upper = query.upper()
        
        # Check if query already has a LIMIT
        if re.search(r'\bLIMIT\s+\d+', query_upper):
            return query
        
        # Add LIMIT for SELECT queries
        if query_upper.startswith("SELECT"):
            return f"{query} LIMIT {limit}"
        
        return query
    
    async def close(self) -> None:
        """Close database connections"""
        if self.engine:
            await asyncio.to_thread(self.engine.dispose)


# Factory function for easy provider creation
def create_sql_provider(
    host: str = "localhost",
    port: int = 5432,
    database: str = "text2x",
    username: str = "text2x",
    password: str = "text2x",
    dialect: str = "postgresql",
    **kwargs
) -> SQLProvider:
    """
    Create SQL provider with sensible defaults
    
    Args:
        host: Database host
        port: Database port
        database: Database name
        username: Database username
        password: Database password
        dialect: SQL dialect (postgresql, mysql, etc.)
        **kwargs: Additional configuration parameters
        
    Returns:
        Configured SQLProvider instance
    """
    config = SQLConnectionConfig(
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        dialect=dialect,
        **kwargs
    )
    
    return SQLProvider(config)
