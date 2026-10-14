# App review and source verification · 9 October 2026

The review covers Grow Central's local Python app, shared desktop/mobile runtime status, Cloud API, Cloud Link V2, existing tests, roadmap and source registers. It is not an exhaustive device-protocol audit or hardware certification.

**Implemented:** Shared heartbeat interpretation detects expired, invalid, missing or future timestamps and server changes. Status endpoints expose `state`, `stale`, `updated_at` and `age_seconds`. Disabled Cloud is reported as disabled; stale Cloud produces a warning without blocking local operation. The freshness window allows for configured sync intervals, diagnostics and bundle uploads.

**Implemented:** Cloud service checks run off the async event loop and tolerate missing systemd or timeouts. Health probing checks Grow Central's service identity and remains advisory. A shared HTTPS-origin validator rejects credentials, paths, query strings, fragments, invalid ports and whitespace/control characters. Invalid URLs are not probed or returned. This validates URL structure; it is not a DNS-based SSRF filter.

**Implemented:** Cloud Link V2 resets its connection state after incompatible health responses or telemetry HTTP 404, repeating the diagnostic handshake on recovery. The roadmap now references canonical Candidate Build 351 instead of Build 118. No new image release is claimed.

Primary sources were retrieved from official repositories on 9 October 2026; documentation domains were blocked by network policy:

- [CPython 3.12 asyncio](https://github.com/python/cpython/blob/58ed60b7415e218ce3d608302e39b5e55bfb0e88/Doc/library/asyncio-task.rst): blocking I/O and `asyncio.to_thread`.
- [CPython URL parsing security](https://github.com/python/cpython/blob/58ed60b7415e218ce3d608302e39b5e55bfb0e88/Doc/library/urllib.parse.rst): parsing does not validate URLs.
- [HTTPX async clients](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/docs/async.md): reuse clients for connection pooling. V2 already does this; status-endpoint client reuse remains a possible follow-up requiring managed app lifecycle.

241 Python tests passed, including stale status, server changes, URL validation, missing/timed-out systemd, non-blocking checks, and both reconnect paths. Existing deprecation warnings remain.

**Experimental / outstanding:** real BLE/GPIO/camera/provider behavior, Pi performance, mobile devices, production connections and image builds remain unverified. Manufacturer sources in the existing registers were not revalidated live; no new Mars Hydro BLE command or hardware approval follows from this review. Heartbeats depend on a reliable clock. V2 has no remote-command polling, and stored automation definitions do not establish that a time/temperature scheduler runs. See the [detailed German review](../de/APP_REVIEW_2026-10-09.md).
