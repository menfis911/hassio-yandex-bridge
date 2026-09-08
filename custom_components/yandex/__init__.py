from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_flow

from .api import YandexApi
from .const import CONF_DEVICE_IDS, CONF_TOKEN, DOMAIN
from .coordinator import YandexCoordinator

PLATFORMS = ["light"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = YandexApi(entry.data[CONF_TOKEN])
    coordinator = YandexCoordinator(hass, api, list(entry.data.get(CONF_DEVICE_IDS, [])))
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"api": api, "coordinator": coordinator}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data[DOMAIN].pop(entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    await data["api"].async_close()
    return unload_ok
