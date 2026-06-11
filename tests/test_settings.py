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

"""Tests for typed application settings."""

from unittest.mock import patch

from qradar_mcp.settings import load_settings, parse_bool


def test_load_settings_secure_defaults():
    """Test security-sensitive defaults."""
    settings = load_settings(None)

    assert settings.qradar.verify_ssl is True
    assert settings.qradar.allow_plain_http_private_network is False
    assert settings.qradar.api_version is None
    assert settings.server.host == "127.0.0.1"
    assert settings.server.port == 5000


def test_load_settings_reads_qradar_api_version():
    """Test api_version is parsed from config."""
    settings = load_settings({
        "qradar": {
            "host": "qradar.local",
            "api_version": "27.0"
        }
    })

    assert settings.qradar.api_version == "27.0"


def test_load_settings_invalid_server_port_falls_back():
    """Test invalid configured port preserves legacy fallback."""
    settings = load_settings({
        "server": {
            "port": "invalid"
        }
    })

    assert settings.server.port == 5000


@patch.dict(
    "os.environ",
    {
        "QRADAR_API_VERSION": "26.0",
        "QRADAR_HOST": "http://192.168.1.10",
        "QRADAR_VERIFY_SSL": "false",
        "QRADAR_ALLOW_PLAIN_HTTP_PRIVATE_NETWORK": "true",
    },
    clear=True
)
def test_load_settings_env_overrides_qradar_runtime_options():
    """Test supported env overrides are applied."""
    settings = load_settings({
        "qradar": {
            "host": "qradar.local",
            "api_version": "27.0",
            "verify_ssl": True
        }
    })

    assert settings.qradar.host == "http://192.168.1.10"
    assert settings.qradar.api_version == "26.0"
    assert settings.qradar.verify_ssl is False
    assert settings.qradar.allow_plain_http_private_network is True


def test_parse_bool_handles_common_values():
    """Test boolean parser for env-style inputs."""
    assert parse_bool("true", False) is True
    assert parse_bool("0", True) is False
    assert parse_bool("unexpected", True) is True
