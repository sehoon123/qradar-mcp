"""Safety checks for composite read-only tools."""

import ast
import json
from pathlib import Path


def test_offense_investigation_context_only_calls_get():
    tool_path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "composite"
        / "get_offense_investigation_context.py"
    )
    tree = ast.parse(tool_path.read_text(encoding="utf-8"))

    forbidden_client_methods = {"post", "put", "patch", "delete"}
    forbidden_calls = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr in forbidden_client_methods:
            forbidden_calls.append((node.func.attr, node.lineno))

    assert forbidden_calls == []


def test_offense_investigation_context_declares_get():
    tool_path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "composite"
        / "get_offense_investigation_context.py"
    )
    source = tool_path.read_text(encoding="utf-8")

    assert 'return "GET"' in source
    assert 'http_methods_used": ["GET"]' in source


def test_read_only_mode_is_enabled():
    config_path = Path(__file__).resolve().parents[1] / "feature_toggles.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert config["read_only_mode"] is True
    assert config["verb_toggles"]["GET"] is True
    assert config["verb_toggles"]["POST"] is False
    assert config["verb_toggles"]["DELETE"] is False
