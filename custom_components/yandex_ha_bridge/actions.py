"""Builders for Yandex Smart Home device actions.

Keep all control payload construction in one place so light and select
entities cannot drift apart from the Yandex API action schema.
"""
from __future__ import annotations

from typing import Any

CAP_ON_OFF = "devices.capabilities.on_off"
CAP_RANGE = "devices.capabilities.range"
CAP_COLOR = "devices.capabilities.color_setting"


def on_off(value: bool) -> dict[str, Any]:
    return {"type": CAP_ON_OFF, "state": {"instance": "on", "value": bool(value)}}


def brightness(value: int | float) -> dict[str, Any]:
    return {
        "type": CAP_RANGE,
        "state": {"instance": "brightness", "value": max(0, min(100, int(round(float(value)))))} ,
    }


def hsv(h: int | float, s: int | float, v: int | float) -> dict[str, Any]:
    """Build a Yandex HSV action using the API-required integer fields."""
    return {
        "type": CAP_COLOR,
        "state": {
            "instance": "hsv",
            "value": {
                "h": max(0, min(360, int(round(float(h))))),
                "s": max(0, min(100, int(round(float(s))))),
                "v": max(0, min(100, int(round(float(v))))),
            },
        },
    }


def rgb(r: int, g: int, b: int) -> dict[str, Any]:
    return {
        "type": CAP_COLOR,
        "state": {
            "instance": "rgb",
            "value": (int(r) << 16) | (int(g) << 8) | int(b),
        },
    }


def temperature_k(value: int | float, minimum: int, maximum: int) -> dict[str, Any]:
    value_int = max(int(minimum), min(int(maximum), int(round(float(value)))))
    return {
        "type": CAP_COLOR,
        "state": {"instance": "temperature_k", "value": value_int},
    }


def scene(scene_id: str) -> dict[str, Any]:
    """Build a Yandex color scene action.

    ``color_scene`` is the capability parameter name; the action instance
    is ``scene`` according to the Yandex device action API.
    """
    return {
        "type": CAP_COLOR,
        "state": {"instance": "scene", "value": str(scene_id)},
    }
