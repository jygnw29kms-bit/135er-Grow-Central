from app.diagnostics import COMPLETION_MARKERS, redact


def test_redacts_common_secret_shapes():
    value = redact("token=test password: hunter2 Authorization=Bearer-secret safe=value")
    assert "test" not in value
    assert "hunter2" not in value
    assert "Bearer-secret" not in value
    assert "safe=value" in value


def test_does_not_redact_unrelated_log_text():
    assert redact("ssh.service active on port 22") == "ssh.service active on port 22"


def test_firstboot_units_have_completion_markers():
    assert set(COMPLETION_MARKERS) == {
        "grow-central-headless-firstboot.service",
        "grow-central-firstboot-firewall.service",
    }
