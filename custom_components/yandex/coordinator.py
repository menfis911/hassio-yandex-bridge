from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import YandexApi, YandexApiError
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class YandexCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    def __init__(self, hass, api: YandexApi, device_ids: list[str]) -> None:
        self.api = api
        self.device_ids = set(device_ids)
        super().__init__(
            hass,
            _LOGGER,
            name="Yandex Smart Home",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            result: dict[str, dict[str, Any]] = {}
            info = await self.api.async_get_info()
            devices = {str(device.get("id")): device for device in info.get("devices", [])}
            for device_id in self.device_ids:
                device = devices.get(device_id)
                if device is None:
                    continue
                try:
                    result[device_id] = await self.api.async_get_device(device_id)
                except YandexApiError:
                    _LOGGER.warning("Не удалось получить состояние устройства %s", device_id)
                    result[device_id] = device
            return result
        except YandexApiError as err:
            raise UpdateFailed(str(err)) from err

    def set_device_ids(self, device_ids: list[str]) -> None:
        self.device_ids = set(device_ids)
