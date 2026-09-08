#!/usr/bin/env python3
import json
import logging
import time
import urllib.error
import urllib.request

LOG = logging.getLogger("yandex_ha_bridge")
API = "https://api.iot.yandex.net"
VERSION = "0.1.1"


def load_options():
    with open("/data/options.json", "r", encoding="utf-8") as f:
        return json.load(f)


def api_get(path, token):
    req = urllib.request.Request(
        API + path,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
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

    LOG.info("Yandex HA Bridge v%s запускается", VERSION)

    if not token:
        LOG.error("OAuth-токен Яндекса не настроен. Добавьте его в разделе «Конфигурация» аддона.")
        while True:
            time.sleep(300)

    LOG.info("Режим только чтения: поиск устройства и получение его состояния")

    while True:
        try:
            data = api_get("/v1.0/user/info", token)
            LOG.info("Соединение с API Яндекс Умного дома установлено")
            device = find_device(data, (options.get("device_id") or "").strip())
            if not device:
                if (options.get("device_id") or "").strip():
                    LOG.warning("Устройство с указанным device_id не найдено")
                else:
                    LOG.warning("Устройство модели YNDX-00019 не найдено в Яндекс Умном доме")
            else:
                info = device.get("device_info", {})
                LOG.info("Найдено устройство: id=%s, имя=%s, модель=%s", device.get("id"), device.get("name"), info.get("model"))
                LOG.info("Тип устройства: %s", device.get("type"))
                LOG.info("Умения: %s", [c.get("type") for c in device.get("capabilities", [])])
                state = api_get("/v1.0/devices/" + device["id"], token)
                LOG.info("Текущее состояние устройства успешно получено")
                LOG.debug("Состояние: %s", json.dumps(state, ensure_ascii=False))
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
