"""Light group entity for the selected Yandex lights."""
from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YandexDataUpdateCoordinator

CAP_ON_OFF = "devices.capabilities.on_off"
CAP_RANGE = "devices.capabilities.range"
CAP_COLOR = "devices.capabilities.color_setting"


class YandexLightsGroup(CoordinatorEntity[YandexDataUpdateCoordinator], LightEntity):
    """Control all selected Yandex lights as one Home Assistant light."""

    _attr_has_entity_name = False
    _attr_name = "Лампы Яндекса"
    _attr_suggested_object_id = "yandex_lights"

    def __init__(self, hass: HomeAssistant, coordinator: YandexDataUpdateCoordinator, device_ids: list[str]) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self.device_ids = tuple(device_ids)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_yandex_lights_group"
        self._attr_icon = "mdi:lightbulb-group"
        self._refresh_capabilities()

    @staticmethod
    def _device_modes(device: dict[str, Any]) -> set[ColorMode]:
        capabilities = device.get("capabilities", [])
        capabilities = capabilities if isinstance(capabilities, list) else []

        def cap(capability_type: str, instance: str | None = None) -> dict[str, Any] | None:
            for item in capabilities:
                if item.get("type") != capability_type:
                    continue
                if instance is None:
                    return item
                state = item.get("state") or {}
                params = item.get("parameters") or {}
                if state.get("instance") == instance or params.get("instance") == instance:
                    return item
            return None

        color = cap(CAP_COLOR)
        params = (color or {}).get("parameters") or {}
        raw_models = params.get("color_model")
        models = {raw_models.lower()} if isinstance(raw_models, str) else {
            str(model).lower() for model in raw_models
        } if isinstance(raw_models, (list, tuple, set)) else set()
        state = (color or {}).get("state") or {}
        has_hs = "hsv" in models or state.get("instance") == "hsv"
        has_rgb = "rgb" in models or state.get("instance") == "rgb"
        has_temp = isinstance(params.get("temperature_k"), dict) or state.get("instance") == "temperature_k"
        has_brightness = cap(CAP_RANGE, "brightness") is not None

        if has_hs:
            modes = {ColorMode.HS}
            if has_temp:
                modes.add(ColorMode.COLOR_TEMP)
            return modes
        if has_rgb:
            modes = {ColorMode.RGB}
            if has_temp:
                modes.add(ColorMode.COLOR_TEMP)
            return modes
        if has_temp:
            return {ColorMode.COLOR_TEMP}
        if has_brightness:
            return {ColorMode.BRIGHTNESS}
        return {ColorMode.ONOFF}

    def _refresh_capabilities(self) -> None:
        devices = [self.coordinator.data.get(device_id) for device_id in self.device_ids]
        devices = [device for device in devices if device]
        if not devices:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_supported_features = LightEntityFeature(0)
            return

        mode_sets = [self._device_modes(device) for device in devices]
        common_modes = set.intersection(*mode_sets)
        if not common_modes:
            common_modes = {ColorMode.ONOFF}
        self._attr_supported_color_modes = common_modes
        self._attr_color_mode = self._current_common_mode(common_modes)

        if all(self._device_effects(device) for device in devices):
            self._attr_supported_features = LightEntityFeature.EFFECT
        else:
            self._attr_supported_features = LightEntityFeature(0)

    def _device_effects(self, device: dict[str, Any]) -> list[str]:
        for capability in device.get("capabilities", []) or []:
            if capability.get("type") != CAP_COLOR:
                continue
            scenes = (((capability.get("parameters") or {}).get("color_scene") or {}).get("scenes"))
            if isinstance(scenes, list):
                return [str(item.get("name") or item.get("id")) for item in scenes if item.get("id")]
        return []

    def _current_common_mode(self, supported: set[ColorMode]) -> ColorMode:
        for state in self._member_states():
            mode = state.attributes.get("color_mode")
            if mode in supported:
                return mode
        return next(iter(supported))

    def _member_entity_ids(self) -> list[str]:
        registry = er.async_get(self.hass)
        result: list[str] = []
        for device_id in self.device_ids:
            entity_id = registry.async_get_entity_id("light", DOMAIN, f"{device_id}_light")
            if entity_id and self.hass.states.get(entity_id):
                result.append(entity_id)
        return result

    def _member_states(self):
        return [self.hass.states.get(entity_id) for entity_id in self._member_entity_ids()]

    def _handle_coordinator_update(self) -> None:
        self._refresh_capabilities()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        states = self._member_states()
        return bool(states) and any(state.state not in ("unavailable", "unknown") for state in states)

    @property
    def is_on(self) -> bool:
        return any(state.state == "on" for state in self._member_states())

    @property
    def brightness(self) -> int | None:
        values = [state.attributes.get(ATTR_BRIGHTNESS) for state in self._member_states()]
        values = [int(value) for value in values if isinstance(value, (int, float))]
        return round(sum(values) / len(values)) if values else None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        values = [state.attributes.get(ATTR_HS_COLOR) for state in self._member_states()]
        values = [value for value in values if isinstance(value, (tuple, list)) and len(value) == 2]
        if not values:
            return None
        if all(tuple(value) == tuple(values[0]) for value in values[1:]):
            return (float(values[0][0]), float(values[0][1]))
        return None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        values = [state.attributes.get(ATTR_RGB_COLOR) for state in self._member_states()]
        values = [value for value in values if isinstance(value, (tuple, list)) and len(value) == 3]
        if not values:
            return None
        if all(tuple(value) == tuple(values[0]) for value in values[1:]):
            return tuple(int(value) for value in values[0])
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        values = [state.attributes.get(ATTR_COLOR_TEMP_KELVIN) for state in self._member_states()]
        values = [int(value) for value in values if isinstance(value, (int, float))]
        return round(sum(values) / len(values)) if values else None

    @property
    def min_color_temp_kelvin(self) -> int:
        values = [state.attributes.get("min_color_temp_kelvin") for state in self._member_states()]
        values = [int(value) for value in values if isinstance(value, (int, float))]
        return max(values) if values else 2000

    @property
    def max_color_temp_kelvin(self) -> int:
        values = [state.attributes.get("max_color_temp_kelvin") for state in self._member_states()]
        values = [int(value) for value in values if isinstance(value, (int, float))]
        return min(values) if values else 6500

    @property
    def effect_list(self) -> list[str] | None:
        states = self._member_states()
        lists = [set(state.attributes.get("effect_list") or []) for state in states]
        if not lists or not all(lists):
            return None
        common = set.intersection(*lists)
        return sorted(common) or None

    @property
    def effect(self) -> str | None:
        effects = [state.attributes.get(ATTR_EFFECT) for state in self._member_states()]
        effects = [effect for effect in effects if effect]
        return effects[0] if effects and all(effect == effects[0] for effect in effects) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "yandex_group": True,
            "member_count": len(self._member_entity_ids()),
            "member_entities": self._member_entity_ids(),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        entity_ids = self._member_entity_ids()
        if not entity_ids:
            return
        service_data = dict(kwargs)
        service_data["entity_id"] = entity_ids
        await self.hass.services.async_call("light", "turn_on", service_data, blocking=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        entity_ids = self._member_entity_ids()
        if not entity_ids:
            return
        await self.hass.services.async_call(
            "light", "turn_off", {"entity_id": entity_ids}, blocking=True
        )


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    """Set up one group containing all selected Yandex light entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    device_ids = [
        device_id
        for device_id, device in coordinator.data.items()
        if device.get("type", "").startswith("devices.types.light")
    ]
    if len(device_ids) >= 2:
        async_add_entities([YandexLightsGroup(hass, coordinator, device_ids)])
