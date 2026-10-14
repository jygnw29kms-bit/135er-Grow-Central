"""Validate the HTTPS origin shared by cloud clients and status probes."""
from urllib.parse import urlparse


def https_origin(value: str) -> str:
    if not value or any(char.isspace() or ord(char) < 32 for char in value):
        raise ValueError("Cloud URL must be a plain HTTPS origin")
    try:
        parsed = urlparse(value)
        port = parsed.port
        valid = (
            parsed.scheme == "https" and parsed.hostname
            and parsed.username is None and parsed.password is None
            and parsed.path in {"", "/"} and not parsed.params
            and not parsed.query and not parsed.fragment
            and (port is None or port > 0)
        )
    except ValueError as exc:
        raise ValueError("Cloud URL must be a plain HTTPS origin") from exc
    if not valid:
        raise ValueError("Cloud URL must be a plain HTTPS origin")
    return value.rstrip("/")
