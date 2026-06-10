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
Safety checks for the read-only POST allowlist and the new read-only tools.

These tests guard the safety contract for the read-only fork:
  * Only the explicitly allowlisted, non-mutating POST tools (Ariel search
    creation / validation) may run while read_only_mode is enabled.
  * Mutating Ariel tools (DELETE) must stay disabled.
  * Every newly added data_classification / config tool is GET-only.
"""

import ast
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Tools added for the read-only expansion. All must be GET-only.
NEW_READ_ONLY_TOOLS = [
    "data_classification/list_qid_records.py",
    "data_classification/get_qid_record.py",
    "data_classification/list_dsm_event_mappings.py",
    "data_classification/list_low_level_categories.py",
    "data_classification/list_high_level_categories.py",
    "config/list_network_hierarchy.py",
    "config/list_domains.py",
    "config/list_regex_properties.py",
    "config/list_calculated_properties.py",
    "health_data/get_security_data_count.py",
    "health_data/list_top_offenses.py",
    "health_data/list_top_rules.py",
    "help/discover_qradar_endpoints.py",
    "ariel/list_ariel_databases.py",
    "ariel/list_ariel_functions.py",
    "ariel/get_ariel_parser_keywords.py",
    "ariel/get_ariel_database_columns.py",
    "ariel/list_ariel_lookups.py",
    "ariel/get_ariel_lookup.py",
]

FORBIDDEN_CLIENT_METHODS = {"post", "put", "patch", "delete"}


def _forbidden_calls(tool_relpath):
    tool_path = REPO_ROOT / "tools" / tool_relpath
    tree = ast.parse(tool_path.read_text(encoding="utf-8"))
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr in FORBIDDEN_CLIENT_METHODS:
            calls.append((node.func.attr, node.lineno))
    return calls


def test_new_tools_only_call_get():
    for relpath in NEW_READ_ONLY_TOOLS:
        assert _forbidden_calls(relpath) == [], f"{relpath} performs a non-GET client call"


def test_new_tools_declare_get_verb():
    for relpath in NEW_READ_ONLY_TOOLS:
        source = (REPO_ROOT / "tools" / relpath).read_text(encoding="utf-8")
        assert 'return "GET"' in source, f"{relpath} does not declare http_verb GET"


def test_allowlist_contains_only_read_only_posts():
    config = json.loads((REPO_ROOT / "feature_toggles.json").read_text(encoding="utf-8"))
    allowlist = config.get("read_only_post_allowlist", [])

    # The non-mutating Ariel POST tools must be allowlisted.
    assert "CreateArielSearchTool" in allowlist
    assert "ValidateAQLTool" in allowlist

    # Mutating (DELETE) tools must never be allowlisted.
    assert "DeleteArielSearchTool" not in allowlist
    assert "DeleteSavedSearchTool" not in allowlist

    # POST verb toggle stays off; the allowlist is the only escape hatch.
    assert config["read_only_mode"] is True
    assert config["verb_toggles"]["POST"] is False
    assert config["verb_toggles"]["DELETE"] is False

    # Groups the new tools live in must be enabled.
    assert config["group_toggles"]["ariel"] is True
    assert config["group_toggles"]["data_classification"] is True
    assert config["group_toggles"]["health_data"] is True
    assert config["group_toggles"]["help"] is True


def _fake_tool(class_name, verb, group):
    """Build a duck-typed tool whose class name matches the allowlist key."""
    cls = type(class_name, (), {
        "http_verb": property(lambda self: verb),
        "tool_group": property(lambda self: group),
    })
    return cls()


def test_manager_enforces_allowlist(tmp_path):
    # Imported lazily so the AST/JSON tests above can run even when the full
    # qradar_mcp dependency stack is unavailable.
    from qradar_mcp.utils.feature_toggle_manager import FeatureToggleManager

    config = {
        "read_only_mode": True,
        "verb_toggles": {"GET": True, "POST": False, "DELETE": False},
        "group_toggles": {"ariel": True, "offense": True, "reference_data": True},
        "per_tool_toggles": {},
        "read_only_post_allowlist": ["CreateArielSearchTool", "ValidateAQLTool"],
    }
    config_path = tmp_path / "feature_toggles.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    manager = FeatureToggleManager(config_path=str(config_path))

    # Allowlisted, non-mutating POST tools -> enabled (group must be on).
    assert manager.is_tool_enabled(_fake_tool("CreateArielSearchTool", "POST", "ariel")) is True
    assert manager.is_tool_enabled(_fake_tool("ValidateAQLTool", "POST", "ariel")) is True

    # Mutating Ariel tool (DELETE) -> blocked even though group is enabled.
    assert manager.is_tool_enabled(_fake_tool("DeleteArielSearchTool", "DELETE", "ariel")) is False

    # Non-allowlisted POST tool -> blocked.
    assert manager.is_tool_enabled(_fake_tool("CreateReferenceSetTool", "POST", "reference_data")) is False

    # Allowlisted POST tool whose group is disabled -> blocked.
    assert manager.is_tool_enabled(_fake_tool("CreateArielSearchTool", "POST", "system")) is False

    # Ordinary GET tool -> unaffected.
    assert manager.is_tool_enabled(_fake_tool("ListOffensesTool", "GET", "offense")) is True
