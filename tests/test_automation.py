import asyncio

from app import automation


def test_local_automation_create_list_and_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(automation, "DATA_FILE", tmp_path / "automations.json")
    definition = automation.AutomationDefinition(
        name="Lampe morgens", trigger="time", trigger_value="08:00",
        device_id="fritz-lampe", ain="08761 0001", on=True,
    )
    created = asyncio.run(automation.create_automation(definition))
    assert created["automation"]["id"] == "gc-1"
    assert created["execution_policy"] == "stored_fritz_credentials"
    listed = asyncio.run(automation.list_automations())
    assert listed["automations"][0]["name"] == "Lampe morgens"
    asyncio.run(automation.delete_automation("gc-1"))
    assert asyncio.run(automation.list_automations())["automations"] == []



def test_time_trigger_validation(tmp_path, monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setattr(automation, "DATA_FILE", tmp_path / "automations.json")
    monkeypatch.setattr(automation, "append_audit", lambda *a, **k: None)
    definition = automation.AutomationDefinition(
        name="Ung?ltig", trigger="time", trigger_value="25:99",
        device_id="fritz-lampe", ain="08761 0001", on=True,
    )
    try:
        asyncio.run(automation.create_automation(definition))
    except HTTPException as exc:
        assert exc.status_code == 422
    else:
        raise AssertionError("invalid time must be rejected")


def test_manual_execution_requires_confirmed_fritz_state(tmp_path, monkeypatch):
    monkeypatch.setattr(automation, "DATA_FILE", tmp_path / "automations.json")
    monkeypatch.setattr(automation, "RUNTIME_FILE", tmp_path / "runtime.json")
    monkeypatch.setattr(automation, "append_audit", lambda *a, **k: None)
    monkeypatch.setattr(automation, "get_provider_config", lambda provider: {"host":"fritz.box","username":"gc","password":"secret"})
    calls=[]
    class FakeFritz:
        def __init__(self, host, username, password):
            assert (host, username, password) == ("fritz.box", "gc", "secret")
        async def command(self, command, ain):
            calls.append((command, ain))
            return "1" if command in {"setswitchon", "getswitchstate"} else "0"
    monkeypatch.setattr(automation, "FritzAhaClient", FakeFritz)
    definition = automation.AutomationDefinition(
        name="Lampe jetzt", trigger="manual", trigger_value="",
        device_id="fritz-lampe", ain="08761 0001", on=True,
    )
    created=asyncio.run(automation.create_automation(definition))["automation"]
    result=asyncio.run(automation.run_automation(created["id"]))
    assert result["confirmed"] is True
    assert calls == [("setswitchon", "08761 0001"), ("getswitchstate", "08761 0001")]
    runtime=automation._runtime_load()["last_runs"][created["id"]]
    assert runtime["ok"] is True and runtime["source"] == "manual"


def test_scheduler_fires_time_rule_once_per_minute(tmp_path, monkeypatch):
    from datetime import datetime
    monkeypatch.setattr(automation, "DATA_FILE", tmp_path / "automations.json")
    monkeypatch.setattr(automation, "RUNTIME_FILE", tmp_path / "runtime.json")
    monkeypatch.setattr(automation, "append_audit", lambda *a, **k: None)
    definition = automation.AutomationDefinition(
        name="Lampe morgens", trigger="time", trigger_value="08:00",
        device_id="fritz-lampe", ain="08761 0001", on=True,
    )
    created=asyncio.run(automation.create_automation(definition))["automation"]
    calls=[]
    async def fake_execute(row, *, source):
        calls.append((row["id"], source)); return {"ok":True}
    monkeypatch.setattr(automation, "_execute", fake_execute)
    now=datetime(2026,10,15,8,0,tzinfo=automation.LOCAL_TZ)
    assert asyncio.run(automation._scheduler_tick(now)) == 1
    assert asyncio.run(automation._scheduler_tick(now)) == 0
    assert calls == [(created["id"], "scheduler")]
