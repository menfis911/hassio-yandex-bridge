from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .api import YandexApi, YandexApiError
from .const import CONF_DEVICE_IDS, CONF_TOKEN, DOMAIN


class YandexConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._token = ""
        self._devices: list[dict] = []

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            api = YandexApi(token)
            try:
                info = await api.async_get_info()
                devices = info.get("devices", [])
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    self._token = token
                    self._devices = devices
                    await api.async_close()
                    return await self.async_step_devices()
            except YandexApiError:
                errors["base"] = "cannot_connect"
            finally:
                await api.async_close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )

    async def async_step_devices(self, user_input=None):
        options = []
        for device in self._devices:
            device_id = str(device.get("id", ""))
            if not device_id:
                continue
            info = device.get("device_info", {}) or {}
            model = info.get("model") or "без модели"
            name = device.get("name") or "Без имени"
            options.append(selector.SelectOptionDict(value=device_id, label=f"{name} — {model}"))

        if user_input is not None:
            selected = list(user_input.get(CONF_DEVICE_IDS, []))
            await self.async_set_unique_id("yandex_smart_home")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Yandex Smart Home",
                data={CONF_TOKEN: self._token, CONF_DEVICE_IDS: selected},
            )

        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_IDS, default=[]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }),
        )

    @staticmethod
    async def async_get_options_flow(config_entry):
        return YandexOptionsFlow(config_entry)


class YandexOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self._devices: list[dict] = []

    async def async_step_init(self, user_input=None):
        api = YandexApi(self.config_entry.data[CONF_TOKEN])
        try:
            info = await api.async_get_info()
            self._devices = info.get("devices", [])
        except YandexApiError:
            return self.async_abort(reason="cannot_connect")
        finally:
            await api.async_close()

        options = []
        for device in self._devices:
            device_id = str(device.get("id", ""))
            info = device.get("device_info", {}) or {}
            options.append(selector.SelectOptionDict(value=device_id, label=f"{device.get('name', 'Без имени')} — {info.get('model', 'без модели')}"))

        if user_input is not None:
            new_data = dict(self.config_entry.data)
            new_data[CONF_DEVICE_IDS] = list(user_input.get(CONF_DEVICE_IDS, []))
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        current = list(self.config_entry.data.get(CONF_DEVICE_IDS, []))
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_IDS, default=current): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options, multiple=True, mode=selector.SelectSelectorMode.LIST)
                )
            }),
        )
