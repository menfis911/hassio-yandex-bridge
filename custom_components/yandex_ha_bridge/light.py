"""Yandex light platform."""
from __future__ import annotations

import colorsys

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YandexDataUpdateCoordinator


class YandexLight(CoordinatorEntity[YandexDataUpdateCoordinator], LightEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, device_id: str, device: dict) -> None:
        super().__init__(coordinator)
        self.device_id = device_id
        self.device = device
        self._attr_unique_id = f"{device_id}_light"
        self._attr_name = device.get("name", "Yandex light")
        info = device.get("device_info") or {}
        self._attr_device_info = {"identifiers": {(DOMAIN, device_id)}, "name": self._attr_name, "manufacturer": info.get("manufacturer"), "model": info.get("model")}
        self._set_modes()

    @property
    def current(self):
        return self.coordinator.data.get(self.device_id, self.device)

    def _caps(self):
        return self.current.get("capabilities", [])

    def _cap(self, capability_type, instance=None):
        for cap in self._caps():
            if cap.get("type") != capability_type:
                continue
            state = cap.get("state") or {}
            params = cap.get("parameters") or {}
            if instance is None or state.get("instance") == instance or params.get("instance") == instance:
                return cap
        return None

    def _state(self, capability_type, instance=None):
        cap = self._cap(capability_type, instance)
        return (cap.get("state") or {}).get("value") if cap else None

    def _set_modes(self):
        modes = set()
        color_cap = self._cap("devices.capabilities.color_setting")
        if color_cap:
            params = color_cap.get("parameters") or {}
            models = params.get("color_model") or []
            if "rgb" in models or "hsv" in models or self._state("devices.capabilities.color_setting", "hsv") is not None or self._state("devices.capabilities.color_setting", "rgb") is not None:
                modes.add(ColorMode.RGB)
            if "temperature_k" in models or self._state("devices.capabilities.color_setting", "temperature_k") is not None:
                modes.add(ColorMode.COLOR_TEMP)
        if not modes:
            if self._cap("devices.capabilities.range", "brightness"):
                modes.add(ColorMode.BRIGHTNESS)
            else:
                modes.add(ColorMode.ONOFF)
        self._attr_supported_color_modes = modes
        self._attr_color_mode = next(iter(modes))

    @property
    def is_on(self):
        return bool(self._state("devices.capabilities.on_off", "on"))

    @property
    def brightness(self):
        value = self._state("devices.capabilities.range", "brightness")
        return round(float(value) * 255 / 100) if value is not None else None

    @property
    def rgb_color(self):
        value = self._state("devices.capabilities.color_setting", "rgb")
        if isinstance(value, int):
            return ((value >> 16) & 255, (value >> 8) & 255, value & 255)
        hsv = self._state("devices.capabilities.color_setting", "hsv")
        if isinstance(hsv, dict):
            r, g, b = colorsys.hsv_to_rgb(float(hsv.get("h", 0)) / 360, float(hsv.get("s", 0)) / 100, float(hsv.get("v", 0)) / 100)
            return round(r * 255), round(g * 255), round(b * 255)
        return None

    @property
    def color_temp_kelvin(self):
        value = self._state("devices.capabilities.color_setting", "temperature_k")
        return int(value) if value is not None else None

    @property
    def min_color_temp_kelvin(self):
        params = (self._cap("devices.capabilities.color_setting") or {}).get("parameters") or {}
        return int(params.get("temperature_k_min", 2700))

    @property
    def max_color_temp_kelvin(self):
        params = (self._cap("devices.capabilities.color_setting") or {}).get("parameters") or {}
        return int(params.get("temperature_k_max", 6500))

    async def async_turn_on(self, **kwargs):
        actions = [{"type": "devices.capabilities.on_off", "state": {"instance": "on", "value": True}}]
        if ATTR_BRIGHTNESS in kwargs:
            actions.append({"type": "devices.capabilities.range", "state": {"instance": "brightness", "value": round(kwargs[ATTR_BRIGHTNESS] * 100 / 255)}})
        if "rgb_color" in kwargs:
            r, g, b = kwargs["rgb_color"]
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            actions.append({"type": "devices.capabilities.color_setting", "state": {"instance": "hsv", "value": {"h": round(h * 360, 2), "s": round(s * 100, 2), "v": round(v * 100, 2)}}})
        if "color_temp_kelvin" in kwargs:
            actions.append({"type": "devices.capabilities.color_setting", "state": {"instance": "temperature_k", "value": int(kwargs["color_temp_kelvin"])}})
        await self.coordinator.async_action(self.device_id, actions)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_action(self.device_id, [{"type": "devices.capabilities.on_off", "state": {"instance": "on", "value": False}}])


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([YandexLight(coordinator, device_id, device) for device_id, device in coordinator.data.items() if device.get("type", "").startswith("devices.types.light") or any(c.get("type") == "devices.capabilities.on_off" for c in device.get("capabilities", []))])
