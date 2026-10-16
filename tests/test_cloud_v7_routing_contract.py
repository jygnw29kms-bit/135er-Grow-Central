from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_plesk_v7_router_keeps_v6_core_contract_public():
    routing = read("scripts/configure-v7-routing.sh")
    assert 'CORE_PORT="${APP_PORT:-18765}"' in routing
    assert "location = /health {" in routing
    assert "proxy_pass http://127.0.0.1:${CORE_PORT}/health;" in routing
    assert "location = /.well-known/growcentral-cloud {" in routing
    assert "location = /pair {" in routing
    assert "location ^~ /api/v2/ {" in routing
    assert r'proxy_set_header Upgrade \$http_upgrade;' in routing
    assert "location = /api/health {" in routing
    assert "proxy_pass http://127.0.0.1:${PLATFORM_PORT}/api/health;" in routing
    assert "normalize_core_public_url" in routing
    assert 'expected="https://${CANONICAL_HOST}"' in routing
    assert "cloud.env.pre-canonical." in routing
    assert 'cp -a "$backup" "$ENV_FILE"' in routing


def test_platform_sidecar_exposes_pre_v7_pi_health_contract():
    source = read("cloud/v7/platform_status_app.py")
    assert '@app.get("/api/health")' in source
    assert '"service": "135er-Grow Central Cloud"' in source
    assert '"version": "7"' in source
    assert '"compatibility": "v7-platform-status"' in source


def test_platform_deploy_uses_checked_out_sources_and_verifies_core_routes():
    workflow = read(".github/workflows/deploy-grow-central-platform.yml")
    installer = read("scripts/install-platform-status-v1.sh")
    assert "remote_copy scripts/configure-v7-routing.sh /tmp/configure-v7-routing.sh" in workflow
    assert "remote_copy cloud/v7/platform_status_app.py /tmp/platform_status_app.py" in workflow
    assert "PLATFORM_SOURCE=/tmp/platform_status_app.py" in workflow
    assert "ROUTER_SOURCE=/tmp/configure-v7-routing.sh" in workflow
    assert "raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/master/scripts/install-platform-status-v1.sh" not in workflow
    assert 'PLATFORM_SOURCE="${PLATFORM_SOURCE:-}"' in installer
    assert 'ROUTER_SOURCE="${ROUTER_SOURCE:-}"' in installer
    for endpoint in (
        "https://135ercloud.grow-central.de/health",
        "https://135ercloud.grow-central.de/.well-known/growcentral-cloud",
        "https://135ercloud.grow-central.de/api/health",
        "https://135ercloud.grow-central.de/api/v2/device/authorize",
    ):
        assert endpoint in workflow
    assert 'd.get("public_url") == "https://135ercloud.grow-central.de"' in workflow
