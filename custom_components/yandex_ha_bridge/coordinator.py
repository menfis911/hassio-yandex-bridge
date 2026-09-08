"""Data coordinator."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import YandexApi, YandexApiError
from .const import CONF_DEVICE_IDS, CONF_TOKEN, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class YandexDataUpdateCoordinator(DataUpdateCoordinator[dict[str, dict]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.api = YandexApi(entry.data[CONF_TOKEN])
        self.device_ids = set(entry.data.get(CONF_DEVICE_IDS, []))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, dict]:
        try:
            devices = await self.api.get_devices()
            selected = {str(d.get("id")): d for d in devices if str(d.get("id")) in self.device_ids}
            result: dict[str, dict] = {}
            for device_id in selected:
                result[device_id] = await self.api.get_device(device_id)
            return result
        except YandexApiError as err:
            raise UpdateFailed(str(err)) from err

    async def async_action(self, device_id: str, actions: list[dict]) -> None:
        try:
            await self.api.actions(device_id, actions)
            await self.async_request_refresh()
        except YandexApiError as err:
            raise UpdateFailed(str(err)) from err
