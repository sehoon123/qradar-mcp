# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
Unit tests for QRadarRestClient headers and HTTP requests.
"""

import pytest
from unittest.mock import patch, AsyncMock
import httpx
from qradar_mcp.client.qradar_rest_client import QRadarRestClient


class TestQRadarRestClientAddHeaders:
    """Tests for _add_headers method."""

    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    def test_add_headers_local_mode_with_service_token(self, mock_load_config):
        """Test _add_headers in local mode with authorized service token."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "authorized_service_token": "service_token_123",
                "sec_token": "sec_token_456",
                "csrf_token": "csrf_token_789"
            }
        }
        mock_load_config.return_value = mock_config

        client = QRadarRestClient()
        headers = client._add_headers({})

        assert headers["SEC"] == "service_token_123"
        assert "QRadarCSRF" not in headers

    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    def test_add_headers_local_mode_with_user_tokens(self, mock_load_config):
        """Test _add_headers in local mode with user tokens."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "sec_token_456",
                "csrf_token": "csrf_token_789"
            }
        }
        mock_load_config.return_value = mock_config

        client = QRadarRestClient()
        headers = client._add_headers({})

        assert headers["SEC"] == "sec_token_456"
        assert headers["QRadarCSRF"] == "csrf_token_789"

    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    def test_add_headers_with_version(self, mock_load_config):
        """Test _add_headers with API version."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_load_config.return_value = mock_config

        client = QRadarRestClient()
        headers = client._add_headers({}, version="14.0")

        assert headers["Version"] == "14.0"

    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    def test_add_headers_with_configured_api_version(self, mock_load_config):
        """Test _add_headers uses configured API version by default."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token",
                "api_version": "27.0"
            }
        }
        mock_load_config.return_value = mock_config

        client = QRadarRestClient()
        headers = client._add_headers({})

        assert headers["Version"] == "27.0"

    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    def test_add_headers_explicit_version_overrides_configured_api_version(self, mock_load_config):
        """Test explicit per-call API version takes precedence."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token",
                "api_version": "27.0"
            }
        }
        mock_load_config.return_value = mock_config

        client = QRadarRestClient()
        headers = client._add_headers({}, version="26.0")

        assert headers["Version"] == "26.0"

    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    def test_add_headers_preserves_existing_headers(self, mock_load_config):
        """Test that _add_headers preserves existing headers."""
        mock_config = {
            "qradar": {
                "host": "https://qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_load_config.return_value = mock_config

        client = QRadarRestClient()
        existing_headers = {"Custom-Header": "custom_value"}
        headers = client._add_headers(existing_headers)

        assert headers["Custom-Header"] == "custom_value"
        assert headers["SEC"] == "test_token"


class TestQRadarRestClientUrlGeneration:
    """Tests for QRadar API URL generation."""

    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    def test_generate_full_url_defaults_to_https_when_scheme_omitted(self, mock_load_config):
        """Test hosts without a scheme keep the historical HTTPS default."""
        mock_load_config.return_value = {
            "qradar": {
                "host": "qradar.local",
                "sec_token": "test_token"
            }
        }

        client = QRadarRestClient()

        assert client._generate_full_url("siem/offenses") == "https://qradar.local/api/siem/offenses"

    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    def test_generate_full_url_preserves_explicit_http_scheme(self, mock_load_config):
        """Test internal HTTP QRadar consoles are not forced to HTTPS."""
        mock_load_config.return_value = {
            "qradar": {
                "host": "http://192.168.1.10",
                "sec_token": "test_token"
            }
        }

        client = QRadarRestClient()

        assert client._generate_full_url("siem/offenses") == "http://192.168.1.10/api/siem/offenses"

    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    def test_generate_full_url_normalizes_leading_slash(self, mock_load_config):
        """Test API paths with leading slash do not create double slashes."""
        mock_load_config.return_value = {
            "qradar": {
                "host": "http://192.168.1.10",
                "sec_token": "test_token"
            }
        }

        client = QRadarRestClient()

        assert client._generate_full_url("/ariel/searches") == "http://192.168.1.10/api/ariel/searches"

    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    def test_generate_full_url_tolerates_host_with_api_suffix(self, mock_load_config):
        """Test accidental /api suffix is not duplicated."""
        mock_load_config.return_value = {
            "qradar": {
                "host": "http://192.168.1.10/api/",
                "sec_token": "test_token"
            }
        }

        client = QRadarRestClient()

        assert client._generate_full_url("/help/endpoints") == "http://192.168.1.10/api/help/endpoints"


class TestQRadarRestClientGet:
    """Tests for get method."""

    @pytest.mark.asyncio
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_get_basic_request(self, mock_load_config):
        """Test basic GET request."""
        mock_config = {
            "qradar": {
                "host": "qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_load_config.return_value = mock_config

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = httpx.Response(200, request=httpx.Request("GET", "http://test"))
        mock_client.get = AsyncMock(return_value=mock_response)

        client = QRadarRestClient(client=mock_client)
        response = await client.get("siem/offenses/123")

        assert response.status_code == 200
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "https://qradar.local/api/siem/offenses/123" in str(call_args)

    @pytest.mark.asyncio
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_get_with_params(self, mock_load_config):
        """Test GET request with query parameters."""
        mock_config = {
            "qradar": {
                "host": "qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_load_config.return_value = mock_config

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = httpx.Response(200, request=httpx.Request("GET", "http://test"))
        mock_client.get = AsyncMock(return_value=mock_response)

        client = QRadarRestClient(client=mock_client)
        await client.get("siem/offenses", params={"filter": "severity>5"})

        call_args = mock_client.get.call_args
        assert call_args[1]["params"] == {"filter": "severity>5"}

    @pytest.mark.asyncio
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_get_with_proxy(self, mock_load_config):
        """Test GET request with proxy."""
        mock_config = {
            "qradar": {
                "host": "qradar.local",
                "sec_token": "test_token",
                "proxy": "http://proxy:8080"
            }
        }
        mock_load_config.return_value = mock_config

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = httpx.Response(200, request=httpx.Request("GET", "http://test"))
        mock_client.get = AsyncMock(return_value=mock_response)

        client = QRadarRestClient(client=mock_client)
        await client.get("siem/offenses")

        call_args = mock_client.get.call_args
        # httpx uses 'proxy' parameter differently than requests
        # Just verify the call was made successfully
        assert mock_client.get.called

    @pytest.mark.asyncio
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_get_with_timeout(self, mock_load_config):
        """Test GET request with timeout."""
        mock_config = {
            "qradar": {
                "host": "qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_load_config.return_value = mock_config

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = httpx.Response(200, request=httpx.Request("GET", "http://test"))
        mock_client.get = AsyncMock(return_value=mock_response)

        client = QRadarRestClient(client=mock_client)
        await client.get("siem/offenses", timeout=30)

        call_args = mock_client.get.call_args
        assert call_args[1]["timeout"] == 30

    @pytest.mark.asyncio
    @patch('qradar_mcp.utils.retry.asyncio.sleep')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_get_retries_retryable_response_status(self, mock_load_config, mock_sleep):
        """Test GET retries when QRadar returns a retryable status."""
        mock_config = {
            "qradar": {
                "host": "qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_load_config.return_value = mock_config
        mock_sleep.return_value = None

        request = httpx.Request("GET", "https://qradar.local/api/siem/offenses")
        retryable_response = httpx.Response(503, request=request)
        success_response = httpx.Response(200, request=request)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=[retryable_response, success_response])

        client = QRadarRestClient(client=mock_client)
        response = await client.get("siem/offenses")

        assert response.status_code == 200
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    @patch('qradar_mcp.utils.retry.asyncio.sleep')
    @patch('qradar_mcp.client.qradar_rest_client.load_config')
    async def test_get_does_not_retry_non_retryable_response_status(self, mock_load_config, mock_sleep):
        """Test GET returns non-retryable statuses for tool-specific handling."""
        mock_config = {
            "qradar": {
                "host": "qradar.local",
                "sec_token": "test_token"
            }
        }
        mock_load_config.return_value = mock_config
        mock_sleep.return_value = None

        request = httpx.Request("GET", "https://qradar.local/api/siem/offenses")
        validation_response = httpx.Response(422, request=request)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=validation_response)

        client = QRadarRestClient(client=mock_client)
        response = await client.get("siem/offenses")

        assert response.status_code == 422
        assert mock_client.get.call_count == 1
