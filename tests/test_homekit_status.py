from app.smarthome.homekit_status import service_mapping, stable_accessory_id


def test_accessory_id_is_stable_and_metric_scoped():
    first = stable_accessory_id('growcentral_esp32:soil-1', 'soil_moisture')
    second = stable_accessory_id('growcentral_esp32:soil-1', 'soil_moisture')
    temperature = stable_accessory_id('growcentral_esp32:soil-1', 'temperature')
    assert first == second
    assert first != temperature


def test_soil_moisture_keeps_semantics_but_maps_to_homekit_visible_service():
    mapping = service_mapping('soil_moisture')
    assert mapping['service'] == 'HumiditySensor'
    assert mapping['characteristic'] == 'CurrentRelativeHumidity'
    assert mapping['semantic'] == 'soil_moisture'
    assert mapping['unit'] == '%'
