"""Config flow for Yandex Smart Home."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .api import YandexApi, YandexApiError
from .const import CONF_DEVICE_IDS, CONF_TOKEN, DOMAIN, NAME

class YandexConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            token = user_input[CONF_TOKEN].strip()
            try:
                devices = await YandexApi(token).get_devices()
            except YandexApiError:
                errors[CONF_TOKEN] = "cannot_connect"
            else:
                self._token = token
                self._devices = devices
                return await self.async_step_devices()
        schema = vol.Schema({vol.Required(CONF_TOKEN): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_devices(self, user_input=None):
        if user_input is not None:
            ids = user_input.get(CONF_DEVICE_IDS, [])
            await self.async_set_unique_id("yandex_smart_home")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=NAME, data={CONF_TOKEN: self._token, CONF_DEVICE_IDS: ids})
        options = [selector.SelectOptionDict(value=str(d.get("id")), label=f"{d.get('name', 'Без имени')} — {(d.get('device_info') or {}).get('model', '—')}") for d in self._devices]
        schema = vol.Schema({vol.Optional(CONF_DEVICE_IDS, default=[]): selector.SelectSelector(selector.SelectSelectorConfig(options=options, multiple=True, mode=selector.SelectSelectorMode.LIST))})
        return self.async_show_form(step_id="devices", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return YandexOptionsFlow(config_entry)

class YandexOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self.hass.config_entries.async_update_entry(self.entry, data={**self.entry.data, CONF_DEVICE_IDS: user_input.get(CONF_DEVICE_IDS, [])})
            return self.async_create_entry(data={})
        try:
            devices = await YandexApi(self.entry.data[CONF_TOKEN]).get_devices()
        except YandexApiError:
            devices = []
        options = [selector.SelectOptionDict(value=str(d.get("id")), label=f"{d.get('name', 'Без имени')} — {(d.get('device_info') or {}).get('model', '—')}") for d in devices]
        selected = self.entry.data.get(CONF_DEVICE_IDS, [])
        schema = vol.Schema({vol.Optional(CONF_DEVICE_IDS, default=selected): selector.SelectSelector(selector.SelectSelectorConfig(options=options, multiple=True, mode=selector.SelectSelectorMode.LIST))})
        return self.async_show_form(step_id="init", data_schema=schema)
