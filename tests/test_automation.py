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
    assert created["execution_policy"] == "manual_fritz_login_required"
    listed = asyncio.run(automation.list_automations())
    assert listed["automations"][0]["name"] == "Lampe morgens"
    asyncio.run(automation.delete_automation("gc-1"))
    assert asyncio.run(automation.list_automations())["automations"] == []
