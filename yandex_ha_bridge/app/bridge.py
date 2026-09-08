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
VERSION = "0.3.3"
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


def save_selected(device_ids):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"device_ids": sorted(set(device_ids))}, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)
