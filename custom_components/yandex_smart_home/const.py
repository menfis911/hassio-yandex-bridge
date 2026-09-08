"""Constants."""
from homeassistant.const import Platform

DOMAIN = "yandex_smart_home"
NAME = "Yandex Smart Home"
VERSION = "0.3.0"
CONF_TOKEN = "token"
CONF_DEVICE_IDS = "device_ids"
DEFAULT_SCAN_INTERVAL = 30
PLATFORMS = [Platform.LIGHT]
