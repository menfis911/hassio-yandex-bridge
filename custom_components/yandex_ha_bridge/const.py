from homeassistant.const import Platform

DOMAIN = "yandex_ha_bridge"
NAME = "Yandex HA Bridge"
VERSION = "0.4.0"
CONF_TOKEN = "token"
CONF_DEVICE_IDS = "device_ids"
DEFAULT_SCAN_INTERVAL = 30
PLATFORMS = [Platform.LIGHT, Platform.SELECT]
