import stat

from app.smarthome.models import DeviceConfig
from app.smarthome.registry import DeviceRegistry


def _device(identifier: str, adapter: str, native_id: str) -> DeviceConfig:
    return DeviceConfig(
        id=identifier,
        name=identifier.replace("-", " ").title(),
        adapter=adapter,
        native_id=native_id,
        approved=True,
        writable=True,
        host="fritz.box" if adapter == "fritz" else "192.168.178.50",
    )


def test_registered_devices_survive_registry_restart(monkeypatch, tmp_path):
    path = tmp_path / "devices.json"
    monkeypatch.setenv("GC_SMARTHOME_DEVICE_CONFIG", str(path))
    registry = DeviceRegistry.from_env()
    registry.upsert(_device("fritz-lampe", "fritz", "11657 0675300"))

    restarted = DeviceRegistry.from_env()

    assert [row.id for row in restarted.list()] == ["fritz-lampe"]
    assert restarted.get("fritz-lampe").native_id == "11657 0675300"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_stale_registry_instances_do_not_overwrite_other_devices(monkeypatch, tmp_path):
    path = tmp_path / "devices.json"
    monkeypatch.setenv("GC_SMARTHOME_DEVICE_CONFIG", str(path))
    seed = DeviceRegistry.from_env()
    seed.upsert(_device("fritz-lampe", "fritz", "old-ain"))
    first = DeviceRegistry.from_env()
    second = DeviceRegistry.from_env()

    first.upsert(_device("fritz-lampe", "fritz", "11657 0675300"))
    second.upsert(_device("tapo-luefter", "tapo", "switch:0"))

    reloaded = DeviceRegistry.from_env()
    assert [row.id for row in reloaded.list()] == [
        "fritz-lampe",
        "tapo-luefter",
    ]
    assert reloaded.get("fritz-lampe").native_id == "11657 0675300"
    assert not list(tmp_path.glob(".devices.json-*"))
