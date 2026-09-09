"""Builders for Yandex Smart Home device actions.

All control payload construction lives here so every entity uses the same
Yandex API schema and numeric normalization rules.
"""
from __future__ import annotations

from typing import Any

CAP_ON_OFF = "devices.capabilities.on_off"
CAP_RANGE = "devices.capabilities.range"
CAP_COLOR = "devices.capabilities.color_setting"


def _int_clamp(value: int | float, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(round(float(value)))))


def on_off(value: bool) -> dict[str, Any]:
    return {"type": CAP_ON_OFF, "state": {"instance": "on", "value": bool(value)}}


def brightness(value: int | float) -> dict[str, Any]:
    return {"type": CAP_RANGE, "state": {"instance": "brightness", "value": _int_clamp(value, 0, 100)}}


def hsv(h: int | float, s: int | float, v: int | float) -> dict[str, Any]:
    """Build a Yandex HSV action using integer fields only."""
    return {
        "type": CAP_COLOR,
        "state": {
            "instance": "hsv",
            "value": {
                "h": _int_clamp(h, 0, 360),
                "s": _int_clamp(s, 0, 100),
                "v": _int_clamp(v, 0, 100),
            },
        },
    }


def rgb(r: int | float, g: int | float, b: int | float) -> dict[str, Any]:
    """Build a packed integer RGB action with strict channel bounds."""
    red, green, blue = (_int_clamp(channel, 0, 255) for channel in (r, g, b))
    return {
        "type": CAP_COLOR,
        "state": {"instance": "rgb", "value": (red << 16) | (green << 8) | blue},
    }


def temperature_k(value: int | float, minimum: int, maximum: int) -> dict[str, Any]:
    low, high = sorted((int(minimum), int(maximum)))
    value_int = max(low, min(high, int(round(float(value)))))
    return {"type": CAP_COLOR, "state": {"instance": "temperature_k", "value": value_int}}


def scene(scene_id: str) -> dict[str, Any]:
    """Build a Yandex color scene action.

    ``color_scene`` is the capability parameter name; the action instance is
    ``scene`` according to the Yandex device action API.
    """
    return {"type": CAP_COLOR, "state": {"instance": "scene", "value": str(scene_id)}}
