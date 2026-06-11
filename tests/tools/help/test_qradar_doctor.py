"""Tests for qradar_doctor diagnostics."""

import pytest

import qradar_mcp.tools.compatibility as compat
from qradar_mcp.tools.help.qradar_doctor import QradarDoctorTool
from qradar_mcp.utils.feature_toggle_manager import set_feature_toggle_manager


class _Resp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


class _DoctorClient:
    _url = "http://192.168.1.10"
    _api_version = "27.0"
    _allow_plain_http_private_network = True

    def __init__(self, fail_help=False):
        self.fail_help = fail_help

    async def get(self, api_path, headers=None, **_kwargs):
        if self.fail_help:
            raise RuntimeError("help unavailable")
        if api_path == "/help/versions":
            return _Resp([{"version": "26.0"}, {"version": "27.0"}])
        if api_path == "/help/endpoints":
            return _Resp([
                {"http_method": "GET", "path": "/help/versions"},
                {"http_method": "GET", "path": "/help/endpoints"},
            ])
        raise AssertionError(api_path)

    async def identify_user(self):
        return -1, ""

    async def identify_authorized_service(self):
        return 7, "mcp-readonly"


@pytest.fixture(autouse=True)
def reset_state():
    compat.reset_catalog()
    compat.set_fail_mode("open")
    set_feature_toggle_manager(None)
    yield
    compat.reset_catalog()
    compat.set_fail_mode("open")
    set_feature_toggle_manager(None)


@pytest.mark.asyncio
async def test_qradar_doctor_reports_internal_http_and_catalog():
    """Test doctor returns structured diagnostics for an internal HTTP console."""
    tool = QradarDoctorTool()
    tool.client = _DoctorClient()

    result = await tool.execute({})

    assert "isError" not in result
    assert result["content"][0]["type"] == "json"
    report = result["content"][0]["json"]
    assert report["qradar_host"]["scheme"] == "http"
    assert report["qradar_host"]["private_or_internal"] is True
    assert report["qradar_host"]["risk"] == "token_sent_without_tls"
    assert report["api"]["configured_version"] == "27.0"
    assert report["api"]["console_max_version"] == "27.0"
    assert report["auth"]["identity_type"] == "authorized_service"
    assert report["compatibility"]["catalog_available"] is True
    assert report["compatibility"]["endpoint_count"] == 2


@pytest.mark.asyncio
async def test_qradar_doctor_reports_help_catalog_failure():
    """Test doctor keeps running when /help catalog is unavailable."""
    tool = QradarDoctorTool()
    tool.client = _DoctorClient(fail_help=True)

    result = await tool.execute({})

    assert "isError" not in result
    report = result["content"][0]["json"]
    assert report["api"]["versions_available"] is False
    assert report["compatibility"]["catalog_available"] is False
    assert any("/help/versions" in item for item in report["recommendations"])
