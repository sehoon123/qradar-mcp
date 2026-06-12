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
Tests for basic parameter builder functions.
"""

import httpx

from qradar_mcp.utils.parameters import (
    build_filter_param,
    build_sort_param,
    build_range_header,
    build_fields_param
)


class TestBuildFilterParam:
    """Tests for build_filter_param function."""

    def test_with_filter(self):
        """Test building filter parameter with expression."""
        result = build_filter_param("status='OPEN'")
        assert result == {"filter": "status%3D%27OPEN%27"}

    def test_filter_is_double_encoded_by_httpx_params(self):
        """Test pre-encoded filter becomes double encoded on the wire."""
        params = build_filter_param("status='OPEN' and severity > 7")
        request = httpx.Request("GET", "https://qradar.local/api/siem/offenses", params=params)

        assert "filter=status%253D%2527OPEN%2527%2520and%2520severity%2520%253E%25207" in str(request.url)

    def test_without_filter(self):
        """Test building filter parameter without expression."""
        result = build_filter_param(None)
        assert result == {}

    def test_empty_filter(self):
        """Test building filter parameter with empty string."""
        result = build_filter_param("")
        assert result == {}


class TestBuildSortParam:
    """Tests for build_sort_param function."""

    def test_single_field(self):
        """Test sorting by single field."""
        result = build_sort_param(["+severity"])
        assert result == {"sort": "%2Bseverity"}

    def test_multiple_fields(self):
        """Test sorting by multiple fields."""
        result = build_sort_param(["+severity", "-start_time"])
        assert result == {"sort": "%2Bseverity%2C-start_time"}

    def test_no_fields(self):
        """Test with no sort fields."""
        result = build_sort_param(None)
        assert result == {}

    def test_empty_list(self):
        """Test with empty list."""
        result = build_sort_param([])
        assert result == {}


class TestBuildRangeHeader:
    """Tests for build_range_header function."""

    def test_with_range(self):
        """Test building range header."""
        result = build_range_header(0, 49)
        assert result == {"Range": "items=0-49"}

    def test_different_range(self):
        """Test building range header with different values."""
        result = build_range_header(50, 99)
        assert result == {"Range": "items=50-99"}

    def test_without_range(self):
        """Test without range parameters."""
        result = build_range_header()
        assert result == {}

    def test_partial_range(self):
        """Test with only start parameter."""
        result = build_range_header(start=0)
        assert result == {}


class TestBuildFieldsParam:
    """Tests for build_fields_param function."""

    def test_single_field(self):
        """Test with single field."""
        result = build_fields_param(["id"])
        assert result == {"fields": "id"}

    def test_multiple_fields(self):
        """Test with multiple fields."""
        result = build_fields_param(["id", "description", "severity"])
        assert result == {"fields": "id,description,severity"}

    def test_no_fields(self):
        """Test with no fields."""
        result = build_fields_param(None)
        assert result == {}

    def test_empty_list(self):
        """Test with empty list."""
        result = build_fields_param([])
        assert result == {}
