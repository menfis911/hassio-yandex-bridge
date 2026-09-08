#!/usr/bin/env python3
import json
import logging
import os
import time
import urllib.error
import urllib.request

LOG = logging.getLogger("yandex_ha_bridge")
API = "https://api.iot.yandex.net"


def load_options():
    with open("/data/options.json", "r", encoding="utf-8") as f:
        return json.load(f)


def api_get(path, token):
    req = urllib.request.Request(
        API + path,
        headers={"Authorization": f"OAuth {token}", "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def find_device(data, requested_id):
    devices = data.get("devices", [])
    if requested_id:
        return next((d for d in devices if d.get("id") == requested_id), None)
    return next((d for d in devices if d.get("device_info", {}).get("model") == "YNDX-00019"), None)


def main():
    options = load_options()
    token = (options.get("yandex_oauth_token") or "").strip()
    interval = max(10, int(options.get("poll_interval", 30)))
    level = getattr(logging, str(options.get("log_level", "info")).upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if not token:
        LOG.error("Yandex OAuth token is not configured. Add it in the add-on Configuration tab.")
        while True:
            time.sleep(300)

    LOG.info("Yandex HA Bridge v0.1.0 started")
    LOG.info("Read-only discovery mode; device control is intentionally disabled")

    while True:
        try:
            data = api_get("/v1.0/user/info", token)
            device = find_device(data, (options.get("device_id") or "").strip())
            if not device:
                LOG.warning("YNDX-00019 was not found in Yandex Smart Home")
            else:
                info = device.get("device_info", {})
                LOG.info("Found device: id=%s name=%s model=%s")
                LOG.info("Device ID: %s", device.get("id"))
                LOG.info("Name: %s", device.get("name"))
                LOG.info("Model: %s", info.get("model"))
                LOG.info("Type: %s", device.get("type"))
                LOG.info("Capabilities: %s", [c.get("type") for c in device.get("capabilities", [])])
                state = api_get("/v1.0/devices/" + device["id"], token)
                LOG.info("Current device state received successfully")
                LOG.debug("State: %s", json.dumps(state, ensure_ascii=False))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                LOG.error("Yandex API authorization failed (HTTP %s). Check the OAuth token and scopes.", e.code)
            else:
                LOG.error("Yandex API returned HTTP %s", e.code)
        except Exception as e:
            LOG.exception("Bridge cycle failed: %s", e)
        time.sleep(interval)


if __name__ == "__main__":
    main()
