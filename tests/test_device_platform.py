from app.devices.catalog import PROVIDERS, provider_by_id, provider_catalog
from app.devices.models import Capability, SupportLevel


def test_provider_ids_are_unique_and_required_families_exist():
    ids = [provider.id for provider in PROVIDERS]
    assert len(ids) == len(set(ids))
    required = {
        "mars_hydro", "spider_farmer", "tuya", "ac_infinity", "vivosun",
        "shelly", "zigbee", "growcentral_esp32", "tapo", "fritz",
        "home_assistant", "mqtt",
    }
    assert required.issubset(set(ids))


def test_all_first_class_providers_are_local_first():
    assert all(provider.local_first for provider in PROVIDERS)


def test_catalog_is_json_ready_and_exposes_support_state():
    catalog = provider_catalog()
    assert catalog
    assert all(isinstance(row["capabilities"], list) for row in catalog)
    assert all(row["support"] in {item.value for item in SupportLevel} for row in catalog)


def test_native_esp32_is_reference_provider():
    provider = provider_by_id("growcentral_esp32")
    assert provider is not None
    assert set(provider.capabilities) == set(Capability)
