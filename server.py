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
FastMCP Server for QRadar
Uses adapter pattern to wrap existing MCPTool implementations.
"""

import os
import sys
import atexit
import asyncio
from urllib.parse import urlparse
import httpx
from fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.routing import Route
from qradar_mcp.auth_context import AuthTokenMiddleware
from qradar_mcp.utils.mcp_access_auth import MCPAccessTokenMiddleware
from qradar_mcp.utils.qradar_auth import QRadarAuthMiddleware
from qradar_mcp.utils.request_context import RequestContextMiddleware
from qradar_mcp.tools.fastmcp_adapter import register_all_tools
from qradar_mcp.tools.compatibility import set_fail_mode
from qradar_mcp.resources.aql_fields import AQLEventsFieldsResource, AQLFlowsFieldsResource
from qradar_mcp.resources.aql_functions import AQLFunctionsResource
from qradar_mcp.resources.aql_guide import AQLGenerationGuideResource
from qradar_mcp.resources.aql_query_templates import AQLQueryTemplatesResource
from qradar_mcp.settings import load_settings
from qradar_mcp.client.qradar_rest_client import QRadarRestClient, load_config
from qradar_mcp.utils.feature_toggle_manager import (
    FeatureToggleManager,
    FeatureToggleConfigError,
    set_feature_toggle_manager
)
from qradar_mcp.utils.structured_logger import log_structured
from qradar_mcp.utils.mcp_logger import get_mcp_logger

# Initialize MCP logger (works in both standalone and QRadar app mode)
get_mcp_logger()


def initialize_feature_toggles():
    """
    Initialize feature toggle manager and fail if config missing.

    This function loads the feature toggle configuration from feature_toggles.json
    and sets up the global feature toggle manager. If the configuration file is
    missing or invalid, the server will fail to start.

    Returns:
        FeatureToggleManager: The initialized feature toggle manager

    Raises:
        SystemExit: If configuration is missing or invalid
    """
    config_path = os.path.join(
        os.path.dirname(__file__),
        'feature_toggles.json'
    )

    try:
        feature_toggle_mgr = FeatureToggleManager(config_path)
        set_feature_toggle_manager(feature_toggle_mgr)

        # Log feature toggle initialization
        log_structured(
            "Feature toggles initialized successfully",
            level='INFO',
            config_path=config_path
        )

        return feature_toggle_mgr
    except FeatureToggleConfigError as e:
        log_structured(
            f"FATAL: Feature toggle configuration error: {e}",
            level='ERROR',
            config_path=config_path
        )
        sys.exit(1)
    except FileNotFoundError:
        log_structured(
            f"FATAL: Feature toggle configuration file not found: {config_path}",
            level='ERROR',
            config_path=config_path
        )
        sys.exit(1)
    except (OSError, IOError) as e:
        log_structured(
            f"FATAL: Failed to initialize feature toggles: {e}",
            level='ERROR',
            config_path=config_path
        )
        sys.exit(1)


def log_feature_toggle_summary(registered_tool_list: list,
                               skipped_tool_list: list):
    """
    Log feature toggle state summary at startup.

    This function logs a comprehensive summary of tool registration status,
    showing which tools were registered and which were skipped due to
    feature toggles.

    Args:
        registered_tool_list: List of registered MCPTool instances
        skipped_tool_list: List of skipped MCPTool instances
    """
    total_tools = len(registered_tool_list) + len(skipped_tool_list)

    # Log high-level summary
    log_structured(
        "Tool Registration Summary",
        level='INFO',
        total_tools=total_tools,
        registered_count=len(registered_tool_list),
        skipped_count=len(skipped_tool_list)
    )

    # Log registered tools by group
    if registered_tool_list:
        registered_by_group = {}
        for tool in registered_tool_list:
            group = tool.tool_group
            if group not in registered_by_group:
                registered_by_group[group] = []
            registered_by_group[group].append({
                'name': tool.name,
                'verb': tool.http_verb
            })

        log_structured(
            "Registered Tools",
            level='INFO',
            count=len(registered_tool_list),
            by_group=registered_by_group
        )

    # Log skipped tools by group
    if skipped_tool_list:
        skipped_by_group = {}
        for tool in skipped_tool_list:
            group = tool.tool_group
            if group not in skipped_by_group:
                skipped_by_group[group] = []
            skipped_by_group[group].append({
                'name': tool.name,
                'verb': tool.http_verb
            })

        log_structured(
            "Skipped Tools (Not Registered)",
            level='WARNING',
            count=len(skipped_tool_list),
            by_group=skipped_by_group
        )


def cleanup_httpx_client():
    """
    Cleanup function to close the shared httpx client on shutdown.
    Called via atexit handler.
    """
    async def _cleanup():
        await QRadarRestClient.close_shared_client()

    # Run the async cleanup
    try:
        asyncio.run(_cleanup())
    except Exception as e:  # pylint: disable=broad-exception-caught
        try:
            log_structured(
                f"Error during httpx client cleanup: {e}",
                level='ERROR'
            )
        except RuntimeError:
            # Logging may not be initialized in test environment
            pass


# Initialize feature toggles (fail fast if config missing)
toggle_manager = initialize_feature_toggles()

# Initialize FastMCP server
mcp = FastMCP("qradar-mcp", version="1.0.0")

# Load configuration to determine SSL verification and proxy settings
config = load_config()
settings = load_settings(config)
set_fail_mode(settings.compatibility.fail_mode)


def enforce_mcp_exposure_policy(settings_obj):
    """Fail fast when a remotely bound MCP server lacks its own access token."""
    if settings_obj.server.host not in {"0.0.0.0", "::"}:
        return
    if settings_obj.auth.mcp_access_token:
        return

    log_structured(
        "FATAL: MCP server remote bind requires MCP_ACCESS_TOKEN",
        level="ERROR",
        mcp_host=settings_obj.server.host,
        recommendation=(
            "Bind MCP to 127.0.0.1 or set auth.mcp_access_token / "
            "MCP_ACCESS_TOKEN before exposing the server."
        ),
    )
    sys.exit(1)


enforce_mcp_exposure_policy(settings)

# Determine verify and proxy settings
if config:
    # Local development mode - use config.json settings
    VERIFY_SSL = settings.qradar.verify_ssl
    PROXY_URL = settings.qradar.proxy

    MAX_KEEPALIVE = settings.httpx.max_keepalive_connections
    MAX_CONNECTIONS = settings.httpx.max_connections
    TIMEOUT = settings.httpx.timeout
else:
    # QRadar App mode - check environment variables
    IS_FVT_ENV = os.getenv('FUNCTIONAL_TEST_ENV') is not None
    CERT_PATH = os.getenv('REQUESTS_CA_BUNDLE')
    PROXY_URL = settings.qradar.proxy

    if IS_FVT_ENV:
        VERIFY_SSL = False
    elif CERT_PATH:
        VERIFY_SSL = CERT_PATH
    else:
        VERIFY_SSL = settings.qradar.verify_ssl

    MAX_KEEPALIVE = settings.httpx.max_keepalive_connections
    MAX_CONNECTIONS = settings.httpx.max_connections
    TIMEOUT = settings.httpx.timeout

# Initialize shared httpx client for connection pooling with proper SSL and proxy config
httpx_client = httpx.AsyncClient(
    timeout=httpx.Timeout(TIMEOUT),
    limits=httpx.Limits(max_keepalive_connections=MAX_KEEPALIVE, max_connections=MAX_CONNECTIONS),
    verify=VERIFY_SSL,
    proxy=PROXY_URL
)

# Set the shared httpx client for all QRadarRestClient instances
QRadarRestClient.set_shared_client(httpx_client)

log_structured(
    "Shared httpx.AsyncClient initialized for connection pooling",
    level='INFO',
    max_keepalive=MAX_KEEPALIVE,
    max_connections=MAX_CONNECTIONS,
    timeout=TIMEOUT
)

# Register cleanup handler
atexit.register(cleanup_httpx_client)

# Create a single QRadarRestClient instance for all tools
qradar_client = QRadarRestClient()


def log_transport_safety(settings_obj, client_obj):
    """Log startup warnings for high-risk transport combinations."""
    raw_host = getattr(client_obj, "_url", "")  # pylint: disable=protected-access
    if not raw_host:
        return

    parsed = urlparse(raw_host if "://" in str(raw_host) else f"https://{raw_host}")
    if parsed.scheme != "http":
        return

    log_structured(
        "QRadar REST is configured for plain HTTP; SEC tokens can traverse the network without TLS",
        level="WARNING",
        qradar_host=parsed.netloc,
        allow_plain_http_private_network=settings_obj.qradar.allow_plain_http_private_network,
    )

    if settings_obj.server.host in {"0.0.0.0", "::"}:
        log_structured(
            "MCP server is remotely bound while QRadar REST uses plain HTTP",
            level="WARNING",
            mcp_host=settings_obj.server.host,
            qradar_host=parsed.netloc,
            recommendation="Bind MCP to 127.0.0.1 or place it behind TLS/firewall controls.",
        )


log_transport_safety(settings, qradar_client)

# Register enabled MCPTool instances using adapter (filtered by feature toggles)
registered_tools, skipped_tools = register_all_tools(mcp, toggle_manager, qradar_client)

# Log feature toggle state summary after tools are registered
log_feature_toggle_summary(registered_tools, skipped_tools)

def get_health_status():
    """Return process-local liveness status."""
    return {
        "status": "ok",
        "service": "qradar-mcp",
        "version": getattr(mcp, "version", "unknown"),
        "registered_tools": len(registered_tools),
    }


def get_readiness_status():
    """Return initialization readiness without calling the QRadar console."""
    shared_client = QRadarRestClient._shared_client  # pylint: disable=protected-access
    httpx_ready = shared_client is not None and not getattr(shared_client, "is_closed", False)
    qradar_host = getattr(qradar_client, "_url", None)  # pylint: disable=protected-access
    ready = httpx_ready and bool(qradar_host)

    return {
        "status": "ready" if ready else "not_ready",
        "service": "qradar-mcp",
        "checks": {
            "httpx_client": "ok" if httpx_ready else "unavailable",
            "qradar_host": "configured" if qradar_host else "missing",
            "registered_tools": len(registered_tools),
        },
    }


def register_health_routes(asgi_app):
    """Attach lightweight liveness and readiness routes to the ASGI app."""
    async def healthz(_request):
        return JSONResponse(get_health_status())

    async def readyz(_request):
        payload = get_readiness_status()
        status_code = 200 if payload["status"] == "ready" else 503
        return JSONResponse(payload, status_code=status_code)

    existing_paths = {
        getattr(route, "path", None)
        for route in getattr(asgi_app, "routes", [])
    }
    if "/healthz" not in existing_paths:
        asgi_app.routes.append(Route("/healthz", healthz, methods=["GET"]))
    if "/readyz" not in existing_paths:
        asgi_app.routes.append(Route("/readyz", readyz, methods=["GET"]))


# Register resources based on feature toggles
def register_resources():
    """Register MCP resources based on feature toggle configuration."""
    resource_toggles = toggle_manager.resource_toggles
    registered_resources = []
    skipped_resources = []

    # AQL Events Fields Resource
    if resource_toggles.get('aql_events_fields', False):
        @mcp.resource("qradar://aql/events/fields")
        async def aql_events_fields() -> str:
            """AQL Events table field definitions"""
            resource = AQLEventsFieldsResource()
            result = await resource.read()
            return result["contents"][0]["text"]
        registered_resources.append('aql_events_fields')
    else:
        skipped_resources.append('aql_events_fields')

    # AQL Flows Fields Resource
    if resource_toggles.get('aql_flows_fields', False):
        @mcp.resource("qradar://aql/flows/fields")
        async def aql_flows_fields() -> str:
            """AQL Flows table field definitions"""
            resource = AQLFlowsFieldsResource()
            result = await resource.read()
            return result["contents"][0]["text"]
        registered_resources.append('aql_flows_fields')
    else:
        skipped_resources.append('aql_flows_fields')

    # AQL Functions Resource
    if resource_toggles.get('aql_functions', False):
        @mcp.resource("qradar://aql/functions")
        async def aql_functions() -> str:
            """AQL function reference"""
            resource = AQLFunctionsResource()
            result = await resource.read()
            return result["contents"][0]["text"]
        registered_resources.append('aql_functions')
    else:
        skipped_resources.append('aql_functions')

    # AQL Generation Guide Resource
    if resource_toggles.get('aql_generation_guide', False):
        @mcp.resource("qradar://aql/guide")
        async def aql_generation_guide() -> str:
            """AQL query generation guide"""
            resource = AQLGenerationGuideResource()
            result = await resource.read()
            return result["contents"][0]["text"]
        registered_resources.append('aql_generation_guide')
    else:
        skipped_resources.append('aql_generation_guide')

    # AQL Query Templates Resource
    if resource_toggles.get('aql_query_templates', False):
        @mcp.resource("qradar://aql/templates")
        async def aql_query_templates() -> str:
            """AQL query templates"""
            resource = AQLQueryTemplatesResource()
            result = await resource.read()
            return result["contents"][0]["text"]
        registered_resources.append('aql_query_templates')
    else:
        skipped_resources.append('aql_query_templates')

    # Log resource registration summary
    log_structured(
        "Resource Registration Summary",
        level='INFO',
        total_resources=len(registered_resources) + len(skipped_resources),
        registered_count=len(registered_resources),
        skipped_count=len(skipped_resources),
        registered=registered_resources,
        skipped=skipped_resources
    )

register_resources()

# Add auth middleware to FastMCP server only after tools and resources are registered.
# Middleware format: list of tuples (middleware_class, args, kwargs).
# Pass the shared qradar_client instance to maintain connection pooling.
app = mcp.http_app(
    middleware=[
        (RequestContextMiddleware, [], {}),
        (
            MCPAccessTokenMiddleware,
            [],
            {
                'access_token': settings.auth.mcp_access_token,
            },
        ),
        (AuthTokenMiddleware, [], {}),
        (
            QRadarAuthMiddleware,
            [],
            {
                'api_client_factory': lambda: qradar_client,
                'identity_probe': settings.auth.identity_probe,
            },
        ),
    ]
)

register_health_routes(app)


def get_server_bind_settings(config_data):
    """Resolve uvicorn bind host and port from config and environment."""
    resolved_settings = load_settings(config_data)
    server_config = config_data.get('server', {}) if config_data else {}
    host = resolved_settings.server.host
    raw_port = os.getenv('MCP_PORT') or server_config.get('port') or resolved_settings.server.port

    try:
        port = int(raw_port)
    except (TypeError, ValueError):
        log_structured(
            "Invalid MCP server port, falling back to 5000",
            level='WARNING',
            configured_port=raw_port
        )
        port = 5000

    return host, port


if __name__ == "__main__":
    # For local development
    import uvicorn
    SERVER_HOST, SERVER_PORT = get_server_bind_settings(config)
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
