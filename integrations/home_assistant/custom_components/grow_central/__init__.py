"""Grow Central local integration."""
from datetime import timedelta

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
import logging

from .api import GrowCentralAPI
from .const import DOMAIN, PLATFORMS

LOGGER = logging.getLogger(__name__)


class GrowCentralCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, entry=None):
        super().__init__(hass, LOGGER, config_entry=entry, name=DOMAIN, update_interval=timedelta(seconds=30))
        self.api = api

    async def _async_update_data(self):
        try:
            return await self.api.snapshot()
        except PermissionError as exc:
            raise ConfigEntryAuthFailed('Check the dedicated Grow Central bridge token') from exc
        except (ClientError, ConnectionError, TimeoutError, ValueError, KeyError) as exc:
            raise UpdateFailed('Grow Central cannot be reached or returned invalid data') from exc


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    api = GrowCentralAPI(async_get_clientsession(hass), entry.data['url'], entry.data['token'])
    coordinator = GrowCentralCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        return True
    return False
