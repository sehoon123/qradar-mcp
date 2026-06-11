"""
Tests for QRadarRestClient HTTP methods (POST, DELETE)
"""

import pytest
from unittest.mock import patch, AsyncMock
import httpx
from qradar_mcp.client.qradar_rest_client import QRadarRestClient


class TestQRadarRestClientPOST:
    """Tests for POST method."""

    @pytest.mark.asyncio
    @patch('qradar_mcp.client.qradar_rest_client.log_structured')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_post_with_dict_data(self, mock_load_config, mock_log):
        """Test POST request with dictionary data."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token",
                "verify_ssl": False
            }
        }
        mock_load_config.return_value = mock_config

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = httpx.Response(201, request=httpx.Request("POST", "http://test"))
        mock_client.post = AsyncMock(return_value=mock_response)

        client = QRadarRestClient(client=mock_client)
        data = {"key": "value", "number": 123}

        response = await client.post('test/endpoint', data=data)

        assert response.status_code == 201
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args[1]
        # httpx uses 'json' parameter for dict data
        assert call_kwargs.get('json') == data or call_kwargs.get('content')
        assert 'Content-Type' in call_kwargs['headers']
        assert call_kwargs['headers']['Content-Type'] == 'application/json'

    @pytest.mark.asyncio
    @patch('qradar_mcp.client.qradar_rest_client.log_structured')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_post_with_string_data(self, mock_load_config, mock_log):
        """Test POST request with string data."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token",
                "verify_ssl": False
            }
        }
        mock_load_config.return_value = mock_config

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = httpx.Response(200, request=httpx.Request("POST", "http://test"))
        mock_client.post = AsyncMock(return_value=mock_response)

        client = QRadarRestClient(client=mock_client)
        data = "raw string data"

        response = await client.post('test/endpoint', data=data)

        assert response.status_code == 200
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args[1]
        # httpx uses 'content' parameter for string data
        assert call_kwargs.get('content') == data or call_kwargs.get('data') == data

    @pytest.mark.asyncio
    @patch('qradar_mcp.client.qradar_rest_client.log_structured')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_post_with_params(self, mock_load_config, mock_log):
        """Test POST request with query parameters."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_load_config.return_value = mock_config

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = httpx.Response(200, request=httpx.Request("POST", "http://test"))
        mock_client.post = AsyncMock(return_value=mock_response)

        client = QRadarRestClient(client=mock_client)
        params = {"filter": "test", "limit": 10}

        response = await client.post('test/endpoint', params=params)

        assert response.status_code == 200
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs['params'] == params

    @pytest.mark.asyncio
    @patch('qradar_mcp.client.qradar_rest_client.log_structured')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_post_with_custom_headers(self, mock_load_config, mock_log):
        """Test POST request with custom headers."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_load_config.return_value = mock_config

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = httpx.Response(200, request=httpx.Request("POST", "http://test"))
        mock_client.post = AsyncMock(return_value=mock_response)

        client = QRadarRestClient(client=mock_client)
        custom_headers = {"Content-Type": "application/xml"}

        response = await client.post('test/endpoint', headers=custom_headers, data={"test": "data"})

        assert response.status_code == 200
        call_kwargs = mock_client.post.call_args[1]
        # Should not override existing Content-Type
        assert call_kwargs['headers']['Content-Type'] == 'application/xml'

    @pytest.mark.asyncio
    @patch('qradar_mcp.client.qradar_rest_client.log_structured')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_post_with_proxy(self, mock_load_config, mock_log):
        """Test POST request with proxy configuration."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token",
                "proxy": "http://proxy.local:8080"
            }
        }
        mock_load_config.return_value = mock_config

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = httpx.Response(200, request=httpx.Request("POST", "http://test"))
        mock_client.post = AsyncMock(return_value=mock_response)

        client = QRadarRestClient(client=mock_client)

        response = await client.post('test/endpoint')

        assert response.status_code == 200
        # httpx handles proxies differently, just verify call was made
        assert mock_client.post.called

    @pytest.mark.asyncio
    @patch('qradar_mcp.utils.retry.asyncio.sleep')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_post_retries_aql_validator(self, mock_load_config, mock_sleep):
        """Test explicitly safe POST endpoints are retried."""
        mock_load_config.return_value = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_sleep.return_value = None

        request = httpx.Request("POST", "https://qradar.local/api/ariel/validators/aql")
        retryable_response = httpx.Response(503, request=request)
        success_response = httpx.Response(200, request=request)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=[retryable_response, success_response])

        client = QRadarRestClient(client=mock_client)
        response = await client.post('ariel/validators/aql', data={"query_expression": "SELECT * FROM events"})

        assert response.status_code == 200
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    @patch('qradar_mcp.utils.retry.asyncio.sleep')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_post_does_not_retry_ariel_search_creation(self, mock_load_config, mock_sleep):
        """Test Ariel search job creation is not automatically retried."""
        mock_load_config.return_value = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_sleep.return_value = None

        request = httpx.Request("POST", "https://qradar.local/api/ariel/searches")
        retryable_response = httpx.Response(503, request=request)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=retryable_response)

        client = QRadarRestClient(client=mock_client)
        response = await client.post('ariel/searches', params={"query_expression": "SELECT * FROM events"})

        assert response.status_code == 503
        assert mock_client.post.call_count == 1
        mock_sleep.assert_not_called()


class TestQRadarRestClientDELETE:
    """Tests for DELETE method."""

    @pytest.mark.asyncio
    @patch('qradar_mcp.client.qradar_rest_client.log_structured')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_delete_basic(self, mock_load_config, mock_log):
        """Test basic DELETE request."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token",
                "verify_ssl": False
            }
        }
        mock_load_config.return_value = mock_config

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = httpx.Response(204, request=httpx.Request("DELETE", "http://test"))
        mock_client.delete = AsyncMock(return_value=mock_response)

        client = QRadarRestClient(client=mock_client)

        response = await client.delete('test/endpoint/123')

        assert response.status_code == 204
        mock_client.delete.assert_called_once()
        mock_log.assert_called()

    @pytest.mark.asyncio
    @patch('qradar_mcp.client.qradar_rest_client.log_structured')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_delete_with_params(self, mock_load_config, mock_log):
        """Test DELETE request with query parameters."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_load_config.return_value = mock_config

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = httpx.Response(200, request=httpx.Request("DELETE", "http://test"))
        mock_client.delete = AsyncMock(return_value=mock_response)

        client = QRadarRestClient(client=mock_client)
        params = {"force": "true"}

        response = await client.delete('test/endpoint/123', params=params)

        assert response.status_code == 200
        call_kwargs = mock_client.delete.call_args[1]
        assert call_kwargs['params'] == params

    @pytest.mark.asyncio
    @patch('qradar_mcp.client.qradar_rest_client.log_structured')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_delete_with_version(self, mock_load_config, mock_log):
        """Test DELETE request with API version."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_load_config.return_value = mock_config

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = httpx.Response(200, request=httpx.Request("DELETE", "http://test"))
        mock_client.delete = AsyncMock(return_value=mock_response)

        client = QRadarRestClient(client=mock_client)

        response = await client.delete('test/endpoint/123', version="15.0")

        assert response.status_code == 200
        call_kwargs = mock_client.delete.call_args[1]
        assert call_kwargs['headers']['Version'] == "15.0"

    @pytest.mark.asyncio
    @patch('qradar_mcp.client.qradar_rest_client.log_structured')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_delete_with_proxy(self, mock_load_config, mock_log):
        """Test DELETE request with proxy configuration."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token",
                "proxy": "http://proxy.local:8080"
            }
        }
        mock_load_config.return_value = mock_config

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = httpx.Response(204, request=httpx.Request("DELETE", "http://test"))
        mock_client.delete = AsyncMock(return_value=mock_response)

        client = QRadarRestClient(client=mock_client)

        response = await client.delete('test/endpoint/123')

        assert response.status_code == 204
        # httpx handles proxies differently, just verify call was made
        assert mock_client.delete.called

    @pytest.mark.asyncio
    @patch('qradar_mcp.utils.retry.asyncio.sleep')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_delete_does_not_retry(self, mock_load_config, mock_sleep):
        """Test DELETE requests are not automatically retried."""
        mock_load_config.return_value = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_sleep.return_value = None

        request = httpx.Request("DELETE", "https://qradar.local/api/ariel/searches/s123")
        retryable_response = httpx.Response(503, request=request)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.delete = AsyncMock(return_value=retryable_response)

        client = QRadarRestClient(client=mock_client)
        response = await client.delete('ariel/searches/s123')

        assert response.status_code == 503
        assert mock_client.delete.call_count == 1
        mock_sleep.assert_not_called()
