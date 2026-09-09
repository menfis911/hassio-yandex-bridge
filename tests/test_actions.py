"""Executable contract tests for Yandex Smart Home action payloads."""
from __future__ import annotations

from custom_components.yandex_ha_bridge.actions import (
    brightness,
    hsv,
    on_off,
    rgb,
    scene,
    temperature_k,
)


CAP_ON_OFF = "devices.capabilities.on_off"
CAP_RANGE = "devices.capabilities.range"
CAP_COLOR = "devices.capabilities.color_setting"


def test_on_off() -> None:
    assert on_off(True) == {
        "type": CAP_ON_OFF,
        "state": {"instance": "on", "value": True},
    }


def test_brightness_is_integer_and_clamped() -> None:
    assert brightness(55.6) == {
        "type": CAP_RANGE,
        "state": {"instance": "brightness", "value": 56},
    }
    assert brightness(-10) ["state"]["value"] == 0
    assert brightness(110) ["state"]["value"] == 100


def test_hsv_uses_integer_fields_and_valid_ranges() -> None:
    payload = hsv(224.0, 55.7, 99.6)
    assert payload == {
        "type": CAP_COLOR,
        "state": {
            "instance": "hsv",
            "value": {"h": 224, "s": 56, "v": 100},
        },
    }
    assert all(isinstance(payload["state"]["value"][key], int) for key in ("h", "s", "v"))
    assert hsv(-1, 101, 101)["state"]["value"] == {"h": 0, "s": 100, "v": 100}
    assert hsv(361, -1, -1)["state"]["value"] == {"h": 360, "s": 0, "v": 0}


def test_rgb_is_yandex_integer_rgb_value() -> None:
    assert rgb(255, 128, 1) == {
        "type": CAP_COLOR,
        "state": {"instance": "rgb", "value": 16744449},
    }


def test_temperature_is_integer_and_clamped_to_device_range() -> None:
    assert temperature_k(4000.4, 2700, 6500) == {
        "type": CAP_COLOR,
        "state": {"instance": "temperature_k", "value": 4000},
    }
    assert temperature_k(1000, 2700, 6500)["state"]["value"] == 2700
    assert temperature_k(8000, 2700, 6500)["state"]["value"] == 6500


def test_scene_uses_scene_instance_not_color_scene() -> None:
    payload = scene("party")
    assert payload == {
        "type": CAP_COLOR,
        "state": {"instance": "scene", "value": "party"},
    }
    assert payload["state"]["instance"] != "color_scene"
