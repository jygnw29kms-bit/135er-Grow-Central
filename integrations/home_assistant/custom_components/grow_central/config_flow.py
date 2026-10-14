from aiohttp import ClientError
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GrowCentralAPI, validate_url
from .const import DOMAIN


class GrowCentralConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                url = validate_url(user_input['url'])
                if len(user_input['token'].strip()) < 32:
                    raise PermissionError()
                await GrowCentralAPI(async_get_clientsession(self.hass), url, user_input['token'].strip()).snapshot()
            except PermissionError:
                errors['base'] = 'invalid_auth'
            except (ClientError, ConnectionError, TimeoutError):
                errors['base'] = 'cannot_connect'
            except (ValueError, KeyError):
                errors['base'] = 'invalid_response'
            else:
                await self.async_set_unique_id(url)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title='Grow Central', data={'url': url, 'token': user_input['token'].strip()})
        return self.async_show_form(step_id='user', data_schema=vol.Schema({vol.Required('url'): str, vol.Required('token'): str}), errors=errors)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}
        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(self.context['entry_id'])
            try:
                await GrowCentralAPI(async_get_clientsession(self.hass), entry.data['url'], user_input['token'].strip()).snapshot()
            except PermissionError:
                errors['base'] = 'invalid_auth'
            except (ClientError, ConnectionError, TimeoutError, ValueError, KeyError):
                errors['base'] = 'cannot_connect'
            else:
                return self.async_update_reload_and_abort(entry, data_updates={'token': user_input['token'].strip()})
        return self.async_show_form(step_id='reauth_confirm', data_schema=vol.Schema({vol.Required('token'): str}), errors=errors)
