from homeassistant.components.sensor import SensorEntity, SensorStateClass
from .const import DOMAIN
from .entity import GrowCentralEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    known = set()

    def discover():
        entities = []
        for identifier, row in coordinator.data.items():
            for metric in row['measurements']:
                key = (identifier, metric)
                if key not in known:
                    known.add(key)
                    entities.append(GrowCentralSensor(coordinator, entry, identifier, metric))
        async_add_entities(entities)

    discover()
    entry.async_on_unload(coordinator.async_add_listener(discover))


class GrowCentralSensor(GrowCentralEntity, SensorEntity):
    def __init__(self, coordinator, entry, identifier, metric):
        super().__init__(coordinator, entry, identifier)
        self.metric = metric
        data = self.row['measurements'][metric]
        self._attr_unique_id = entry.entry_id + ':' + identifier + ':' + metric
        self._attr_name = metric.replace('_', ' ')
        self._attr_native_unit_of_measurement = data['unit']
        self._attr_device_class = data['device_class']
        # Energy sources may reset and are not guaranteed cumulative meters.
        self._attr_state_class = SensorStateClass.MEASUREMENT if metric != 'energy_wh' else None

    @property
    def native_value(self):
        return self.row.get('measurements', {}).get(self.metric, {}).get('value')

    @property
    def available(self):
        return super().available and self.metric in self.row.get('measurements', {})
