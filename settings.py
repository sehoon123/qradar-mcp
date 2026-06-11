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
Typed runtime settings for qradar-mcp.

The project still accepts the existing JSON config shape, but normalizes the
security-sensitive defaults in one place.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"


class QRadarSettings(BaseModel):
    """QRadar connection and API settings."""

    model_config = ConfigDict(extra="allow")

    host: Optional[str] = None
    sec_token: Optional[str] = None
    csrf_token: Optional[str] = None
    authorized_service_token: Optional[str] = None
    app_id: Optional[str] = None
    verify_ssl: bool = True
    api_version: Optional[str] = None
    proxy: Optional[str] = None


class ServerSettings(BaseModel):
    """MCP HTTP server settings."""

    model_config = ConfigDict(extra="allow")

    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = True

    @field_validator("port", mode="before")
    @classmethod
    def _coerce_port(cls, value: Any) -> int:
        """Keep legacy fallback behavior for invalid configured ports."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return 5000


class HttpxSettings(BaseModel):
    """Shared httpx client settings."""

    model_config = ConfigDict(extra="allow")

    max_keepalive_connections: int = 20
    max_connections: int = 100
    timeout: float = 30.0


class AppSettings(BaseModel):
    """Top-level application settings."""

    model_config = ConfigDict(extra="allow")

    qradar: QRadarSettings = Field(default_factory=QRadarSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    httpx: HttpxSettings = Field(default_factory=HttpxSettings)


def parse_bool(value: Any, default: bool) -> bool:
    """Parse common environment-style boolean values."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def load_raw_config(config_path: Path = DEFAULT_CONFIG_PATH) -> Optional[dict]:
    """Load the legacy JSON config file, if present."""
    if not os.path.exists(config_path):
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_settings(config_data: Optional[dict] = None) -> AppSettings:
    """
    Normalize config data into typed settings and apply supported env overrides.

    Env overrides are intentionally limited to deployment/runtime knobs that are
    already documented or security-sensitive.
    """
    settings = AppSettings.model_validate(config_data or {})

    qradar_api_version = os.getenv("QRADAR_API_VERSION")
    if qradar_api_version:
        settings.qradar.api_version = qradar_api_version

    qradar_verify_ssl = os.getenv("QRADAR_VERIFY_SSL")
    if qradar_verify_ssl is not None:
        settings.qradar.verify_ssl = parse_bool(qradar_verify_ssl, settings.qradar.verify_ssl)

    qradar_rest_proxy = os.getenv("QRADAR_REST_PROXY")
    if qradar_rest_proxy:
        settings.qradar.proxy = qradar_rest_proxy

    mcp_host = os.getenv("MCP_HOST")
    if mcp_host:
        settings.server.host = mcp_host

    mcp_port = os.getenv("MCP_PORT")
    if mcp_port:
        try:
            settings.server.port = int(mcp_port)
        except ValueError:
            # server.py logs and falls back for invalid ports.
            pass

    httpx_max_keepalive = os.getenv("MCP_HTTPX_MAX_KEEPALIVE_CONNECTIONS")
    if httpx_max_keepalive:
        settings.httpx.max_keepalive_connections = int(httpx_max_keepalive)

    httpx_max_connections = os.getenv("MCP_HTTPX_MAX_CONNECTIONS")
    if httpx_max_connections:
        settings.httpx.max_connections = int(httpx_max_connections)

    httpx_timeout = os.getenv("MCP_HTTPX_TIMEOUT")
    if httpx_timeout:
        settings.httpx.timeout = float(httpx_timeout)

    return settings
