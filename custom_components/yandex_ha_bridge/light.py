"""Yandex light platform."""
from __future__ import annotations

import colorsys
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YandexDataUpdateCoordinator

CAP_ON_OFF = "devices.capabilities.on_off"
CAP_RANGE = "devices.capabilities.range"
CAP_COLOR = "devices.capabilities.color_setting"


class YandexLight(CoordinatorEntity[YandexDataUpdateCoordinator], LightEntity):
    """Representation of a Yandex Smart Home light."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: YandexDataUpdateCoordinator, device_id: str, device: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self.device_id = device_id
        self.device = device
        self._attr_unique_id = f"{device_id}_light"
        self._attr_name = device.get("name", "Yandex light")
        info = device.get("device_info") or {}
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": self._attr_name,
            "manufacturer": info.get("manufacturer"),
            "model": info.get("model"),
        }
        self._set_modes()

    @property
    def current(self) -> dict[str, Any]:
        return self.coordinator.data.get(self.device_id, self.device)

    def _caps(self) -> list[dict[str, Any]]:
        return self.current.get("capabilities", [])

    def _cap(self, capability_type: str, instance: str | None = None) -> dict[str, Any] | None:
        for cap in self._caps():
            if cap.get("type") != capability_type:
                continue
            if instance is None:
                return cap
            state = cap.get("state") or {}
            params = cap.get("parameters") or {}
            if state.get("instance") == instance or params.get("instance") == instance:
                return cap
        return None

    def _state(self, capability_type: str, instance: str | None = None) -> Any:
        cap = self._cap(capability_type, instance)
        return (cap.get("state") or {}).get("value") if cap else None

    def _color_models(self) -> set[str]:
        params = (self._cap(CAP_COLOR) or {}).get("parameters") or {}
        models = params.get("color_model") or []
        return {str(model) for model in models}

    def _set_modes(self) -> None:
        modes: set[ColorMode] = set()
        models = self._color_models()
        if "rgb" in models or "hsv" in models or self._state(CAP_COLOR, "hsv") is not None or self._state(CAP_COLOR, "rgb") is not None:
            modes.add(ColorMode.RGB)
        if "temperature_k" in models or self._state(CAP_COLOR, "temperature_k") is not None:
            modes.add(ColorMode.COLOR_TEMP)
        if self._cap(CAP_RANGE, "brightness"):
            modes.add(ColorMode.BRIGHTNESS)
        if not modes:
            modes.add(ColorMode.ONOFF)
        self._attr_supported_color_modes = modes
        self._attr_color_mode = next(iter(modes))

    @property
    def is_on(self) -> bool:
        return bool(self._state(CAP_ON_OFF, "on"))

    @property
    def brightness(self) -> int | None:
        value = self._state(CAP_RANGE, "brightness")
        return round(float(value) * 255 / 100) if value is not None else None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        value = self._state(CAP_COLOR, "rgb")
        if isinstance(value, int):
            return ((value >> 16) & 255, (value >> 8) & 255, value & 255)
        hsv = self._state(CAP_COLOR, "hsv")
        if isinstance(hsv, dict):
            r, g, b = colorsys.hsv_to_rgb(
                float(hsv.get("h", 0)) / 360,
                float(hsv.get("s", 0)) / 100,
                float(hsv.get("v", 0)) / 100,
            )
            return round(r * 255), round(g * 255), round(b * 255)
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        value = self._state(CAP_COLOR, "temperature_k")
        return int(value) if value is not None else None

    @property
    def min_color_temp_kelvin(self) -> int:
        params = (self._cap(CAP_COLOR) or {}).get("parameters") or {}
        return int(params.get("temperature_k_min", 2700))

    @property
    def max_color_temp_kelvin(self) -> int:
        params = (self._cap(CAP_COLOR) or {}).get("parameters") or {}
        return int(params.get("temperature_k_max", 6500))

    async def async_turn_on(self, **kwargs: Any) -> None:
        actions: list[dict[str, Any]] = []
        if self._cap(CAP_ON_OFF, "on"):
            actions.append({"type": CAP_ON_OFF, "state": {"instance": "on", "value": True}})

        if ATTR_BRIGHTNESS in kwargs and self._cap(CAP_RANGE, "brightness"):
            actions.append({
                "type": CAP_RANGE,
                "state": {
                    "instance": "brightness",
                    "value": max(1, min(100, round(kwargs[ATTR_BRIGHTNESS] * 100 / 255))),
                },
            })

        models = self._color_models()
        if ATTR_RGB_COLOR in kwargs and self._cap(CAP_COLOR):
            r, g, b = kwargs[ATTR_RGB_COLOR]
            if "hsv" in models:
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                actions.append({
                    "type": CAP_COLOR,
                    "state": {
                        "instance": "hsv",
                        "value": {
                            "h": round(h * 360, 2),
                            "s": round(s * 100, 2),
                            "v": round(v * 100, 2),
                        },
                    },
                })
            elif "rgb" in models:
                rgb = (int(r) << 16) | (int(g) << 8) | int(b)
                actions.append({
                    "type": CAP_COLOR,
                    "state": {"instance": "rgb", "value": rgb},
                })

        if ATTR_COLOR_TEMP_KELVIN in kwargs and "temperature_k" in models:
            actions.append({
                "type": CAP_COLOR,
                "state": {
                    "instance": "temperature_k",
                    "value": int(kwargs[ATTR_COLOR_TEMP_KELVIN]),
                },
            })

        if actions:
            await self.coordinator.async_action(self.device_id, actions)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._cap(CAP_ON_OFF, "on"):
            await self.coordinator.async_action(
                self.device_id,
                [{"type": CAP_ON_OFF, "state": {"instance": "on", "value": False}}],
            )


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up Yandex light entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        YandexLight(coordinator, device_id, device)
        for device_id, device in coordinator.data.items()
        if device.get("type", "").startswith("devices.types.light")
    ]
    async_add_entities(entities)
