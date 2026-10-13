from aiohttp import ClientError
from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN
from .entity import GrowCentralEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    known = set()

    def discover():
        entities = []
        for identifier, row in coordinator.data.items():
            if row['writable'] and identifier not in known:
                known.add(identifier)
                entities.append(GrowCentralSwitch(coordinator, entry, identifier))
        async_add_entities(entities)

    discover()
    entry.async_on_unload(coordinator.async_add_listener(discover))


class GrowCentralSwitch(GrowCentralEntity, SwitchEntity):
    _attr_name = 'Switch'

    def __init__(self, coordinator, entry, identifier):
        super().__init__(coordinator, entry, identifier)
        self._attr_unique_id = entry.entry_id + ':' + identifier + ':switch'

    @property
    def is_on(self):
        return self.row.get('on') is True

    @property
    def available(self):
        return super().available and self.row.get('writable', False) and self.row.get('on') is not None

    async def _set(self, on):
        if not self.available:
            raise HomeAssistantError('Grow Central device is unavailable or no longer approved')
        try:
            await self.coordinator.api.switch(self.identifier, on)
        except (ClientError, ConnectionError, PermissionError, TimeoutError, ValueError) as exc:
            raise HomeAssistantError('Grow Central denied or could not complete the command') from exc
        finally:
            await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._set(True)

    async def async_turn_off(self, **kwargs):
        await self._set(False)
