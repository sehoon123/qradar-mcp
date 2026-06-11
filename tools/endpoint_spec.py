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

"""Endpoint metadata shared by tool registration and compatibility gating."""

from dataclasses import dataclass, field
from typing import Dict, Literal, Optional, Tuple

HttpMethod = Literal["GET", "POST", "DELETE", "PATCH", "PUT"]
EndpointRef = Tuple[str, str]


@dataclass(frozen=True)
class EndpointSpec:  # pylint: disable=too-many-instance-attributes
    """Static QRadar API contract for one MCP tool class."""

    tool_name: str
    class_name: str
    group: str
    method: HttpMethod
    path: str
    min_api_version: str = "24.0"
    read_only: bool = True
    side_effect: Optional[str] = None
    deprecated: bool = False
    permission_hint: Optional[str] = None
    additional_required_endpoints: Tuple[EndpointRef, ...] = field(default_factory=tuple)
    optional_endpoints: Tuple[EndpointRef, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", self.method.upper())
        object.__setattr__(
            self,
            "additional_required_endpoints",
            tuple((method.upper(), path) for method, path in self.additional_required_endpoints),
        )
        object.__setattr__(
            self,
            "optional_endpoints",
            tuple((method.upper(), path) for method, path in self.optional_endpoints),
        )

    @property
    def required_endpoints(self) -> Tuple[EndpointRef, ...]:
        """Endpoints that must be exposed by the connected console."""
        return ((self.method, self.path),) + self.additional_required_endpoints

    def to_compatibility_entry(self) -> Dict:
        """Convert to the legacy compatibility registry entry shape."""
        entry = {
            "required_endpoints": list(self.required_endpoints),
            "optional_endpoints": list(self.optional_endpoints),
            "min_api_version": self.min_api_version,
            "read_only": self.read_only,
            "group": self.group,
            "tool_name": self.tool_name,
        }
        if self.side_effect:
            entry["side_effect"] = self.side_effect
        if self.deprecated:
            entry["deprecated"] = True
        if self.permission_hint:
            entry["permission_hint"] = self.permission_hint
        return entry
