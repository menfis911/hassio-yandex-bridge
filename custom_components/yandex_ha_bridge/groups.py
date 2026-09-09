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

    def _refresh_capabilities(self) -> None:
        states = self._member_states()
        if not states:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_supported_features = LightEntityFeature(0)
            return

        mode_sets = []
        for state in states:
            raw = state.attributes.get(ATTR_SUPPORTED_COLOR_MODES, [])
            mode_sets.append(set(raw))
        common_modes = set.intersection(*mode_sets) if mode_sets else set()
        if not common_modes:
            common_modes = {ColorMode.ONOFF}
        self._attr_supported_color_modes = common_modes
        self._attr_color_mode = self._current_common_mode(states, common_modes)
        if all(state.attributes.get("effect_list") for state in states):
            self._attr_supported_features = LightEntityFeature.EFFECT
        else:
            self._attr_supported_features = LightEntityFeature(0)

    @staticmethod
    def _current_common_mode(states, supported: set[ColorMode]) -> ColorMode:
        for state in states:
            mode = state.attributes.get("color_mode")
            if mode in supported:
                return mode
        return next(iter(supported))

    async def async_update(self) -> None:
        """Refresh group capabilities and state from member entities."""
        self._refresh_capabilities()

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
