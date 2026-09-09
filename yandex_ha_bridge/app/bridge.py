#!/usr/bin/env python3
import html
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = logging.getLogger("yandex_ha_bridge")
API = "https://api.iot.yandex.net"
VERSION = "0.6.0"
DATA_FILE = "/data/selected_devices.json"
WEB_PORT = 8099


def load_options():
    with open("/data/options.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_selected():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(str(x) for x in data.get("device_ids", []))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return set()
