# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""MCP endpoint access control middleware."""

from secrets import compare_digest
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


PUBLIC_MCP_AUTH_BYPASS_PATHS = {"/healthz", "/readyz"}


class MCPAccessTokenMiddleware(BaseHTTPMiddleware):
    """Require an MCP access token when one is configured."""

    def __init__(self, app, access_token: Optional[str] = None):
        super().__init__(app)
        self.access_token = str(access_token or "").strip()

    async def dispatch(self, request: Request, call_next):
        """Validate X-MCP-Token or Authorization: Bearer before MCP handling."""
        if request.url.path in PUBLIC_MCP_AUTH_BYPASS_PATHS or not self.access_token:
            return await call_next(request)

        provided = self._extract_token(request)
        if provided and compare_digest(provided, self.access_token):
            return await call_next(request)

        return JSONResponse(
            status_code=401,
            content={
                "code": "MCP_UNAUTHENTICATED",
                "message": "MCP access token is required.",
            },
        )

    @staticmethod
    def _extract_token(request: Request) -> Optional[str]:
        """Extract access token from supported headers."""
        explicit = request.headers.get("X-MCP-Token")
        if explicit:
            return explicit.strip()

        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            return token.strip()

        return None
