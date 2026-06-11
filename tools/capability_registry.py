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

"""Public MCP capability metadata.

EndpointSpec remains the internal QRadar REST API catalog. CapabilitySpec is the
small public surface exposed to MCP clients. A capability can depend on one or
more QRadar endpoints and may be backed by an existing endpoint wrapper or a
higher-level workflow tool.
"""

from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional

from qradar_mcp.tools.endpoint_registry import ENDPOINT_SPECS
from qradar_mcp.tools.endpoint_spec import EndpointRef


@dataclass(frozen=True)
class CapabilitySpec:  # pylint: disable=too-many-instance-attributes
    """Static contract for one public MCP capability."""

    tool_name: str
    class_name: str
    group: str
    required_endpoints: tuple[EndpointRef, ...]
    optional_endpoints: tuple[EndpointRef, ...] = field(default_factory=tuple)
    read_only: bool = True
    side_effect: Optional[str] = None
    risk_level: str = "low"
    min_api_version: str = "24.0"
    permission_hint: Optional[str] = None
    module_group: Optional[str] = None
    module_name: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "required_endpoints",
            tuple((method.upper(), path) for method, path in self.required_endpoints),
        )
        object.__setattr__(
            self,
            "optional_endpoints",
            tuple((method.upper(), path) for method, path in self.optional_endpoints),
        )

    @property
    def module_path(self) -> str:
        """Python module path for the capability implementation."""
        group = self.module_group or self.group
        module_name = self.module_name or self.tool_name
        return f"qradar_mcp.tools.{group}.{module_name}"

    @property
    def class_path(self) -> str:
        """Fully qualified class path for dynamic imports."""
        return f"{self.module_path}.{self.class_name}"

    def to_compatibility_entry(self) -> Dict:
        """Convert to the compatibility registry entry shape."""
        entry = {
            "required_endpoints": list(self.required_endpoints),
            "optional_endpoints": list(self.optional_endpoints),
            "min_api_version": self.min_api_version,
            "read_only": self.read_only,
            "group": self.group,
            "tool_name": self.tool_name,
            "risk_level": self.risk_level,
        }
        if self.side_effect:
            entry["side_effect"] = self.side_effect
        if self.permission_hint:
            entry["permission_hint"] = self.permission_hint
        return entry


def _from_endpoint(
    class_name: str,
    *,
    risk_level: str = "low",
    required_endpoints: Optional[tuple[EndpointRef, ...]] = None,
    optional_endpoints: Optional[tuple[EndpointRef, ...]] = None,
) -> CapabilitySpec:
    """Build a public capability from an internal EndpointSpec."""
    endpoint = ENDPOINT_SPECS[class_name]
    return CapabilitySpec(
        tool_name=endpoint.tool_name,
        class_name=endpoint.class_name,
        group=endpoint.group,
        required_endpoints=required_endpoints or endpoint.required_endpoints,
        optional_endpoints=endpoint.optional_endpoints if optional_endpoints is None else optional_endpoints,
        read_only=endpoint.read_only,
        side_effect=endpoint.side_effect,
        risk_level=risk_level,
        min_api_version=endpoint.min_api_version,
        permission_hint=endpoint.permission_hint,
        module_group=endpoint.group,
        module_name=endpoint.tool_name,
    )


CAPABILITY_SPECS: Dict[str, CapabilitySpec] = {
    # Operator diagnostics and API catalog discovery.
    "QradarDoctorTool": _from_endpoint("QradarDoctorTool"),
    "DiscoverQradarEndpointsTool": _from_endpoint("DiscoverQradarEndpointsTool"),

    # SOC offense investigation capabilities. These are intentionally higher
    # level than one QRadar endpoint and hide most Ariel/status/result plumbing
    # from the model.
    "ListOffensesTool": _from_endpoint("ListOffensesTool"),
    "GetOffenseInvestigationContextTool": _from_endpoint("GetOffenseInvestigationContextTool"),
    "InvestigateOffenseEventsTool": _from_endpoint("InvestigateOffenseEventsTool", risk_level="medium"),

    # AQL authoring guard. Kept public because it is non-mutating and useful
    # before operator profiles expose broader Ariel workflows.
    "ValidateAQLTool": _from_endpoint("ValidateAQLTool"),
}


def get_capability_spec(class_name: str) -> Optional[CapabilitySpec]:
    """Return public MCP capability metadata for a tool class name."""
    return CAPABILITY_SPECS.get(class_name)


def compatibility_registry_from_capabilities(base: Optional[Mapping[str, Dict]] = None) -> Dict[str, Dict]:
    """Build compatibility registry entries for public capabilities."""
    registry = dict(base or {})
    for class_name, spec in CAPABILITY_SPECS.items():
        registry[class_name] = spec.to_compatibility_entry()
    return registry
