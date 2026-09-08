from __future__ import annotations

import colorsys
from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import YandexApiError
from .const import DOMAIN
from .coordinator import YandexCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: YandexCoordinator = data["coordinator"]
    async_add_entities(
        YandexLight(coordinator, device_id)
        for device_id in coordinator.device_ids
        if device_id in coordinator.data
    )


class YandexLight(CoordinatorEntity[YandexCoordinator], LightEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: YandexCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = device_id
        self._capabilities: dict[str, dict[str, Any]] = {}
        self._device: dict[str, Any] = {}
        self._refresh_metadata()

    @property
    def device(self) -> dict[str, Any]:
        return self.coordinator.data.get(self._device_id, {})

    def _handle_coordinator_update(self) -> None:
        self._refresh_metadata()
        super()._handle_coordinator_update()

    def _refresh_metadata(self) -> None:
        self._device = self.device
        self._capabilities = {
            capability["type"]: capability
            for capability in self._device.get("capabilities", []) or []
            if capability.get("type")
        }

        info = self._device.get("device_info", {}) or {}
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device.get("name") or "Yandex light",
            "manufacturer": info.get("manufacturer") or "Yandex",
            "model": info.get("model"),
            "sw_version": info.get("sw_version"),
        }

        modes = set()
        color = self._capabilities.get("devices.capabilities.color_setting", {})
        params = color.get("parameters", {}) or {}
        if params.get("color_model") in ("rgb", "hsv"):
            modes.add(ColorMode.RGB)
        if params.get("temperature_k") is not None:
            modes.add(ColorMode.COLOR_TEMP)
        if not modes:
            modes.add(
                ColorMode.BRIGHTNESS
                if self._has_brightness_capability()
                else ColorMode.ONOFF
            )
        self._attr_supported_color_modes = modes

        temp = params.get("temperature_k") or {}
        if temp.get("min") is not None:
            self._attr_min_color_temp_kelvin = int(temp["min"])
        if temp.get("max") is not None:
            self._attr_max_color_temp_kelvin = int(temp["max"])

    def _has_brightness_capability(self) -> bool:
        capability = self._capabilities.get("devices.capabilities.range", {})
        params = capability.get("parameters", {}) or {}
        return params.get("instance") == "brightness" or any(
            item.get("instance") == "brightness" for item in capability.get("parameters", {}).get("instances", []) or []
        ) or any(
            item.get("state", {}).get("instance") == "brightness"
            for item in self._device.get("capabilities", []) or []
            if item.get("type") == "devices.capabilities.range"
        )

    @property
    def name(self) -> str:
        return self._device.get("name") or "Yandex light"

    @property
    def is_on(self) -> bool:
        for capability in self._device.get("capabilities", []) or []:
            if capability.get("type") == "devices.capabilities.on_off":
                value = (capability.get("state") or {}).get("value")
                if isinstance(value, bool):
                    return value
        return False

    def _get_range_brightness(self) -> int | None:
        for capability in self._device.get("capabilities", []) or []:
            if capability.get("type") != "devices.capabilities.range":
                continue
            state = capability.get("state", {}) or {}
            if state.get("instance") == "brightness":
                value = state.get("value")
                return int(value) if isinstance(value, (int, float)) else None
        return None

    @property
    def brightness(self) -> int | None:
        value = self._get_range_brightness()
        if value is not None:
            return round(max(0, min(100, value)) * 255 / 100)
        color = self._color_state()
        if color and color[0] == "hsv" and isinstance(color[1], dict):
            return round(color[1].get("v", 0) * 255 / 100)
        return None

    def _color_state(self):
        for capability in self._device.get("capabilities", []) or []:
            if capability.get("type") == "devices.capabilities.color_setting":
                state = capability.get("state", {}) or {}
                instance = state.get("instance")
                if instance in ("rgb", "hsv", "temperature_k"):
                    return instance, state.get("value")
        return None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        color = self._color_state()
        if not color:
            return None
        instance, value = color
        if instance == "rgb" and isinstance(value, int):
            return ((value >> 16) & 255, (value >> 8) & 255, value & 255)
        if instance == "hsv" and isinstance(value, dict):
            r, g, b = colorsys.hsv_to_rgb(
                value.get("h", 0) / 360,
                value.get("s", 0) / 100,
                value.get("v", 0) / 100,
            )
            return (round(r * 255), round(g * 255), round(b * 255))
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        color = self._color_state()
        if color and color[0] == "temperature_k" and isinstance(color[1], (int, float)):
            return int(color[1])
        return None

    async def _async_action(self, actions: list[dict[str, Any]]) -> None:
        try:
            await self.coordinator.api.async_actions(self._device_id, actions)
        except YandexApiError as err:
            raise RuntimeError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        actions: list[dict[str, Any]] = []
        if kwargs.get("brightness") is not None and self._has_brightness_capability():
            actions.append({
                "type": "devices.capabilities.range",
                "state": {"instance": "brightness", "value": round(kwargs["brightness"] * 100 / 255)},
            })
        if kwargs.get("rgb_color") is not None:
            r, g, b = kwargs["rgb_color"]
            rgb = (int(r) << 16) | (int(g) << 8) | int(b)
            actions.append({
                "type": "devices.capabilities.color_setting",
                "state": {"instance": "rgb", "value": rgb},
            })
        if kwargs.get("color_temp_kelvin") is not None:
            actions.append({
                "type": "devices.capabilities.color_setting",
                "state": {"instance": "temperature_k", "value": int(kwargs["color_temp_kelvin"])},
            })
        actions.append({
            "type": "devices.capabilities.on_off",
            "state": {"instance": "on", "value": True},
        })
        await self._async_action(actions)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_action([{
            "type": "devices.capabilities.on_off",
            "state": {"instance": "on", "value": False},
        }])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"yandex_device_id": self._device_id}
