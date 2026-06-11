"""Tests for AQL query templates resource."""

import json

from qradar_mcp.resources.aql_query_templates import AQLQueryTemplatesResource


def test_aql_query_templates_metadata():
    resource = AQLQueryTemplatesResource()
    assert resource.uri == "qradar://aql/templates"
    assert resource.name == "AQL Query Templates"
    assert resource.mime_type == "application/json"


def test_aql_query_templates_content():
    resource = AQLQueryTemplatesResource()
    result = resource.read()
    payload = json.loads(result["contents"][0]["text"])

    assert result["contents"][0]["uri"] == "qradar://aql/templates"
    assert "workflow" in payload
    assert "templates" in payload
    names = {template["name"] for template in payload["templates"]}
    assert "offense_events" in names
    assert "top_source_ips" in names
