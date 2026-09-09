"""Yandex light presets and scenes."""
from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .actions import hsv as hsv_action
from .actions import on_off
from .actions import scene as scene_action
from .const import DOMAIN
from .coordinator import YandexDataUpdateCoordinator

CAP_ON_OFF = "devices.capabilities.on_off"
CAP_RANGE = "devices.capabilities.range"
CAP_COLOR = "devices.capabilities.color_setting"

# Temperature presets deliberately do not live here. Home Assistant's light
# entity already provides native color-temperature control. This selector is
# for colors and Yandex scenes/modes only.
PRESETS: dict[str, dict[str, Any]] = {
    "Тёплый цвет": {"kind": "hsv", "value": {"h": 30, "s": 65}},
    "Красный": {"kind": "hsv", "value": {"h": 0, "s": 100}},
    "Зелёный": {"kind": "hsv", "value": {"h": 120, "s": 100}},
    "Синий": {"kind": "hsv", "value": {"h": 240, "s": 100}},
}

SCENE_NAMES: dict[str, str] = {
    "miracle": "Чудо", "fairy": "Сказочные огни", "northern": "Северное сияние", "christmas": "Рождество",
    "alice": "Алиса", "party": "Вечеринка", "jungle": "Джунгли", "neon": "Неон", "night": "Ночь",
    "ocean": "Океан", "romance": "Романтика", "candle": "Свеча", "siren": "Сирена", "alarm": "Тревога",
    "fantasy": "Фантазия", "reading": "Чтение",
}


class YandexLightPresetSelect(CoordinatorEntity[YandexDataUpdateCoordinator], SelectEntity):
    """Quick colors and Yandex scenes for a light."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:palette"

    def __init__(self, coordinator: YandexDataUpdateCoordinator, device_id: str, device: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self.device_id, self.device = device_id, device
        self._attr_unique_id = f"{device_id}_presets"
        self._attr_name = "Режим"
        info = device.get("device_info") or {}
        room = device.get("room") or device.get("room_name") or info.get("room")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)}, name=device.get("name") or "Yandex light",
            manufacturer=info.get("manufacturer"), model=info.get("model"), serial_number=device_id,
            suggested_area=room,
        )
        self._update_options()

    @property
    def current(self) -> dict[str, Any]:
        return self.coordinator.data.get(self.device_id, self.device)

    def _color_cap(self) -> dict[str, Any] | None:
        for cap in self.current.get("capabilities", []):
            if cap.get("type") == CAP_COLOR:
                return cap
        return None

    def _models(self) -> set[str]:
        params = (self._color_cap() or {}).get("parameters") or {}
        raw = params.get("color_model")
        if isinstance(raw, str): return {raw.lower()}
        if isinstance(raw, (list, tuple, set)): return {str(x).lower() for x in raw}
        return set()

    def _scenes(self) -> list[dict[str, Any]]:
        scenes = (((self._color_cap() or {}).get("parameters") or {}).get("color_scene") or {}).get("scenes", [])
        return scenes if isinstance(scenes, list) else []

    def _update_options(self) -> None:
        models = self._models()
        options: list[str] = []
        if "hsv" in models or "rgb" in models:
            options.extend(PRESETS)
        for item in self._scenes():
            scene_id = str(item.get("id", ""))
            if scene_id:
                name = str(item.get("name") or SCENE_NAMES.get(scene_id, scene_id))
                if name not in options:
                    options.append(name)
        self._attr_options = options

    def _scene_by_name(self, name: str) -> str | None:
        for item in self._scenes():
            scene_id = str(item.get("id", ""))
            if str(item.get("name") or SCENE_NAMES.get(scene_id, scene_id)) == name:
                return scene_id
        return None

    def _brightness_value(self) -> int:
        for cap in self.current.get("capabilities", []):
            if cap.get("type") != CAP_RANGE:
                continue
            params, state = cap.get("parameters") or {}, cap.get("state") or {}
            if params.get("instance") == "brightness" or state.get("instance") == "brightness":
                value = state.get("value")
                if isinstance(value, (int, float)):
                    return max(1, min(100, int(round(float(value)))))
        return 100

    @property
    def current_option(self) -> str | None:
        self._update_options()
        cap = self._color_cap() or {}
        state = cap.get("state") or {}
        instance, value = state.get("instance"), state.get("value")
        if instance == "scene" and isinstance(value, str):
            name = SCENE_NAMES.get(value)
            if name in self.options: return name
            for item in self._scenes():
                if str(item.get("id")) == value: return str(item.get("name") or value)
        internal = state.get("internal_state") or {}
        color_id = internal.get("color_id")
        if isinstance(color_id, str):
            name = SCENE_NAMES.get(color_id)
            if name in self.options: return name
            for item in self._scenes():
                if str(item.get("id")) == color_id: return str(item.get("name") or color_id)
        return None

    async def async_select_option(self, option: str) -> None:
        self._update_options()
        color_cap = self._color_cap()
        if not color_cap or option not in self.options:
            return
        preset = PRESETS.get(option)
        if preset:
            p = preset["value"]
            action = hsv_action(p["h"], p["s"], self._brightness_value())
        else:
            scene_id = self._scene_by_name(option)
            if not scene_id:
                return
            action = scene_action(scene_id)
        actions = [on_off(True)] if any(c.get("type") == CAP_ON_OFF for c in self.current.get("capabilities", [])) else []
        actions.append(action)
        await self.coordinator.async_action(self.device_id, actions)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "yandex_device_id": self.device_id,
            "preset_count": len(PRESETS),
            "scene_count": len(self._scenes()),
            "temperature_presets": False,
        }


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up preset selectors for Yandex lights."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        YandexLightPresetSelect(coordinator, device_id, device)
        for device_id, device in coordinator.data.items()
        if device.get("type", "").startswith("devices.types.light")
        and any(cap.get("type") == CAP_COLOR for cap in device.get("capabilities", []))
    ])
