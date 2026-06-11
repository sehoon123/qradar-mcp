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

"""MCP tools package.

The package no longer eagerly imports every QRadar endpoint wrapper. Public MCP
registration is driven by ``tools/capability_registry.py`` and class loading is
lazy so disabled or internal endpoint modules are not imported as a side effect
of importing ``qradar_mcp.tools``.
"""

# pylint: disable=undefined-all-variable

from importlib import import_module
from typing import Any

from .base import MCPTool
from .endpoint_registry import ENDPOINT_SPECS
from .schema import schema


def __getattr__(name: str) -> Any:
    """Lazily load tool classes for backwards-compatible package exports."""
    spec = ENDPOINT_SPECS.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(spec.module_path)
    value = getattr(module, spec.class_name)
    globals()[name] = value
    return value


__all__ = [
    "MCPTool",
    "schema",
    *ENDPOINT_SPECS.keys(),
]
