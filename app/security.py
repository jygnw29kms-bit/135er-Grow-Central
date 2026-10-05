"""Local write authentication helpers / Lokale Schreibauthentifizierung."""
from __future__ import annotations

import os
from pathlib import Path
import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from app.gui_auth import authenticated

TOKEN_FILE = Path(os.getenv("GC_LOCAL_API_TOKEN_FILE", "/var/lib/135er-grow-central/local-api-token"))
_MIN_TOKEN_LENGTH = 32
_UNSAFE_TOKENS = {"", "test", "changeme", "change_me", "default"}


def _candidate_token(x_api_token: str | None, authorization: str | None) -> str:
    if x_api_token:
        return x_api_token.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def _valid_configured_token(value: str) -> bool:
    token = value.strip()
    return len(token) >= _MIN_TOKEN_LENGTH and token.lower() not in _UNSAFE_TOKENS and not token.upper().startswith("CHANGE_ME")


def _read_token_file() -> str:
    try:
        value = TOKEN_FILE.read_text(encoding="utf-8").strip()
        return value if _valid_configured_token(value) else ""
    except OSError:
        return ""


def _persist_token(value: str) -> bool:
    try:
        TOKEN_FILE.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
        temporary = TOKEN_FILE.with_suffix(".tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, TOKEN_FILE)
        os.chmod(TOKEN_FILE, 0o600)
        return True
    except OSError:
        return False


def configured_api_token() -> str:
    """Return one stable per-device token, generating it when needed.

    Public/test image placeholders such as ``test`` are deliberately ignored.
    A strong explicitly configured token remains supported for development and
    managed deployments. On the appliance the generated token lives only in
    /var/lib and is shared with the local cloud-link process.
    """
    stored = _read_token_file()
    if stored:
        return stored

    configured = os.getenv("GC_LOCAL_API_TOKEN", "").strip()
    if _valid_configured_token(configured):
        _persist_token(configured)
        return configured

    generated = secrets.token_urlsafe(32)
    if _persist_token(generated):
        return generated
    return ""


def api_token_authenticated(request: Request) -> bool:
    expected = configured_api_token()
    if not expected:
        return False
    candidate = _candidate_token(request.headers.get("X-API-Token"), request.headers.get("Authorization"))
    return bool(candidate) and secrets.compare_digest(candidate, expected)


def require_write_auth(
    request: Request,
    x_api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Allow an authenticated GUI session or the per-device local API token.

    Browser writes use the GUI session established during first-boot setup.
    Local service/API clients authenticate with X-API-Token or Bearer. The
    dependency fails closed when no usable per-device token can be established.
    """
    if authenticated(request):
        return
    expected = configured_api_token()
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
