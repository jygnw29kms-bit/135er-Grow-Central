from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN


class GrowCentralEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, identifier):
        super().__init__(coordinator)
        self.identifier = identifier
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id + ':' + identifier)},
            name=coordinator.data[identifier]['name'], manufacturer='Grow Central')

    @property
    def row(self):
        return self.coordinator.data.get(self.identifier, {})

    @property
    def available(self):
        return super().available and self.row.get('online', False)
