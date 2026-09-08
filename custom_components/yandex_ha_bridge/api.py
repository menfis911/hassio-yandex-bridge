"""Async wrapper around the official Yandex Smart Home API."""
from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from typing import Any

API = "https://api.iot.yandex.net"


class YandexApiError(Exception):
    """Yandex API error."""

    def __init__(self, message: str, status: int | None = None, request_id: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.request_id = request_id


class YandexApi:
    def __init__(self, token: str) -> None:
        self.token = token

    async def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        def request() -> dict[str, Any]:
            data = json.dumps(payload).encode() if payload is not None else None
            req = urllib.request.Request(
                API + path,
                data=data,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "Yandex-HABridge/0.3.6",
                },
                method=method,
            )
            try:
                with urllib.request.urlopen(req, timeout=20) as response:
                    raw = response.read().decode()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as err:
                raw = err.read().decode(errors="replace")
                details = ""
                request_id = None
                try:
                    body = json.loads(raw) if raw else {}
                    request_id = body.get("request_id")
                    details = body.get("message") or body.get("error_message") or ""
                except json.JSONDecodeError:
                    details = raw.strip()

                if err.code == 403:
                    message = "Yandex API denied the request (HTTP 403). The OAuth token must have the iot:control permission for device actions."
                else:
                    message = f"Yandex API HTTP {err.code}"
                if details:
                    message += f": {details}"
                if request_id:
                    message += f" (request_id={request_id})"
                raise YandexApiError(message, status=err.code, request_id=request_id) from err
            except urllib.error.URLError as err:
                raise YandexApiError(str(err.reason)) from err

        return await asyncio.to_thread(request)

    async def get_user_info(self) -> dict[str, Any]:
        return await self._request("GET", "/v1.0/user/info")

    async def get_devices(self) -> list[dict[str, Any]]:
        return (await self.get_user_info()).get("devices", [])

    async def get_device(self, device_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1.0/devices/{device_id}")

    async def actions(self, device_id: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1.0/devices/actions",
            {"devices": [{"id": device_id, "actions": actions}]},
        )
