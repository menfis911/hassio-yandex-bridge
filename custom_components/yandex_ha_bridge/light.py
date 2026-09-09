"""Yandex light platform."""
from __future__ import annotations

import colorsys
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.helpers.entity import DeviceInfo
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
        room = device.get("room") or device.get("room_name") or info.get("room")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.get("name") or self._attr_name,
            manufacturer=info.get("manufacturer"),
            model=info.get("model"),
            serial_number=device_id,
            suggested_area=room,
        )
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
        return {str(model) for model in (params.get("color_model") or [])}

    def _set_modes(self) -> None:
        """Set a Home Assistant-valid color mode combination."""
        models = self._color_models()
        has_hs = "hsv" in models or self._state(CAP_COLOR, "hsv") is not None
        has_rgb = "rgb" in models or self._state(CAP_COLOR, "rgb") is not None
        has_color_temp = "temperature_k" in models or self._state(CAP_COLOR, "temperature_k") is not None
        has_brightness = self._cap(CAP_RANGE, "brightness") is not None

        # HSV is represented by Home Assistant's HS mode. RGB is only used
        # when Yandex explicitly advertises rgb. COLOR_TEMP includes brightness
        # support implicitly, so BRIGHTNESS is never combined with it.
        if has_hs:
            modes: set[ColorMode] = {ColorMode.HS}
            if has_color_temp:
                modes.add(ColorMode.COLOR_TEMP)
            self._attr_color_mode = ColorMode.HS
        elif has_rgb:
            modes = {ColorMode.RGB}
            if has_color_temp:
                modes.add(ColorMode.COLOR_TEMP)
            self._attr_color_mode = ColorMode.RGB
        elif has_color_temp:
            modes = {ColorMode.COLOR_TEMP}
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif has_brightness:
            modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF

        self._attr_supported_color_modes = modes

    @property
    def is_on(self) -> bool:
        return bool(self._state(CAP_ON_OFF, "on"))

    @property
    def brightness(self) -> int | None:
        value = self._state(CAP_RANGE, "brightness")
        return round(float(value) * 255 / 100) if value is not None else None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        value = self._state(CAP_COLOR, "hsv")
        if not isinstance(value, dict):
            return None
        return float(value.get("h", 0)), float(value.get("s", 0))

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
        return int(((self._cap(CAP_COLOR) or {}).get("parameters") or {}).get("temperature_k_min", 2700))

    @property
    def max_color_temp_kelvin(self) -> int:
        return int(((self._cap(CAP_COLOR) or {}).get("parameters") or {}).get("temperature_k_max", 6500))

    @staticmethod
    def _display_value(value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, list):
            return ", ".join(str(item.get("name", item)) if isinstance(item, dict) else str(item) for item in value)
        return str(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        current = self.current
        info = current.get("device_info") or {}
        color_cap = self._cap(CAP_COLOR) or {}
        color_params = color_cap.get("parameters") or {}
        room = current.get("room") or current.get("room_name") or info.get("room")
        group = current.get("group") or current.get("group_name") or current.get("groups")
        return {
            "yandex_device_id": self.device_id,
            "yandex_device_type": current.get("type"),
            "yandex_state": current.get("state"),
            "yandex_room": self._display_value(room),
            "yandex_group": self._display_value(group),
            "yandex_manufacturer": info.get("manufacturer"),
            "yandex_model": info.get("model"),
            "yandex_color_model": ", ".join(sorted(self._color_models())) or None,
            "yandex_brightness_min": ((self._cap(CAP_RANGE, "brightness") or {}).get("parameters") or {}).get("range_min"),
            "yandex_brightness_max": ((self._cap(CAP_RANGE, "brightness") or {}).get("parameters") or {}).get("range_max"),
            "yandex_temperature_min": color_params.get("temperature_k_min"),
            "yandex_temperature_max": color_params.get("temperature_k_max"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        actions: list[dict[str, Any]] = []
        if self._cap(CAP_ON_OFF, "on"):
            actions.append({"type": CAP_ON_OFF, "state": {"instance": "on", "value": True}})
        if ATTR_BRIGHTNESS in kwargs and self._cap(CAP_RANGE, "brightness"):
            # Yandex rejects a brightness-only action while this lamp is OFF.
            # The ON action above intentionally accompanies brightness so the
            # Home Assistant behaviour matches the physical light expectation.
            actions.append({
                "type": CAP_RANGE,
                "state": {
                    "instance": "brightness",
                    "value": max(1, min(100, round(kwargs[ATTR_BRIGHTNESS] * 100 / 255))),
                },
            })
        models = self._color_models()
        if ATTR_HS_COLOR in kwargs and self._cap(CAP_COLOR) and "hsv" in models:
            h, s = kwargs[ATTR_HS_COLOR]
            v = max(1, min(100, round((kwargs.get(ATTR_BRIGHTNESS, self.brightness or 255)) * 100 / 255)))
            actions.append({"type": CAP_COLOR, "state": {"instance": "hsv", "value": {"h": round(h, 2), "s": round(s, 2), "v": v}}})
        elif ATTR_RGB_COLOR in kwargs and self._cap(CAP_COLOR):
            r, g, b = kwargs[ATTR_RGB_COLOR]
            if "hsv" in models:
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                actions.append({"type": CAP_COLOR, "state": {"instance": "hsv", "value": {"h": round(h * 360, 2), "s": round(s * 100, 2), "v": round(v * 100, 2)}}})
            elif "rgb" in models:
                actions.append({"type": CAP_COLOR, "state": {"instance": "rgb", "value": (int(r) << 16) | (int(g) << 8) | int(b)}})
        if ATTR_COLOR_TEMP_KELVIN in kwargs and "temperature_k" in models:
            actions.append({"type": CAP_COLOR, "state": {"instance": "temperature_k", "value": int(kwargs[ATTR_COLOR_TEMP_KELVIN])}})
        if actions:
            await self.coordinator.async_action(self.device_id, actions)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._cap(CAP_ON_OFF, "on"):
            await self.coordinator.async_action(self.device_id, [{"type": CAP_ON_OFF, "state": {"instance": "on", "value": False}}])


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up Yandex light entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        YandexLight(coordinator, device_id, device)
        for device_id, device in coordinator.data.items()
        if device.get("type", "").startswith("devices.types.light")
    ])
