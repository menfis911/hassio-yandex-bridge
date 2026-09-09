"""Yandex light presets and scenes."""
from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YandexDataUpdateCoordinator

CAP_COLOR = "devices.capabilities.color_setting"

PRESETS: dict[str, dict[str, Any]] = {
    "Тёплый свет": {"kind": "temperature", "value": 2700},
    "Нейтральный свет": {"kind": "temperature", "value": 4000},
    "Холодный свет": {"kind": "temperature", "value": 6500},
    "Красный": {"kind": "hsv", "value": {"h": 0, "s": 100}},
    "Зелёный": {"kind": "hsv", "value": {"h": 120, "s": 100}},
    "Синий": {"kind": "hsv", "value": {"h": 240, "s": 100}},
}

SCENE_NAMES: dict[str, str] = {
    "miracle": "Чудо",
    "fairy": "Сказочные огни",
    "northern": "Северное сияние",
    "christmas": "Рождество",
    "alice": "Алиса",
    "party": "Вечеринка",
    "jungle": "Джунгли",
    "neon": "Неон",
    "night": "Ночь",
    "ocean": "Океан",
    "romance": "Романтика",
    "candle": "Свеча",
    "siren": "Сирена",
    "alarm": "Тревога",
    "fantasy": "Фантазия",
    "reading": "Чтение",
}


class YandexLightPresetSelect(
    CoordinatorEntity[YandexDataUpdateCoordinator], SelectEntity
):
    """Quick presets and Yandex color scenes for a light."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:palette"

    def __init__(self, coordinator: YandexDataUpdateCoordinator, device_id: str, device: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self.device_id = device_id
        self.device = device
        self._attr_unique_id = f"{device_id}_presets"
        self._attr_name = "Режим"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.get("name") or "Yandex light",
            manufacturer=(device.get("device_info") or {}).get("manufacturer"),
            model=(device.get("device_info") or {}).get("model"),
            serial_number=device_id,
        )
        self._attr_options = self._build_options(device)

    @property
    def current(self) -> dict[str, Any]:
        return self.coordinator.data.get(self.device_id, self.device)

    def _color_cap(self) -> dict[str, Any] | None:
        for cap in self.current.get("capabilities", []):
            if cap.get("type") == CAP_COLOR:
                return cap
        return None

    def _build_options(self, device: dict[str, Any]) -> list[str]:
        options = list(PRESETS)
        for scene in self._scenes(device):
            scene_id = str(scene.get("id", ""))
            if not scene_id:
                continue
            name = str(scene.get("name") or SCENE_NAMES.get(scene_id, scene_id))
            if name not in options:
                options.append(name)
        return options

    @staticmethod
    def _scenes(device: dict[str, Any]) -> list[dict[str, Any]]:
        for cap in device.get("capabilities", []):
            if cap.get("type") != CAP_COLOR:
                continue
            params = cap.get("parameters") or {}
            scenes = params.get("color_scene", {}).get("scenes", [])
            if isinstance(scenes, list):
                return [scene for scene in scenes if isinstance(scene, dict)]
        return []

    def _scene_by_name(self, name: str) -> str | None:
        for scene in self._scenes(self.current):
            scene_id = str(scene.get("id", ""))
            scene_name = str(scene.get("name") or SCENE_NAMES.get(scene_id, scene_id))
            if scene_name == name:
                return scene_id
        return None

    @property
    def current_option(self) -> str | None:
        cap = self._color_cap() or {}
        state = cap.get("state") or {}
        internal = state.get("internal_state") or {}
        color_id = internal.get("color_id")

        if color_id == "warm_white":
            return "Тёплый свет"
        if color_id == "cool_white":
            return "Холодный свет"

        value = state.get("value")
        if state.get("instance") == "temperature_k" and isinstance(value, (int, float)):
            nearest = min(
                PRESETS.items(),
                key=lambda item: abs(item[1]["value"] - float(value))
                if item[1]["kind"] == "temperature"
                else float("inf"),
            )
            if nearest[1]["kind"] == "temperature" and abs(nearest[1]["value"] - float(value)) <= 150:
                return nearest[0]

        if isinstance(color_id, str):
            name = SCENE_NAMES.get(color_id)
            if name in self.options:
                return name
            for scene in self._scenes(self.current):
                if str(scene.get("id")) == color_id:
                    return str(scene.get("name") or color_id)

        return None

    async def async_select_option(self, option: str) -> None:
        color_cap = self._color_cap()
        if not color_cap:
            return

        preset = PRESETS.get(option)
        if preset:
            if preset["kind"] == "temperature":
                action = {
                    "type": CAP_COLOR,
                    "state": {
                        "instance": "temperature_k",
                        "value": int(preset["value"]),
                    },
                }
            else:
                hsv = dict(preset["value"])
                current_brightness = self._brightness_value()
                hsv["v"] = current_brightness
                action = {
                    "type": CAP_COLOR,
                    "state": {"instance": "hsv", "value": hsv},
                }
        else:
            scene_id = self._scene_by_name(option)
            if not scene_id:
                return
            action = {
                "type": CAP_COLOR,
                "state": {"instance": "color_scene", "value": scene_id},
            }

        await self.coordinator.async_action(
            self.device_id,
            [
                {"type": "devices.capabilities.on_off", "state": {"instance": "on", "value": True}},
                action,
            ],
        )

    def _brightness_value(self) -> int:
        for cap in self.current.get("capabilities", []):
            if cap.get("type") != "devices.capabilities.range":
                continue
            params = cap.get("parameters") or {}
            state = cap.get("state") or {}
            if params.get("instance") == "brightness" or state.get("instance") == "brightness":
                value = state.get("value")
                if isinstance(value, (int, float)):
                    return max(1, min(100, round(float(value))))
        return 100

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "yandex_device_id": self.device_id,
            "preset_count": len(PRESETS),
            "scene_count": len(self._scenes(self.current)),
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
