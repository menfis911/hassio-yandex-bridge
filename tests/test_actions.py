"""Executable contract tests for Yandex Smart Home action payloads and light groups."""
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]
ACTIONS_PATH = ROOT / "custom_components" / "yandex_ha_bridge" / "actions.py"
GROUP_PATH = ROOT / "custom_components" / "yandex_ha_bridge" / "groups.py"
LIGHT_PATH = ROOT / "custom_components" / "yandex_ha_bridge" / "light.py"
spec = importlib.util.spec_from_file_location("yandex_ha_bridge_actions", ACTIONS_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

CAP_ON_OFF = "devices.capabilities.on_off"
CAP_RANGE = "devices.capabilities.range"
CAP_COLOR = "devices.capabilities.color_setting"

assert module.on_off(True) == {"type": CAP_ON_OFF, "state": {"instance": "on", "value": True}}
assert module.brightness(55.6) == {"type": CAP_RANGE, "state": {"instance": "brightness", "value": 56}}
assert module.brightness(-10)["state"]["value"] == 0
assert module.brightness(110)["state"]["value"] == 100

hsv_payload = module.hsv(224.0, 55.7, 99.6)
assert hsv_payload == {
    "type": CAP_COLOR,
    "state": {"instance": "hsv", "value": {"h": 224, "s": 56, "v": 100}},
}
assert all(isinstance(hsv_payload["state"]["value"][key], int) for key in ("h", "s", "v"))
assert module.hsv(-1, 101, 101)["state"]["value"] == {"h": 0, "s": 100, "v": 100}
assert module.hsv(361, -1, -1)["state"]["value"] == {"h": 360, "s": 0, "v": 0}

assert module.rgb(255, 128, 1) == {
    "type": CAP_COLOR,
    "state": {"instance": "rgb", "value": 16744449},
}
assert module.rgb(999, -10, 300)["state"]["value"] == 16711935

assert module.temperature_k(4000.4, 2700, 6500) == {
    "type": CAP_COLOR,
    "state": {"instance": "temperature_k", "value": 4000},
}
assert module.temperature_k(1000, 2700, 6500)["state"]["value"] == 2700
assert module.temperature_k(8000, 2700, 6500)["state"]["value"] == 6500

scene_payload = module.scene("party")
assert scene_payload == {
    "type": CAP_COLOR,
    "state": {"instance": "scene", "value": "party"},
}
assert scene_payload["state"]["instance"] != "color_scene"

# 0.6.0 light-group contract: existing individual lights remain the source
# entities, while a separate aggregate light proxies standard light actions.
group_source = GROUP_PATH.read_text(encoding="utf-8")
light_source = LIGHT_PATH.read_text(encoding="utf-8")
assert "class YandexLightsGroup" in group_source
assert "light", "turn_on" in group_source
assert "light", "turn_off" in group_source
assert "_yandex_lights_group" in group_source
assert "YandexLightsGroup" in light_source
assert "if len(lights) >= 2" in light_source
assert "entities = list(lights)" in light_source

print("Yandex action and light-group contract tests passed")
