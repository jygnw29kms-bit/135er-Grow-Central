from app.diagnostics import redact


def test_redacts_common_secret_shapes():
    value = redact("token=test password: hunter2 Authorization=Bearer-secret safe=value")
    assert "test" not in value
    assert "hunter2" not in value
    assert "Bearer-secret" not in value
    assert "safe=value" in value


def test_does_not_redact_unrelated_log_text():
    assert redact("ssh.service active on port 22") == "ssh.service active on port 22"
