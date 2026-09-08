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
VERSION = "0.3.5"
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


def api_get(path, token):
    req = urllib.request.Request(
        API + path,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_devices(token):
    return api_get("/v1.0/user/info", token).get("devices", [])


def render_page(devices, selected):
    rows = []
    for d in devices:
        device_id = str(d.get("id", ""))
        info = d.get("device_info", {}) or {}
        name = html.escape(str(d.get("name") or "Без имени"))
        model = html.escape(str(info.get("model") or "—"))
        dtype = html.escape(str(d.get("type") or "—"))
        checked = " checked" if device_id in selected else ""
        rows.append(
            f'<label class="device"><input type="checkbox" name="device_id" value="{html.escape(device_id)}"{checked}>'
            f'<span><b>{name}</b><small>{model} · {dtype}</small><code>{html.escape(device_id)}</code></span></label>'
        )
    body = "\n".join(rows) or '<p class="empty">Устройства не найдены или токен не настроен.</p>'
    return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Yandex HA Bridge</title><style>
body{{font-family:system-ui,-apple-system,sans-serif;max-width:900px;margin:0 auto;padding:24px;background:#f5f5f5;color:#222}}
main{{background:white;border-radius:14px;padding:24px;box-shadow:0 2px 12px #0001}}h1{{margin-top:0}}
.device{{display:flex;gap:14px;align-items:flex-start;padding:14px;border:1px solid #ddd;border-radius:10px;margin:8px 0;cursor:pointer}}
.device:hover{{background:#fafafa}}input{{width:20px;height:20px;margin-top:2px}}small,code{{display:block;margin-top:4px;color:#666}}code{{font-size:11px;word-break:break-all}}
button{{margin-top:18px;padding:10px 18px;border:0;border-radius:8px;cursor:pointer;font-size:15px}}.primary{{background:#111;color:white}}
.hint{{color:#666}}.empty{{color:#a00}}
</style></head><body><main>
<h1>Yandex HA Bridge</h1><p class="hint">Веб-панель оставлена для диагностики. Основной способ добавить устройства: Настройки → Устройства и службы → Добавить интеграцию → Yandex HA Bridge.</p>
<p class="hint">Выбор ниже сохраняется локально в App и используется для технической диагностики.</p>
<form method="post" action="/save">{body}<button class="primary" type="submit">Сохранить диагностический выбор</button></form>
</main></body></html>'''


class WebHandler(BaseHTTPRequestHandler):
    server_version = "YandexHABridge/0.3.5"

    def log_message(self, fmt, *args):
        LOG.debug("Web UI: " + fmt, *args)

    def send_html(self, status, body):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if self.path != "/":
            self.send_html(404, "<h1>404</h1>")
            return
        try:
            devices = fetch_devices(self.server.token)
            selected = load_selected()
            self.send_html(200, render_page(devices, selected))
        except urllib.error.HTTPError as e:
            self.send_html(502, f"<h1>Ошибка API: HTTP {e.code}</h1><p>Проверьте OAuth-токен и права iot:view.</p>")
        except Exception as e:
            LOG.exception("Ошибка Web UI: %s", e)
            self.send_html(500, "<h1>Ошибка</h1><p>Не удалось получить список устройств.</p>")

    def do_POST(self):
        if self.path != "/save":
            self.send_html(404, "<h1>404</h1>")
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        values = urllib.parse.parse_qs(raw).get("device_id", [])
        try:
            devices = fetch_devices(self.server.token)
            valid_ids = {str(d.get("id")) for d in devices}
            selected = [x for x in values if x in valid_ids]
            save_selected(selected)
            LOG.info("Сохранён диагностический выбор устройств: %s", len(selected))
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
        except Exception as e:
            LOG.exception("Не удалось сохранить выбор устройств: %s", e)
            self.send_html(500, "<h1>Ошибка сохранения</h1>")


def start_web(token):
    server = ThreadingHTTPServer(("0.0.0.0", WEB_PORT), WebHandler)
    server.token = token
    LOG.info("Веб-интерфейс диагностики запущен на порту %s", WEB_PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()


def main():
    options = load_options()
    token = (options.get("yandex_oauth_token") or "").strip()
    interval = max(10, int(options.get("poll_interval", 30)))
    level = getattr(logging, str(options.get("log_level", "info")).upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    LOG.info("Yandex HA Bridge v%s запускается", VERSION)

    if not token:
        LOG.error("OAuth-токен Яндекса не настроен. Добавьте его в разделе «Конфигурация» приложения.")
        while True:
            time.sleep(300)

    start_web(token)
    LOG.info("Основная работа с устройствами выполняется через интеграцию Yandex HA Bridge в Home Assistant")

    while True:
        try:
            data = api_get("/v1.0/user/info", token)
            LOG.info("Соединение с API Яндекс Умного дома установлено")
            devices = data.get("devices", [])
            selected = load_selected()
            if not selected:
                LOG.info("Диагностические устройства не выбраны. Основной выбор выполняется в интеграции Home Assistant.")
            else:
                selected_devices = [d for d in devices if str(d.get("id")) in selected]
                LOG.info("Диагностически выбрано устройств: %s из %s доступных", len(selected_devices), len(devices))
                for device in selected_devices:
                    info = device.get("device_info", {}) or {}
                    LOG.info("Проверка: id=%s, имя=%s, модель=%s", device.get("id"), device.get("name"), info.get("model"))
                    state = api_get("/v1.0/devices/" + str(device["id"]), token)
                    LOG.debug("Состояние %s: %s", device.get("name"), json.dumps(state, ensure_ascii=False))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                LOG.error("Ошибка авторизации Яндекс API (HTTP %s). Проверьте OAuth-токен и права iot:view.", e.code)
            else:
                LOG.error("Яндекс API вернул HTTP %s", e.code)
        except urllib.error.URLError as e:
            LOG.error("Не удалось подключиться к API Яндекса: %s", e.reason)
        except Exception as e:
            LOG.exception("Ошибка цикла моста: %s", e)
        time.sleep(interval)


if __name__ == "__main__":
    main()
