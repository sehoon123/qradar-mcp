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
QRadar Authentication Middleware

Provides BaseHTTPMiddleware implementation for QRadar authentication that stores
authentication context in ContextVars, enabling access across async boundaries.
"""

from contextvars import ContextVar
import hashlib
import time
from typing import Optional, Dict, Any, Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from .mcp_logger import log_mcp

PUBLIC_AUTH_BYPASS_PATHS = {"/healthz", "/readyz"}
AUTH_CACHE_TTL_SECONDS = 60.0


# Context variables to store authentication information for the current request
_user_id: ContextVar[Optional[int]] = ContextVar('user_id', default=None)
_username: ContextVar[Optional[str]] = ContextVar('username', default=None)
_service_id: ContextVar[Optional[int]] = ContextVar('service_id', default=None)
_service_label: ContextVar[Optional[str]] = ContextVar('service_label', default=None)
_is_service: ContextVar[bool] = ContextVar('is_service', default=False)


def get_user_id() -> Optional[int]:
    """
    Get the authenticated user ID from the current request context.

    Returns:
        User ID or None if not authenticated as a user
    """
    return _user_id.get()


def get_username() -> Optional[str]:
    """
    Get the authenticated username from the current request context.

    Returns:
        Username or None if not authenticated as a user
    """
    return _username.get()


def get_service_id() -> Optional[int]:
    """
    Get the authenticated service ID from the current request context.

    Returns:
        Service ID or None if not authenticated as a service
    """
    return _service_id.get()


def get_service_label() -> Optional[str]:
    """
    Get the authenticated service label from the current request context.

    Returns:
        Service label or None if not authenticated as a service
    """
    return _service_label.get()


def is_service_auth() -> bool:
    """
    Check if the current request is authenticated as a service.

    Returns:
        True if authenticated as a service, False otherwise
    """
    return _is_service.get()


def get_auth_context() -> Dict[str, Any]:
    """
    Get all authentication context information.

    Returns:
        Dictionary containing all authentication context variables
    """
    return {
        'user_id': get_user_id(),
        'username': get_username(),
        'service_id': get_service_id(),
        'service_label': get_service_label(),
        'is_service': is_service_auth()
    }


def set_user_auth(user_id: int, username: str) -> None:
    """
    Set user authentication context.

    Args:
        user_id: The authenticated user's ID
        username: The authenticated user's username
    """
    _user_id.set(user_id)
    _username.set(username)
    _service_id.set(None)
    _service_label.set(None)
    _is_service.set(False)


def set_service_auth(service_id: int, service_label: str) -> None:
    """
    Set service authentication context.

    Args:
        service_id: The authenticated service's ID
        service_label: The authenticated service's label
    """
    _user_id.set(None)
    _username.set(None)
    _service_id.set(service_id)
    _service_label.set(service_label)
    _is_service.set(True)


def clear_auth_context() -> None:
    """Clear all authentication context variables."""
    _user_id.set(None)
    _username.set(None)
    _service_id.set(None)
    _service_label.set(None)
    _is_service.set(False)


class QRadarAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to authenticate requests with QRadar and store auth context.

    This middleware:
    - Authenticates incoming requests as either a QRadar user or authorized service
    - Sets authentication context variables that work across async boundaries
    - Returns 401 if authentication fails

    For users:
    - Sets user_id, username, and is_service=False

    For authorized services:
    - Sets service_id, service_label, and is_service=True

    Authentication priority:
    1. User authentication (via SEC + CSRF tokens)
    2. Service authentication (via SEC token only)
    """

    def __init__(self, app, api_client_factory: Callable, identity_probe: str = "strict"):
        """
        Initialize the authentication middleware.

        Args:
            app: The ASGI application
            api_client_factory: Callable that returns a QRadarRestClient instance
        """
        super().__init__(app)
        self.api_client_factory = api_client_factory
        self._auth_cache: Dict[str, Dict[str, Any]] = {}
        self.identity_probe = self._normalize_identity_probe(identity_probe)

    async def dispatch(self, request: Request, call_next):
        """
        Authenticate the request and set auth context before processing.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            Response from the handler or 401 error if authentication fails
        """
        if request.url.path in PUBLIC_AUTH_BYPASS_PATHS:
            return await call_next(request)

        # Get API client instance
        api_client = self.api_client_factory()
        cache_key = self._auth_cache_key(request, api_client)

        token_parts = self._request_token_parts(request)
        if not token_parts:
            local_mode_auth = getattr(api_client, '_local_mode_auth', None)
            if callable(local_mode_auth):
                local_tokens = local_mode_auth()
                if isinstance(local_tokens, dict):
                    token_parts = local_tokens

        if self.identity_probe == "disabled_for_local_config" and self._has_local_config_token(api_client, token_parts):
            identity = {
                "type": "service",
                "id": -1,
                "label": "local_config_identity_probe_disabled",
                "identity_unknown": True,
            }
            return await self._call_with_identity(identity, request, call_next)

        cached_identity = self._get_cached_identity(cache_key)
        if cached_identity:
            return await self._call_with_identity(cached_identity, request, call_next)

        # First, try to authenticate as a user
        user_id, username = await api_client.identify_user()
        if username and user_id:
            identity = {
                "type": "user",
                "id": user_id,
                "label": username,
            }
            self._set_cached_identity(cache_key, identity)
            log_mcp(f"Authenticated as user: {username} (ID: {user_id})", level='DEBUG')
            return await self._call_with_identity(identity, request, call_next)

        # If user authentication fails, try authorized service authentication
        service_id, service_label = await api_client.identify_authorized_service()
        if service_label and service_id:
            identity = {
                "type": "service",
                "id": service_id,
                "label": service_label,
            }
            self._set_cached_identity(cache_key, identity)
            log_mcp(f"Authenticated as service: {service_label} (ID: {service_id})", level='DEBUG')
            return await self._call_with_identity(identity, request, call_next)

        if self.identity_probe == "permissive" and token_parts:
            identity = {
                "type": "service",
                "id": -1,
                "label": "identity_probe_failed",
                "identity_unknown": True,
            }
            self._set_cached_identity(cache_key, identity)
            log_mcp("QRadar identity probe failed; proceeding in permissive mode", level='WARNING')
            return await self._call_with_identity(identity, request, call_next)

        # If both authentication methods fail, return 401
        log_mcp("Authentication failed for both user and service", level='ERROR')
        return JSONResponse(
            status_code=401,
            content={
                'code': 'UNAUTHENTICATED',
                'message': 'User is not authenticated. Failing request.'
            }
        )

    async def _call_with_identity(self, identity: Dict[str, Any], request: Request, call_next):
        """Set auth context from an identity and continue the request."""
        if identity["type"] == "user":
            set_user_auth(identity["id"], identity["label"])
        else:
            set_service_auth(identity["id"], identity["label"])

        try:
            response = await call_next(request)
            return response
        finally:
            clear_auth_context()

    def _get_cached_identity(self, cache_key: Optional[str]) -> Optional[Dict[str, Any]]:
        """Return a cached identity if present and unexpired."""
        if not cache_key:
            return None

        entry = self._auth_cache.get(cache_key)
        if not entry:
            return None

        if entry["expires_at"] <= time.monotonic():
            self._auth_cache.pop(cache_key, None)
            return None

        return entry["identity"]

    def _set_cached_identity(self, cache_key: Optional[str], identity: Dict[str, Any]) -> None:
        """Cache an identity without storing raw QRadar tokens."""
        if not cache_key:
            return

        self._auth_cache[cache_key] = {
            "identity": identity,
            "expires_at": time.monotonic() + AUTH_CACHE_TTL_SECONDS,
        }

    @staticmethod
    def _auth_cache_key(request: Request, api_client) -> Optional[str]:
        """Build a token fingerprint for auth cache lookup."""
        token_parts = QRadarAuthMiddleware._request_token_parts(request)
        local_mode_auth = getattr(api_client, '_local_mode_auth', None)
        if not token_parts and callable(local_mode_auth):
            local_token_parts = local_mode_auth()
            if isinstance(local_token_parts, dict):
                token_parts = local_token_parts
        if not token_parts:
            return None

        fingerprint_source = '|'.join(
            f"{key}={token_parts[key]}"
            for key in sorted(token_parts)
            if token_parts[key]
        )
        if not fingerprint_source:
            return None

        return hashlib.sha256(fingerprint_source.encode('utf-8')).hexdigest()

    @staticmethod
    def _normalize_identity_probe(identity_probe: str) -> str:
        """Normalize and validate identity probe mode."""
        normalized = str(identity_probe or "strict").strip().lower()
        if normalized not in {"strict", "permissive", "disabled_for_local_config"}:
            return "strict"
        return normalized

    @staticmethod
    def _has_local_config_token(api_client, token_parts: Dict[str, str]) -> bool:
        """Return True when the client is using local config auth tokens."""
        return bool(getattr(api_client, '_local_mode', False) and token_parts)

    @staticmethod
    def _request_token_parts(request: Request) -> Dict[str, str]:
        """Extract auth token values from request state or headers."""
        state_tokens = getattr(request.state, 'auth_tokens', None)
        token_parts = dict(state_tokens or {})

        if 'SEC' in request.headers and 'sec_token' not in token_parts:
            token_parts['sec_token'] = request.headers['SEC']
        if 'QRadarCSRF' in request.headers and 'csrf_token' not in token_parts:
            token_parts['csrf_token'] = request.headers['QRadarCSRF']

        return token_parts
