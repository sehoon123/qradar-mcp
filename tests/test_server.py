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
Tests for server.py

Tests the FastMCP server initialization, factory methods, and resource functions.
"""

import pytest
import httpx
from unittest.mock import Mock, patch, MagicMock
from qradar_mcp.server import (
    mcp,
    app,
    qradar_client,
    enforce_mcp_exposure_policy,
    get_health_status,
    get_readiness_status,
)
from qradar_mcp.settings import load_settings
from qradar_mcp.utils.feature_toggle_manager import FeatureToggleManager

class TestMCPServerInitialization:
    """Test FastMCP server initialization."""

    def test_mcp_server_exists(self):
        """Test that MCP server is initialized."""
        assert mcp is not None
        assert hasattr(mcp, 'name')
        assert mcp.name == "qradar-mcp"

    def test_mcp_server_version(self):
        """Test that MCP server has correct version."""
        assert hasattr(mcp, 'version')
        assert mcp.version == "1.0.0"

    def test_app_has_middleware(self):
        """Test that app is created with middleware."""
        assert app is not None
        # App should be an ASGI application
        assert callable(app)

    def test_health_routes_registered(self):
        """Test that liveness and readiness routes are attached."""
        paths = {getattr(route, 'path', None) for route in app.routes}

        assert '/healthz' in paths
        assert '/readyz' in paths

    def test_health_status_payload(self):
        """Test liveness payload is process-local and stable."""
        payload = get_health_status()

        assert payload['status'] == 'ok'
        assert payload['service'] == 'qradar-mcp'
        assert payload['version'] == '1.0.0'
        assert payload['registered_tools'] > 0

    def test_readiness_status_payload(self):
        """Test readiness payload reports initialization checks."""
        payload = get_readiness_status()

        assert payload['status'] in {'ready', 'not_ready'}
        assert payload['service'] == 'qradar-mcp'
        assert 'httpx_client' in payload['checks']
        assert 'qradar_host' in payload['checks']
        assert payload['checks']['registered_tools'] > 0

    @patch.dict('os.environ', {}, clear=True)
    def test_server_bind_defaults_to_localhost(self):
        """Test default bind settings prefer localhost."""
        from qradar_mcp.server import get_server_bind_settings

        host, port = get_server_bind_settings(None)

        assert host == "127.0.0.1"
        assert port == 5000

    def test_remote_bind_requires_mcp_access_token(self):
        """Test remotely bound MCP servers require their own access token."""
        settings = load_settings({
            "server": {
                "host": "0.0.0.0"
            }
        })

        with pytest.raises(SystemExit):
            enforce_mcp_exposure_policy(settings)

    def test_remote_bind_allows_configured_mcp_access_token(self):
        """Test remote bind is allowed when MCP access token is configured."""
        settings = load_settings({
            "server": {
                "host": "0.0.0.0"
            },
            "auth": {
                "mcp_access_token": "0123456789abcdef0123456789abcdef"
            }
        })

        enforce_mcp_exposure_policy(settings)

    @pytest.mark.parametrize("token", [
        "secret",
        "a" * 32,
    ])
    def test_remote_bind_rejects_weak_mcp_access_token(self, token):
        """Test weak and low-diversity tokens do not satisfy remote bind policy."""
        settings = load_settings({
            "server": {
                "host": "0.0.0.0"
            },
            "auth": {
                "mcp_access_token": token
            }
        })

        with pytest.raises(SystemExit):
            enforce_mcp_exposure_policy(settings)

    @pytest.mark.asyncio
    async def test_health_routes_bypass_qradar_auth_in_asgi_stack(self, monkeypatch):
        """Test health routes bypass QRadar auth in the actual ASGI app."""
        async def fail_if_called(*_args, **_kwargs):
            raise AssertionError("QRadar auth must not be called for health routes")

        monkeypatch.setattr(qradar_client, "identify_user", fail_if_called)
        monkeypatch.setattr(qradar_client, "identify_authorized_service", fail_if_called)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            health_response = await client.get("/healthz")
            ready_response = await client.get("/readyz")

        assert health_response.status_code == 200
        assert ready_response.status_code in {200, 503}


class TestResourceRegistration:
    """Test the register_resources function and resource registration logic."""

    @patch('qradar_mcp.server.log_structured')
    @patch('qradar_mcp.server.AQLEventsFieldsResource')
    @patch('qradar_mcp.server.AQLFlowsFieldsResource')
    @patch('qradar_mcp.server.AQLFunctionsResource')
    @patch('qradar_mcp.server.AQLGenerationGuideResource')
    def test_register_resources_with_mixed_toggles(
        self,
        mock_guide_resource,
        mock_functions_resource,
        mock_flows_resource,
        mock_events_resource,
        mock_log_structured
    ):
        """Test that register_resources respects feature toggles."""
        # Create a mock toggle manager with mixed settings
        mock_toggle_manager = Mock(spec=FeatureToggleManager)
        mock_toggle_manager.resource_toggles = {
            'aql_events_fields': True,
            'aql_flows_fields': False,
            'aql_functions': True,
            'aql_generation_guide': False,
            'aql_query_templates': False
        }

        # Mock the resource read methods
        for mock_resource_class in [mock_events_resource, mock_flows_resource,
                                     mock_functions_resource, mock_guide_resource]:
            mock_instance = Mock()
            mock_instance.read.return_value = {"contents": [{"text": "test"}]}
            mock_resource_class.return_value = mock_instance

        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Import and execute register_resources logic
        from qradar_mcp.server import register_resources

        # Patch the toggle_manager and mcp in the server module
        with patch('qradar_mcp.server.toggle_manager', mock_toggle_manager), \
             patch('qradar_mcp.server.mcp', mock_mcp):
            register_resources()

        # Verify log_structured was called with summary
        summary_calls = [
            call for call in mock_log_structured.call_args_list
            if len(call[0]) > 0 and call[0][0] == "Resource Registration Summary"
        ]

        assert len(summary_calls) == 1, "Should log resource registration summary"
        summary_kwargs = summary_calls[0][1]

        assert summary_kwargs['total_resources'] == 5
        assert summary_kwargs['registered_count'] == 2
        assert summary_kwargs['skipped_count'] == 3
        assert 'aql_events_fields' in summary_kwargs['registered']
        assert 'aql_functions' in summary_kwargs['registered']
        assert 'aql_flows_fields' in summary_kwargs['skipped']
        assert 'aql_generation_guide' in summary_kwargs['skipped']
        assert 'aql_query_templates' in summary_kwargs['skipped']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
