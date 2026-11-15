"""Web Push subscription isolation, SSRF protection, delivery and revoked users."""
from app.room_push import trusted_endpoint, dispatch_event, valid_recipient


def test_only_recognized_https_push_services():
    assert trusted_endpoint("https://web.push.apple.com/QmFzZTY0")
    assert trusted_endpoint("https://fcm.googleapis.com/fcm/send/sample")
    assert trusted_endpoint("https://updates.push.services.mozilla.com/wpush/v2/sample")
    for url in ("http://web.push.apple.com/send/x", "https://127.0.0.1/private",
                "https://push.apple.com.evil.example/path", "https://example.org/webpush",
                "https://127.0.0.1:8443/path", "https://x@web.push.apple.com/route"):
        assert not trusted_endpoint(url)


def test_revoked_member_never_receives_push():
    event = {"room_id": "room_a", "kind": "threshold_high", "message": "Luftfeuchte zu hoch"}
    subscriptions = [
        {"room_id": "room_a", "actor": "owner", "endpoint": "https://web.push.apple.com/a", "keys": {}},
        {"room_id": "room_a", "actor": "member_1", "endpoint": "https://web.push.apple.com/b", "keys": {}},
        {"room_id": "room_b", "actor": "member_2", "endpoint": "https://web.push.apple.com/c", "keys": {}},
    ]
    shared = {"members": [{"id": "member_1", "status": "revoked", "room_id": "room_a", "role": "grower"}]}
    sent = []
    result = dispatch_event(event, subscriptions, sharing=shared, send=lambda row, payload: sent.append((row, payload)))
    assert result["accepted"] == 1
    assert sent[0][0]["actor"] == "owner"
    assert sent[0][1]["body"] == "Luftfeuchte zu hoch"


def test_active_grower_can_receive_room_alert_only():
    shared = {"members": [{"id": "m1", "status": "active", "room_id": "r1", "role": "grower"}]}
    assert valid_recipient({"actor": "m1", "room_id": "r1"}, shared)
    assert not valid_recipient({"actor": "m1", "room_id": "r2"}, shared)


def test_no_configured_sender_is_not_fake_delivery(monkeypatch):
    monkeypatch.delenv("GC_WEBPUSH_VAPID_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("GC_WEBPUSH_SUBJECT", raising=False)
    result = dispatch_event({"room_id": "room_a", "kind": "warning"}, [], sharing={"members": []})
    assert result["status"] == "not_configured"
    assert result["accepted"] == 0


def test_stored_malicious_endpoint_is_not_sent_even_if_file_was_modified():
    event = {"room_id": "room_a", "kind": "sensor_offline"}
    rows = [{"room_id": "room_a", "actor": "owner",
             "endpoint": "https://127.0.0.1/admin", "keys": {}}]
    submitted = []
    result = dispatch_event(event, rows, sharing={"members": []},
                            send=lambda row, data: submitted.append(row))
    assert result["accepted"] == 0
    assert submitted == []
