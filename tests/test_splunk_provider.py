"""Tests for Splunk Provider"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.text2x.providers.splunk_provider import (
    SplunkProvider,
    SplunkConnectionConfig,
    SearchJobStatus,
    create_splunk_provider,
)
from src.text2x.providers.base import (
    ProviderCapability,
    ValidationResult,
    ExecutionResult,
)


@pytest.fixture
def splunk_config():
    """Create test Splunk configuration"""
    return SplunkConnectionConfig(
        host="localhost",
        port=8089,
        username="admin",
        password="changeme",
        scheme="https",
        verify=False,
    )


@pytest.fixture
def mock_splunk_service():
    """Create mock Splunk service"""
    service = Mock()

    # Mock indexes
    index_mock = Mock()
    index_mock.name = "main"
    index_mock.get = Mock(side_effect=lambda k, default=0: {
        'totalEventCount': 1000,
        'currentDBSizeMB': 50.5,
    }.get(k, default))

    service.indexes = [index_mock]

    return service


class TestSplunkProvider:
    """Test suite for SplunkProvider"""

    def test_provider_initialization(self, splunk_config):
        """Test provider initialization"""
        provider = SplunkProvider(splunk_config)

        assert provider.get_provider_id() == f"splunk_{splunk_config.host}"
        assert provider.get_query_language() == "SPL"

    def test_provider_capabilities(self, splunk_config):
        """Test provider capabilities"""
        provider = SplunkProvider(splunk_config)
        capabilities = provider.get_capabilities()

        assert ProviderCapability.SCHEMA_INTROSPECTION in capabilities
        assert ProviderCapability.QUERY_VALIDATION in capabilities
        assert ProviderCapability.QUERY_EXECUTION in capabilities

    @pytest.mark.asyncio
    @patch('src.text2x.providers.splunk_provider.client.connect')
    async def test_get_schema(self, mock_connect, splunk_config, mock_splunk_service):
        """Test schema retrieval"""
        mock_connect.return_value = mock_splunk_service

        provider = SplunkProvider(splunk_config)
        schema = await provider.get_schema()

        assert schema is not None
        assert len(schema.tables) > 0
        assert schema.metadata['provider'] == 'splunk'
        assert schema.metadata['host'] == splunk_config.host

    def test_ensure_limit(self, splunk_config):
        """Test query limit enforcement"""
        provider = SplunkProvider(splunk_config)

        # Query without limit
        query = "search index=main error"
        limited_query = provider._ensure_limit(query, 100)
        assert "| head 100" in limited_query

        # Query with existing head
        query_with_head = "search index=main error | head 50"
        result = provider._ensure_limit(query_with_head, 100)
        assert result == query_with_head  # Should not modify

        # Query with tail
        query_with_tail = "search index=main error | tail 50"
        result = provider._ensure_limit(query_with_tail, 100)
        assert result == query_with_tail  # Should not modify

    @pytest.mark.asyncio
    async def test_validate_syntax_empty_query(self, splunk_config):
        """Test validation of empty query"""
        provider = SplunkProvider(splunk_config)
        result = await provider.validate_syntax("")

        assert not result.valid
        assert "Empty query" in result.error

    @pytest.mark.asyncio
    async def test_validate_syntax_warnings(self, splunk_config):
        """Test validation warnings"""
        provider = SplunkProvider(splunk_config)

        # Query without 'search' prefix should generate warning
        with patch.object(provider, '_validate_with_splunk', return_value=ValidationResult(valid=True)):
            result = await provider.validate_syntax("index=main error")

            assert result.valid
            assert len(result.warnings) > 0
            assert any("search" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    @patch('src.text2x.providers.splunk_provider.client.connect')
    async def test_execute_query_success(self, mock_connect, splunk_config):
        """Test successful query execution"""
        # Setup mock
        mock_service = Mock()
        mock_job = Mock()
        mock_job.sid = "12345"
        mock_job.is_done = Mock(return_value=True)
        mock_job.get = Mock(side_effect=lambda k, default=0: {
            'doneProgress': '1.0',
            'eventCount': '100',
            'resultCount': '100',
            'scanCount': '100',
            'runDuration': '1.5',
            'isFailed': '0',
        }.get(k, str(default)))

        # Mock results
        mock_results = [
            {'_time': '2024-01-01', 'host': 'server1', 'message': 'error'},
            {'_time': '2024-01-02', 'host': 'server2', 'message': 'warning'},
        ]
        mock_job.results = Mock(return_value=iter(mock_results))
        mock_job.cancel = Mock()

        mock_service.jobs.create = Mock(return_value=mock_job)
        mock_connect.return_value = mock_service

        provider = SplunkProvider(splunk_config)
        result = await provider.execute_query("search index=main error", limit=10)

        assert result.success
        assert result.row_count == 2
        assert len(result.sample_rows) == 2
        assert '_time' in result.columns

    @pytest.mark.asyncio
    @patch('src.text2x.providers.splunk_provider.client.connect')
    async def test_execute_query_failure(self, mock_connect, splunk_config):
        """Test query execution failure"""
        # Setup mock for failed job
        mock_service = Mock()
        mock_job = Mock()
        mock_job.sid = "12345"
        mock_job.is_done = Mock(return_value=True)
        mock_job.get = Mock(side_effect=lambda k, default=0: {
            'isFailed': '1',
            'messages': 'Invalid search command',
        }.get(k, str(default)))

        mock_service.jobs.create = Mock(return_value=mock_job)
        mock_connect.return_value = mock_service

        provider = SplunkProvider(splunk_config)
        result = await provider.execute_query("search invalid syntax", limit=10)

        assert not result.success
        assert "failed" in result.error.lower() or "error" in result.error.lower()

    def test_factory_function(self):
        """Test factory function"""
        provider = create_splunk_provider(
            host="splunk.example.com",
            port=8089,
            username="admin",
            password="password123"
        )

        assert isinstance(provider, SplunkProvider)
        assert provider.config.host == "splunk.example.com"
        assert provider.config.port == 8089
        assert provider.config.username == "admin"

    @pytest.mark.asyncio
    @patch('src.text2x.providers.splunk_provider.client.connect')
    async def test_search_job_cancellation(self, mock_connect, splunk_config):
        """Test search job cancellation"""
        mock_service = Mock()
        mock_job = Mock()
        mock_job.cancel = Mock()

        mock_service.job = Mock(return_value=mock_job)
        mock_connect.return_value = mock_service

        provider = SplunkProvider(splunk_config)
        result = await provider.cancel_search_job("test_sid_123")

        assert result is True
        mock_job.cancel.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.text2x.providers.splunk_provider.client.connect')
    async def test_get_search_job_status(self, mock_connect, splunk_config):
        """Test getting search job status"""
        mock_service = Mock()
        mock_job = Mock()
        mock_job.sid = "test_sid"
        mock_job.get = Mock(side_effect=lambda k, default=0: {
            'dispatchState': 'RUNNING',
            'doneProgress': '0.5',
            'eventCount': '50',
            'resultCount': '50',
        }.get(k, str(default)))

        mock_service.job = Mock(return_value=mock_job)
        mock_connect.return_value = mock_service

        provider = SplunkProvider(splunk_config)
        status = await provider.get_search_job_status("test_sid")

        assert status is not None
        assert status.sid == "test_sid"
        assert status.status == SearchJobStatus.RUNNING
        assert status.event_count == 50

    @pytest.mark.asyncio
    async def test_close_connection(self, splunk_config):
        """Test closing connection"""
        provider = SplunkProvider(splunk_config)

        # Should not raise any errors
        await provider.close()
        assert provider._service is None


class TestSplunkConnectionConfig:
    """Test suite for SplunkConnectionConfig"""

    def test_connection_config_defaults(self):
        """Test connection config default values"""
        config = SplunkConnectionConfig(
            host="localhost",
            username="admin",
            password="changeme"
        )

        assert config.host == "localhost"
        assert config.port == 8089
        assert config.scheme == "https"
        assert config.verify is False
        assert config.owner == "admin"
        assert config.app == "search"

    def test_connection_config_with_token(self):
        """Test connection config with token authentication"""
        config = SplunkConnectionConfig(
            host="localhost",
            username="admin",
            password="",
            token="Bearer abc123"
        )

        assert config.token == "Bearer abc123"

    def test_connection_config_extra_params(self):
        """Test connection config with extra parameters"""
        config = SplunkConnectionConfig(
            host="localhost",
            username="admin",
            password="changeme",
            extra_params={"custom_param": "value"}
        )

        assert config.extra_params["custom_param"] == "value"
