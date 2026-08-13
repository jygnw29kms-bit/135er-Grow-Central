"""Local write authentication helpers / Lokale Schreibauthentifizierung."""
from __future__ import annotations

import os
import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from app.gui_auth import authenticated


def _candidate_token(x_api_token: str | None, authorization: str | None) -> str:
    if x_api_token:
        return x_api_token.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def require_write_auth(
    request: Request,
    x_api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Allow an authenticated GUI session or an explicitly configured API token.

    Browser writes are already protected by the GUI session established during
    first-boot configuration. Non-browser/API clients can still authenticate
    with X-API-Token or a Bearer token. The dependency remains fail-closed.
    """
    if authenticated(request):
        return
    expected = os.getenv("GC_LOCAL_API_TOKEN", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="local write authentication is not configured",
        )
    candidate = _candidate_token(x_api_token, authorization)
    if not candidate or not secrets.compare_digest(candidate, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid local write token",
            headers={"WWW-Authenticate": "Bearer"},
        )
