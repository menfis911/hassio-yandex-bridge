"""Constants."""
from homeassistant.const import Platform

DOMAIN = "yandex_ha_bridge"
NAME = "Yandex HA Bridge"
VERSION = "0.3.12"
CONF_TOKEN = "token"
CONF_DEVICE_IDS = "device_ids"
DEFAULT_SCAN_INTERVAL = 30
PLATFORMS = [Platform.LIGHT]
