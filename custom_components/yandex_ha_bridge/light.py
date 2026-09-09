"""Yandex light platform."""
from __future__ import annotations

import colorsys
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .actions import brightness as brightness_action
from .actions import hsv as hsv_action
from .actions import on_off
from .actions import rgb as rgb_action
from .actions import scene as scene_action
from .actions import temperature_k as temperature_action
from .const import DOMAIN
from .coordinator import YandexDataUpdateCoordinator

CAP_ON_OFF = "devices.capabilities.on_off"
CAP_RANGE = "devices.capabilities.range"
CAP_COLOR = "devices.capabilities.color_setting"


SCENE_NAMES: dict[str, str] = {
    "miracle": "Чудо", "fairy": "Сказочные огни", "northern": "Северное сияние", "christmas": "Рождество",
    "alice": "Алиса", "party": "Вечеринка", "jungle": "Джунгли", "neon": "Неон", "night": "Ночь",
    "ocean": "Океан", "romance": "Романтика", "candle": "Свеча", "siren": "Сирена", "alarm": "Тревога",
    "fantasy": "Фантазия", "reading": "Чтение",
}


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
            identifiers={(DOMAIN, device_id)}, name=device.get("name") or self._attr_name,
            manufacturer=info.get("manufacturer"), model=info.get("model"),
            serial_number=device_id, suggested_area=room,
        )
        self._set_modes()

    @property
    def current(self) -> dict[str, Any]:
        return self.coordinator.data.get(self.device_id, self.device)

    def _caps(self) -> list[dict[str, Any]]:
        caps = self.current.get("capabilities", [])
        return caps if isinstance(caps, list) else []

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
        raw = params.get("color_model")
        if isinstance(raw, str):
            return {raw.lower()}
        if isinstance(raw, (list, tuple, set)):
            return {str(model).lower() for model in raw}
        return set()

    def _has_color_capability(self, instance: str) -> bool:
        cap = self._cap(CAP_COLOR) or {}
        params = cap.get("parameters") or {}
        state = cap.get("state") or {}
        if instance in self._color_models() or state.get("instance") == instance:
            return True
        if instance == "temperature_k":
            return isinstance(params.get("temperature_k"), dict)
        return False

    def _scenes(self) -> list[dict[str, Any]]:
        scenes = (((self._cap(CAP_COLOR) or {}).get("parameters") or {}).get("color_scene") or {}).get("scenes", [])
        return scenes if isinstance(scenes, list) else []

    def _scene_name(self, scene_id: str) -> str:
        for item in self._scenes():
            if str(item.get("id")) == scene_id:
                return str(item.get("name") or SCENE_NAMES.get(scene_id, scene_id))
        return SCENE_NAMES.get(scene_id, scene_id)

    def _scene_id_by_name(self, name: str) -> str | None:
        for item in self._scenes():
            scene_id = str(item.get("id", ""))
            if scene_id and self._scene_name(scene_id) == name:
                return scene_id
        return None

    def _effect_list(self) -> list[str]:
        return [self._scene_name(str(item.get("id"))) for item in self._scenes() if item.get("id")]

    def _set_modes(self) -> None:
        models = self._color_models()
        has_hs = "hsv" in models or self._state(CAP_COLOR, "hsv") is not None
        has_rgb = "rgb" in models or self._state(CAP_COLOR, "rgb") is not None
        has_temp = self._has_color_capability("temperature_k")
        has_brightness = self._cap(CAP_RANGE, "brightness") is not None
        if has_hs:
            modes: set[ColorMode] = {ColorMode.HS}
            if has_temp:
                modes.add(ColorMode.COLOR_TEMP)
            self._attr_color_mode = ColorMode.HS
        elif has_rgb:
            modes = {ColorMode.RGB}
            if has_temp:
                modes.add(ColorMode.COLOR_TEMP)
            self._attr_color_mode = ColorMode.RGB
        elif has_temp:
            modes = {ColorMode.COLOR_TEMP}
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif has_brightness:
            modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF
        self._attr_supported_color_modes = modes
        self._attr_supported_features = LightEntityFeature.EFFECT if self._scenes() else LightEntityFeature(0)

    @property
    def is_on(self) -> bool:
        return bool(self._state(CAP_ON_OFF, "on"))

    @property
    def available(self) -> bool:
        state = self.current.get("state")
        return super().available if state is None else str(state).lower() == "online"

    @property
    def brightness(self) -> int | None:
        value = self._state(CAP_RANGE, "brightness")
        return round(float(value) * 255 / 100) if value is not None else None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        value = self._state(CAP_COLOR, "hsv")
        return (float(value.get("h", 0)), float(value.get("s", 0))) if isinstance(value, dict) else None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        value = self._state(CAP_COLOR, "rgb")
        if isinstance(value, int):
            return ((value >> 16) & 255, (value >> 8) & 255, value & 255)
        hsv = self._state(CAP_COLOR, "hsv")
        if isinstance(hsv, dict):
            r, g, b = colorsys.hsv_to_rgb(float(hsv.get("h", 0)) / 360, float(hsv.get("s", 0)) / 100, float(hsv.get("v", 0)) / 100)
            return round(r * 255), round(g * 255), round(b * 255)
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        value = self._state(CAP_COLOR, "temperature_k")
        return int(value) if value is not None else None

    def _temperature_range(self) -> tuple[int, int]:
        temp = ((self._cap(CAP_COLOR) or {}).get("parameters") or {}).get("temperature_k") or {}
        return int(temp.get("min", 2700)), int(temp.get("max", 6500))

    @property
    def min_color_temp_kelvin(self) -> int:
        return self._temperature_range()[0]

    @property
    def max_color_temp_kelvin(self) -> int:
        return self._temperature_range()[1]

    @property
    def effect_list(self) -> list[str] | None:
        effects = self._effect_list()
        return effects or None

    @property
    def effect(self) -> str | None:
        state = (self._cap(CAP_COLOR) or {}).get("state") or {}
        if state.get("instance") == "scene" and isinstance(state.get("value"), str):
            return self._scene_name(state["value"])
        internal = state.get("internal_state") or {}
        color_id = internal.get("color_id")
        if isinstance(color_id, str) and color_id in {str(x.get("id")) for x in self._scenes()}:
            return self._scene_name(color_id)
        return None

    def _brightness_value(self) -> int:
        value = self._state(CAP_RANGE, "brightness")
        return max(1, min(100, int(round(float(value))))) if isinstance(value, (int, float)) else 100

    @property
    def _mode_name(self) -> str | None:
        state = (self._cap(CAP_COLOR) or {}).get("state") or {}
        if state.get("instance") == "scene":
            return "Сцена"
        internal = state.get("internal_state") or {}
        if internal.get("color_id") and str(internal["color_id"]) in {str(x.get("id")) for x in self._scenes()}:
            return "Сцена"
        models = self._color_models()
        if "hsv" in models: return "HSV"
        if "rgb" in models: return "RGB"
        if self._has_color_capability("temperature_k"): return "Цветовая температура"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        current, info = self.current, self.current.get("device_info") or {}
        color_params = (self._cap(CAP_COLOR) or {}).get("parameters") or {}
        brightness_value = self._state(CAP_RANGE, "brightness")
        room = current.get("room") or current.get("room_name") or info.get("room")
        group = current.get("group") or current.get("group_name") or current.get("groups")
        return {
            "yandex_online": str(current.get("state", "")).lower() == "online", "yandex_power": self.is_on,
            "yandex_brightness": int(brightness_value) if brightness_value is not None else None,
            "yandex_color": self._color_name(), "yandex_temperature": self.color_temp_kelvin,
            "yandex_mode": self._mode_name, "yandex_effect": self.effect, "yandex_effects": self.effect_list,
            "yandex_device_id": self.device_id, "yandex_device_type": current.get("type"), "yandex_state": current.get("state"),
            "yandex_room": self._display_value(room), "yandex_group": self._display_value(group),
            "yandex_manufacturer": info.get("manufacturer"), "yandex_model": info.get("model"),
            "yandex_color_model": ", ".join(sorted(self._color_models())) or None,
            "yandex_brightness_min": ((self._cap(CAP_RANGE, "brightness") or {}).get("parameters") or {}).get("range", {}).get("min"),
            "yandex_brightness_max": ((self._cap(CAP_RANGE, "brightness") or {}).get("parameters") or {}).get("range", {}).get("max"),
            "yandex_temperature_min": (color_params.get("temperature_k") or {}).get("min"),
            "yandex_temperature_max": (color_params.get("temperature_k") or {}).get("max"),
        }

    def _color_name(self) -> str | None:
        hsv = self._state(CAP_COLOR, "hsv")
        if not isinstance(hsv, dict):
            return None
        h, s = float(hsv.get("h", 0)) % 360, float(hsv.get("s", 0))
        if s < 10: return "Белый"
        if h < 15 or h >= 345: return "Красный"
        if h < 45: return "Оранжевый"
        if h < 75: return "Жёлтый"
        if h < 165: return "Зелёный"
        if h < 195: return "Бирюзовый"
        if h < 255: return "Синий"
        if h < 285: return "Фиолетовый"
        return "Пурпурный"

    @staticmethod
    def _display_value(value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None: return value
        if isinstance(value, list): return ", ".join(str(x.get("name", x)) if isinstance(x, dict) else str(x) for x in value)
        return str(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        actions: list[dict[str, Any]] = []
        if self._cap(CAP_ON_OFF, "on"):
            actions.append(on_off(True))
        if ATTR_EFFECT in kwargs and kwargs[ATTR_EFFECT] in (self.effect_list or []):
            scene_id = self._scene_id_by_name(kwargs[ATTR_EFFECT])
            if scene_id:
                actions.append(scene_action(scene_id))
        elif ATTR_BRIGHTNESS in kwargs and self._cap(CAP_RANGE, "brightness"):
            actions.append(brightness_action(kwargs[ATTR_BRIGHTNESS] * 100 / 255))
        models = self._color_models()
        if ATTR_HS_COLOR in kwargs and "hsv" in models:
            h, s = kwargs[ATTR_HS_COLOR]
            brightness_ha = kwargs.get(ATTR_BRIGHTNESS, self.brightness or 255)
            v = max(1, min(100, round(float(brightness_ha) * 100 / 255)))
            actions.append(hsv_action(h, s, v))
        elif ATTR_RGB_COLOR in kwargs and self._cap(CAP_COLOR):
            r, g, b = (int(x) for x in kwargs[ATTR_RGB_COLOR])
            if "hsv" in models:
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                actions.append(hsv_action(h * 360, s * 100, v * 100))
            elif "rgb" in models:
                actions.append(rgb_action(r, g, b))
        if ATTR_COLOR_TEMP_KELVIN in kwargs and self._has_color_capability("temperature_k"):
            actions.append(temperature_action(kwargs[ATTR_COLOR_TEMP_KELVIN], *self._temperature_range()))
        if actions:
            await self.coordinator.async_action(self.device_id, actions)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._cap(CAP_ON_OFF, "on"):
            await self.coordinator.async_action(self.device_id, [on_off(False)])


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up Yandex light entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([YandexLight(coordinator, device_id, device) for device_id, device in coordinator.data.items() if device.get("type", "").startswith("devices.types.light")])
