"""Append-only local audit log for state-changing commands."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def append_audit(event: str, **fields: Any) -> None:
    """Append one JSON line without logging credentials or request headers."""
    path = Path(os.getenv("GC_AUDIT_PATH", "data/audit.jsonl"))
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o640)
    try:
        os.write(fd, (json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8"))
    finally:
        os.close(fd)
