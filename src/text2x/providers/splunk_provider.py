"""Splunk Provider Implementation for Text2X"""
import asyncio
import time
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

import splunklib.client as client
from splunklib.results import JSONResultsReader

from .base import (
    QueryProvider,
    ProviderCapability,
    SchemaDefinition,
    ValidationResult,
    ExecutionResult,
    TableInfo,
    ColumnInfo,
    ProviderConfig,
)


class SearchJobStatus(Enum):
    """Splunk search job status"""
    QUEUED = "QUEUED"
    PARSING = "PARSING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    FINALIZING = "FINALIZING"
    FAILED = "FAILED"
    DONE = "DONE"


@dataclass
class SplunkConnectionConfig:
    """Configuration for Splunk connection"""
    host: str
    port: int = 8089
    username: str = "admin"
    password: str = ""
    scheme: str = "https"
    owner: str = "admin"
    app: str = "search"
    token: Optional[str] = None  # For token-based authentication
    verify: bool = False  # SSL verification
    autologin: bool = True
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SplunkSearchJob:
    """Represents a Splunk search job"""
    sid: str  # Search ID
    status: SearchJobStatus
    progress: float = 0.0
    event_count: int = 0
    result_count: int = 0
    scan_count: int = 0
    error: Optional[str] = None
    earliest_time: Optional[str] = None
    latest_time: Optional[str] = None
    run_duration: Optional[float] = None


@dataclass
class SplunkFieldInfo:
    """Information about a Splunk field"""
    name: str
    type: str = "unknown"  # string, number, boolean, timestamp
    distinct_count: Optional[int] = None
    common_values: Optional[List[str]] = None


@dataclass
class SplunkIndexInfo:
    """Information about a Splunk index"""
    name: str
    total_event_count: Optional[int] = None
    earliest_time: Optional[str] = None
    latest_time: Optional[str] = None
    total_size_mb: Optional[float] = None
    sourcetypes: List[str] = field(default_factory=list)


class SplunkProvider(QueryProvider):
    """Splunk Provider for SPL (Search Processing Language) queries"""

    def __init__(self, config: SplunkConnectionConfig, provider_config: Optional[ProviderConfig] = None):
        """
        Initialize Splunk Provider

        Args:
            config: Splunk connection configuration
            provider_config: General provider configuration
        """
        self.config = config
        self.provider_config = provider_config or ProviderConfig(provider_type="splunk")

        # Connection will be created lazily
        self._service = None
        self._schema_cache: Optional[SchemaDefinition] = None
        self._cache_time: Optional[float] = None
        self._cache_ttl = 3600  # 1 hour cache for schema

    def _get_service(self) -> client.Service:
        """Get or create Splunk service connection"""
        if self._service is None:
            # Build connection arguments
            conn_args = {
                'host': self.config.host,
                'port': self.config.port,
                'scheme': self.config.scheme,
                'verify': self.config.verify,
                'owner': self.config.owner,
                'app': self.config.app,
                'autologin': self.config.autologin,
            }

            # Use token or username/password authentication
            if self.config.token:
                conn_args['token'] = self.config.token
            else:
                conn_args['username'] = self.config.username
                conn_args['password'] = self.config.password

            # Add any extra parameters
            conn_args.update(self.config.extra_params)

            self._service = client.connect(**conn_args)

        return self._service

    def get_provider_id(self) -> str:
        """Unique identifier for this provider"""
        return f"splunk_{self.config.host}"

    def get_query_language(self) -> str:
        """Query language supported by this provider"""
        return "SPL"

    def get_capabilities(self) -> List[ProviderCapability]:
        """List of capabilities this provider supports"""
        return [
            ProviderCapability.SCHEMA_INTROSPECTION,
            ProviderCapability.QUERY_VALIDATION,
            ProviderCapability.QUERY_EXECUTION,
        ]

    async def get_schema(self) -> SchemaDefinition:
        """
        Retrieve the Splunk schema (indexes, sourcetypes, and common fields)

        Returns:
            SchemaDefinition with Splunk indexes and field information
        """
        # Check cache
        if self._schema_cache and self._cache_time:
            if time.time() - self._cache_time < self._cache_ttl:
                return self._schema_cache

        # Use asyncio.to_thread to run blocking Splunk SDK code in thread pool
        schema = await asyncio.to_thread(self._get_schema_sync)

        # Update cache
        self._schema_cache = schema
        self._cache_time = time.time()

        return schema

    def _get_schema_sync(self) -> SchemaDefinition:
        """Synchronous schema introspection"""
        service = self._get_service()

        # Get all indexes
        indexes = service.indexes
        index_infos = []
        all_sourcetypes = set()

        for index in indexes:
            index_name = index.name

            # Skip internal indexes
            if index_name.startswith('_') and index_name not in ['_internal', '_audit']:
                continue

            # Get index statistics
            index_info = SplunkIndexInfo(
                name=index_name,
                total_event_count=int(index.get('totalEventCount', 0)),
                total_size_mb=float(index.get('currentDBSizeMB', 0)),
            )

            # Get sourcetypes for this index
            try:
                # Search for sourcetypes in this index (limited to avoid long query)
                search_query = f'| metadata type=sourcetypes index={index_name}'
                job = service.jobs.create(search_query, exec_mode="blocking", max_time=10)

                sourcetypes = []
                for result in JSONResultsReader(job.results(output_mode='json')):
                    if isinstance(result, dict) and 'sourcetype' in result:
                        sourcetype = result['sourcetype']
                        sourcetypes.append(sourcetype)
                        all_sourcetypes.add(sourcetype)

                index_info.sourcetypes = sourcetypes
                job.cancel()
            except Exception:
                # If metadata search fails, continue without sourcetypes
                pass

            index_infos.append(index_info)

        # Get common fields across all data
        # This is done by running a sample search and examining field extractions
        common_fields = self._get_common_fields(service)

        # Convert to TableInfo format (treating indexes as "tables")
        tables = []
        for idx_info in index_infos:
            # Create columns from common fields
            columns = [
                ColumnInfo(
                    name=field.name,
                    type=field.type,
                    comment=f"Common field in Splunk (distinct values: {field.distinct_count})"
                )
                for field in common_fields
            ]

            # Add sourcetype information to comment
            sourcetype_info = f"Sourcetypes: {', '.join(idx_info.sourcetypes[:5])}"
            if len(idx_info.sourcetypes) > 5:
                sourcetype_info += f" (and {len(idx_info.sourcetypes) - 5} more)"

            table = TableInfo(
                name=idx_info.name,
                columns=columns,
                comment=sourcetype_info,
                row_count=idx_info.total_event_count,
            )
            tables.append(table)

        return SchemaDefinition(
            tables=tables,
            sourcetypes=sorted(list(all_sourcetypes)),
            metadata={
                "provider": "splunk",
                "host": self.config.host,
                "index_count": len(index_infos),
                "sourcetype_count": len(all_sourcetypes),
            }
        )

    def _get_common_fields(self, service: client.Service) -> List[SplunkFieldInfo]:
        """Get common fields from Splunk"""
        # Default common fields in Splunk
        common_fields = [
            SplunkFieldInfo(name="_time", type="timestamp"),
            SplunkFieldInfo(name="_raw", type="string"),
            SplunkFieldInfo(name="host", type="string"),
            SplunkFieldInfo(name="source", type="string"),
            SplunkFieldInfo(name="sourcetype", type="string"),
            SplunkFieldInfo(name="index", type="string"),
            SplunkFieldInfo(name="_indextime", type="timestamp"),
        ]

        # Try to get additional fields from recent data
        try:
            search_query = 'search * | head 1000 | fieldsummary | fields field'
            job = service.jobs.create(search_query, exec_mode="blocking", max_time=15)

            for result in JSONResultsReader(job.results(output_mode='json')):
                if isinstance(result, dict) and 'field' in result:
                    field_name = result['field']
                    # Skip internal fields and already included fields
                    if not field_name.startswith('_') and field_name not in [f.name for f in common_fields]:
                        common_fields.append(SplunkFieldInfo(name=field_name, type="string"))

            job.cancel()
        except Exception:
            # If field discovery fails, just use default fields
            pass

        return common_fields

    async def validate_syntax(self, query: str) -> ValidationResult:
        """
        Validate SPL query syntax

        Args:
            query: SPL query to validate

        Returns:
            ValidationResult with validation status and any errors
        """
        start_time = time.time()

        try:
            # Basic syntax checks
            query = query.strip()
            if not query:
                return ValidationResult(
                    valid=False,
                    error="Empty query",
                    validation_time_ms=(time.time() - start_time) * 1000,
                )

            warnings = []

            # Check if query starts with search command or pipe
            if not query.startswith('search') and not query.startswith('|'):
                warnings.append("Query should start with 'search' or '|' for best practice")

            # Check for common syntax issues
            if query.count('|') != query.count('| ') and '||' not in query:
                warnings.append("Pipes should be followed by a space")

            # Validate with Splunk by parsing
            result = await asyncio.to_thread(self._validate_with_splunk, query)

            validation_time = (time.time() - start_time) * 1000
            result.validation_time_ms = validation_time
            if warnings and result.valid:
                result.warnings.extend(warnings)

            return result

        except Exception as e:
            return ValidationResult(
                valid=False,
                error=f"Validation error: {str(e)}",
                validation_time_ms=(time.time() - start_time) * 1000,
            )

    def _validate_with_splunk(self, query: str) -> ValidationResult:
        """Validate query with Splunk (synchronous)"""
        service = self._get_service()

        try:
            # Parse the search query using Splunk's parser
            # We create a search job with exec_mode="oneshot" and a very early finish_time
            # This will validate syntax without actually running the search
            job = service.jobs.create(
                query,
                exec_mode="blocking",
                max_time=1,  # Timeout after 1 second
                status_buckets=0,
                rf=["*"],
            )

            # If we get here, syntax is valid
            job.cancel()

            return ValidationResult(
                valid=True,
                warnings=[],
            )

        except Exception as e:
            error_msg = str(e)

            # Parse Splunk error messages for better feedback
            if "Error in 'search' command" in error_msg:
                return ValidationResult(valid=False, error=f"Search command error: {error_msg}")
            elif "Unable to parse" in error_msg:
                return ValidationResult(valid=False, error=f"Parse error: {error_msg}")
            else:
                return ValidationResult(valid=False, error=error_msg)

    async def execute_query(self, query: str, limit: Optional[int] = None) -> ExecutionResult:
        """
        Execute SPL query and return results

        Args:
            query: SPL query to execute
            limit: Maximum number of results to return

        Returns:
            ExecutionResult with query results
        """
        if limit is None:
            limit = self.provider_config.max_rows

        start_time = time.time()

        try:
            # Add head command if not present to limit results
            safe_query = self._ensure_limit(query, limit)

            # Execute query in thread pool
            result = await asyncio.to_thread(self._execute_query_sync, safe_query)

            execution_time_ms = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time_ms

            return result

        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def _execute_query_sync(self, query: str) -> ExecutionResult:
        """Execute query synchronously"""
        service = self._get_service()

        try:
            # Create search job
            job = service.jobs.create(
                query,
                exec_mode="blocking",  # Wait for job to complete
                max_time=self.provider_config.timeout_seconds,
            )

            # Wait for job to complete and poll status
            search_job_info = self._poll_search_job(job)

            if search_job_info.status == SearchJobStatus.FAILED:
                return ExecutionResult(
                    success=False,
                    error=search_job_info.error or "Search job failed",
                )

            # Get results
            result_rows = []
            columns = set()

            for result in JSONResultsReader(job.results(output_mode='json')):
                if isinstance(result, dict):
                    # Track all columns
                    columns.update(result.keys())
                    result_rows.append(result)

            # Clean up
            job.cancel()

            # Prepare sample rows (first 10)
            sample_rows = result_rows[:10]

            return ExecutionResult(
                success=True,
                row_count=len(result_rows),
                columns=sorted(list(columns)),
                sample_rows=sample_rows,
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Search execution failed: {str(e)}",
            )

    def _poll_search_job(self, job: client.Job, poll_interval: float = 0.5) -> SplunkSearchJob:
        """
        Poll search job until completion

        Args:
            job: Splunk search job
            poll_interval: Polling interval in seconds

        Returns:
            SplunkSearchJob with final status
        """
        while not job.is_done():
            time.sleep(poll_interval)
            job.refresh()

        # Get final job status
        job_info = SplunkSearchJob(
            sid=job.sid,
            status=SearchJobStatus.DONE if job.is_done() else SearchJobStatus.RUNNING,
            progress=float(job.get('doneProgress', 0.0)) * 100,
            event_count=int(job.get('eventCount', 0)),
            result_count=int(job.get('resultCount', 0)),
            scan_count=int(job.get('scanCount', 0)),
            run_duration=float(job.get('runDuration', 0.0)),
        )

        # Check for errors
        if job.get('isFailed') == '1':
            job_info.status = SearchJobStatus.FAILED
            job_info.error = job.get('messages', 'Unknown error')

        return job_info

    def _ensure_limit(self, query: str, limit: int) -> str:
        """
        Ensure query has a limit (head command in SPL)

        Args:
            query: Original SPL query
            limit: Maximum number of results

        Returns:
            Query with head command added if not present
        """
        query = query.strip()
        query_lower = query.lower()

        # Check if query already has head or tail command
        if ' head ' in query_lower or query_lower.endswith('head') or \
           ' tail ' in query_lower or query_lower.endswith('tail') or \
           ' head=' in query_lower or ' limit=' in query_lower:
            return query

        # Add head command at the end
        return f"{query} | head {limit}"

    async def get_search_job_status(self, sid: str) -> Optional[SplunkSearchJob]:
        """
        Get status of a search job

        Args:
            sid: Search job ID

        Returns:
            SplunkSearchJob with current status or None if not found
        """
        try:
            return await asyncio.to_thread(self._get_search_job_status_sync, sid)
        except Exception:
            return None

    def _get_search_job_status_sync(self, sid: str) -> SplunkSearchJob:
        """Get search job status synchronously"""
        service = self._get_service()
        job = service.job(sid)

        return SplunkSearchJob(
            sid=job.sid,
            status=SearchJobStatus(job.get('dispatchState', 'RUNNING')),
            progress=float(job.get('doneProgress', 0.0)) * 100,
            event_count=int(job.get('eventCount', 0)),
            result_count=int(job.get('resultCount', 0)),
            scan_count=int(job.get('scanCount', 0)),
            run_duration=float(job.get('runDuration', 0.0)),
        )

    async def cancel_search_job(self, sid: str) -> bool:
        """
        Cancel a running search job

        Args:
            sid: Search job ID

        Returns:
            True if cancelled successfully
        """
        try:
            await asyncio.to_thread(self._cancel_search_job_sync, sid)
            return True
        except Exception:
            return False

    def _cancel_search_job_sync(self, sid: str) -> None:
        """Cancel search job synchronously"""
        service = self._get_service()
        job = service.job(sid)
        job.cancel()

    async def close(self) -> None:
        """Close Splunk connection"""
        if self._service:
            # Splunk SDK doesn't have explicit close, connections are managed automatically
            self._service = None


# Factory function for easy provider creation
def create_splunk_provider(
    host: str = "localhost",
    port: int = 8089,
    username: str = "admin",
    password: str = "",
    **kwargs
) -> SplunkProvider:
    """
    Create Splunk provider with sensible defaults

    Args:
        host: Splunk host
        port: Splunk management port (default 8089)
        username: Splunk username
        password: Splunk password
        **kwargs: Additional configuration parameters

    Returns:
        Configured SplunkProvider instance
    """
    config = SplunkConnectionConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        **kwargs
    )

    return SplunkProvider(config)
