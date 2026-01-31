"""Async HTTP client for Text2X API."""

from typing import Any, Optional
from uuid import UUID

import httpx
from pydantic import ValidationError

from .models import (
    ConversationResponse,
    ErrorResponse,
    ExampleRequest,
    FeedbackRequest,
    ProviderInfo,
    ProviderSchema,
    QueryRequest,
    QueryResponse,
    RAGExampleResponse,
    ReviewQueueItem,
    ReviewUpdateRequest,
)


class Text2XError(Exception):
    """Base exception for Text2X client errors."""

    pass


class Text2XAPIError(Text2XError):
    """Exception raised when API returns an error response."""

    def __init__(self, error_response: ErrorResponse):
        self.error_response = error_response
        super().__init__(f"{error_response.error}: {error_response.message}")


class Text2XConnectionError(Text2XError):
    """Exception raised when connection to API fails."""

    pass


class Text2XValidationError(Text2XError):
    """Exception raised when request/response validation fails."""

    pass


class Text2XClient:
    """Async HTTP client for Text2X API.

    This client provides a Pythonic interface to the Text2X API for converting
    natural language queries into executable database queries.

    Args:
        base_url: Base URL of the Text2X API (e.g., "http://localhost:8000")
        api_key: Optional API key for authentication
        timeout: Request timeout in seconds (default: 30.0)
        max_retries: Maximum number of retry attempts (default: 3)

    Example:
        ```python
        async with Text2XClient("http://localhost:8000") as client:
            response = await client.query(
                provider_id="postgres_main",
                query="Show me all orders from last month"
            )
            print(response.generated_query)
        ```
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize the Text2X client."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

        # Build headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Initialize httpx client
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from the API."""
        try:
            error_data = response.json()
            error_response = ErrorResponse(**error_data)
            raise Text2XAPIError(error_response)
        except (ValidationError, ValueError):
            # If we can't parse the error response, raise a generic error
            raise Text2XError(
                f"API request failed with status {response.status_code}: {response.text}"
            )

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make an HTTP request to the API."""
        try:
            response = await self._client.request(
                method=method,
                url=endpoint,
                json=json_data,
                params=params,
            )

            if response.status_code >= 400:
                self._handle_error_response(response)

            return response.json()

        except httpx.ConnectError as e:
            raise Text2XConnectionError(f"Failed to connect to API: {e}") from e
        except httpx.TimeoutException as e:
            raise Text2XConnectionError(f"Request timed out: {e}") from e
        except httpx.HTTPError as e:
            raise Text2XError(f"HTTP error occurred: {e}") from e

    async def query(
        self,
        provider_id: str,
        query: str,
        conversation_id: Optional[UUID] = None,
        **options,
    ) -> QueryResponse:
        """Generate a database query from natural language.

        Args:
            provider_id: ID of the database provider/connection
            query: Natural language query
            conversation_id: Optional conversation ID for multi-turn dialogue
            **options: Additional query options (max_iterations, confidence_threshold, etc.)

        Returns:
            QueryResponse with generated query and metadata

        Raises:
            Text2XAPIError: If API returns an error
            Text2XConnectionError: If connection fails
            Text2XValidationError: If request/response validation fails

        Example:
            ```python
            response = await client.query(
                provider_id="postgres_main",
                query="Show me all orders from last month",
                max_iterations=5,
                trace_level="summary"
            )
            ```
        """
        try:
            request = QueryRequest(
                provider_id=provider_id,
                query=query,
                conversation_id=conversation_id,
                options=options,
            )
        except ValidationError as e:
            raise Text2XValidationError(f"Invalid request: {e}") from e

        data = await self._request("POST", "/api/v1/query", json_data=request.model_dump())

        try:
            return QueryResponse(**data)
        except ValidationError as e:
            raise Text2XValidationError(f"Invalid response: {e}") from e

    async def get_conversation(self, conversation_id: UUID) -> ConversationResponse:
        """Get conversation details by ID.

        Args:
            conversation_id: Conversation UUID

        Returns:
            ConversationResponse with conversation details and turns

        Example:
            ```python
            conversation = await client.get_conversation(conversation_id)
            print(f"Turns: {conversation.turn_count}")
            ```
        """
        data = await self._request("GET", f"/api/v1/conversations/{conversation_id}")

        try:
            return ConversationResponse(**data)
        except ValidationError as e:
            raise Text2XValidationError(f"Invalid response: {e}") from e

    async def submit_feedback(
        self,
        conversation_id: UUID,
        rating: int,
        is_query_correct: bool,
        corrected_query: Optional[str] = None,
        comments: Optional[str] = None,
    ) -> dict[str, Any]:
        """Submit feedback for a conversation.

        Args:
            conversation_id: Conversation UUID
            rating: User satisfaction rating (1-5)
            is_query_correct: Whether the generated query is correct
            corrected_query: Optional corrected query if original was wrong
            comments: Optional feedback comments

        Returns:
            Success response

        Example:
            ```python
            await client.submit_feedback(
                conversation_id=conversation_id,
                rating=5,
                is_query_correct=True,
                comments="Perfect query!"
            )
            ```
        """
        try:
            request = FeedbackRequest(
                rating=rating,
                is_query_correct=is_query_correct,
                corrected_query=corrected_query,
                comments=comments,
            )
        except ValidationError as e:
            raise Text2XValidationError(f"Invalid request: {e}") from e

        return await self._request(
            "POST",
            f"/api/v1/conversations/{conversation_id}/feedback",
            json_data=request.model_dump(),
        )

    async def list_providers(self) -> list[ProviderInfo]:
        """List all available database providers.

        Returns:
            List of ProviderInfo objects

        Example:
            ```python
            providers = await client.list_providers()
            for provider in providers:
                print(f"{provider.name}: {provider.connection_status}")
            ```
        """
        data = await self._request("GET", "/api/v1/providers")

        try:
            return [ProviderInfo(**item) for item in data]
        except ValidationError as e:
            raise Text2XValidationError(f"Invalid response: {e}") from e

    async def get_schema(self, provider_id: str) -> ProviderSchema:
        """Get schema information for a provider.

        Args:
            provider_id: Provider identifier

        Returns:
            ProviderSchema with table and column information

        Example:
            ```python
            schema = await client.get_schema("postgres_main")
            for table in schema.tables:
                print(f"Table: {table.name}, Columns: {len(table.columns)}")
            ```
        """
        data = await self._request("GET", f"/api/v1/providers/{provider_id}/schema")

        try:
            return ProviderSchema(**data)
        except ValidationError as e:
            raise Text2XValidationError(f"Invalid response: {e}") from e

    async def refresh_schema(self, provider_id: str) -> dict[str, Any]:
        """Trigger a schema refresh for a provider.

        Args:
            provider_id: Provider identifier

        Returns:
            Success response

        Example:
            ```python
            result = await client.refresh_schema("postgres_main")
            print(result["message"])
            ```
        """
        return await self._request("POST", f"/api/v1/providers/{provider_id}/schema/refresh")

    async def get_review_queue(self, limit: int = 50) -> list[ReviewQueueItem]:
        """Get pending items from the expert review queue.

        Args:
            limit: Maximum number of items to return (default: 50)

        Returns:
            List of ReviewQueueItem objects

        Example:
            ```python
            queue = await client.get_review_queue(limit=10)
            for item in queue:
                print(f"Review needed: {item.reason_for_review}")
            ```
        """
        data = await self._request("GET", "/api/v1/review/queue", params={"limit": limit})

        try:
            return [ReviewQueueItem(**item) for item in data]
        except ValidationError as e:
            raise Text2XValidationError(f"Invalid response: {e}") from e

    async def submit_review(
        self,
        review_id: UUID,
        approved: bool,
        corrected_query: Optional[str] = None,
        feedback: Optional[str] = None,
    ) -> dict[str, Any]:
        """Submit an expert review for a queued item.

        Args:
            review_id: Review item UUID
            approved: Whether the query is approved
            corrected_query: Optional corrected query
            feedback: Optional expert feedback

        Returns:
            Success response

        Example:
            ```python
            await client.submit_review(
                review_id=item.id,
                approved=True,
                feedback="Query looks good"
            )
            ```
        """
        try:
            request = ReviewUpdateRequest(
                approved=approved,
                corrected_query=corrected_query,
                feedback=feedback,
            )
        except ValidationError as e:
            raise Text2XValidationError(f"Invalid request: {e}") from e

        return await self._request(
            "PUT",
            f"/api/v1/review/queue/{review_id}",
            json_data=request.model_dump(),
        )

    async def list_examples(
        self,
        provider_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[RAGExampleResponse]:
        """List RAG examples.

        Args:
            provider_id: Optional filter by provider
            status: Optional filter by status (pending_review, approved, rejected)
            limit: Maximum number of items to return (default: 50)

        Returns:
            List of RAGExampleResponse objects

        Example:
            ```python
            examples = await client.list_examples(
                provider_id="postgres_main",
                status="approved",
                limit=20
            )
            ```
        """
        params = {"limit": limit}
        if provider_id:
            params["provider_id"] = provider_id
        if status:
            params["status"] = status

        data = await self._request("GET", "/api/v1/examples", params=params)

        try:
            return [RAGExampleResponse(**item) for item in data]
        except ValidationError as e:
            raise Text2XValidationError(f"Invalid response: {e}") from e

    async def add_example(
        self,
        provider_id: str,
        natural_language_query: str,
        generated_query: str,
        is_good_example: bool,
        involved_tables: Optional[list[str]] = None,
        query_intent: Optional[str] = None,
        complexity_level: Optional[str] = None,
    ) -> RAGExampleResponse:
        """Add a new RAG example.

        Args:
            provider_id: Provider identifier
            natural_language_query: Natural language query text
            generated_query: Generated database query
            is_good_example: True for positive example, False for negative
            involved_tables: Optional list of table names
            query_intent: Optional query intent classification
            complexity_level: Optional complexity level

        Returns:
            RAGExampleResponse for the created example

        Example:
            ```python
            example = await client.add_example(
                provider_id="postgres_main",
                natural_language_query="Show recent orders",
                generated_query="SELECT * FROM orders ORDER BY created_at DESC LIMIT 10",
                is_good_example=True,
                involved_tables=["orders"]
            )
            ```
        """
        try:
            request = ExampleRequest(
                provider_id=provider_id,
                natural_language_query=natural_language_query,
                generated_query=generated_query,
                is_good_example=is_good_example,
                involved_tables=involved_tables or [],
                query_intent=query_intent,
                complexity_level=complexity_level,
            )
        except ValidationError as e:
            raise Text2XValidationError(f"Invalid request: {e}") from e

        data = await self._request("POST", "/api/v1/examples", json_data=request.model_dump())

        try:
            return RAGExampleResponse(**data)
        except ValidationError as e:
            raise Text2XValidationError(f"Invalid response: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        """Check API health status.

        Returns:
            Health check response with service status

        Example:
            ```python
            health = await client.health_check()
            print(f"Status: {health['status']}")
            ```
        """
        return await self._request("GET", "/api/v1/health")
