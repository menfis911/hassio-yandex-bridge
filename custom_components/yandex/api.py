from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .const import API_BASE


class YandexApiError(Exception):
    """Yandex API error."""


class YandexApi:
    def __init__(self, token: str) -> None:
        self._token = token
        self._session: aiohttp.ClientSession | None = None

    async def async_close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        try:
            async with self._session.request(
                method, API_BASE + path, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                data = await response.json(content_type=None)
                if response.status >= 400:
                    raise YandexApiError(f"HTTP {response.status}: {data}")
                return data
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise YandexApiError(str(err)) from err

    async def async_get_info(self) -> dict[str, Any]:
        return await self._request("GET", "/v1.0/user/info")

    async def async_get_device(self, device_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1.0/devices/{device_id}")

    async def async_actions(self, device_id: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
        return await self._request("POST", "/v1.0/devices/actions", {"devices": [{"id": device_id, "actions": actions}]})
