"""Carrier Cync cloud API client."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_CONTROL, API_WEATHER

_LOGGER = logging.getLogger(__name__)


class CarrierCyncApi:
    """Client for control.php + weather.php."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        member_id: str,
        device_id: str,
        device_model: str,
    ) -> None:
        self._session = session
        self.member_id = member_id
        self.device_id = device_id
        self.device_model = device_model

    def _base_payload(self, command: str) -> dict[str, str]:
        return {
            "command": command,
            "member_id": self.member_id,
            "device_id": self.device_id,
            "device_model": self.device_model,
        }

    async def _post(self, url: str, data: dict[str, str]) -> dict[str, Any]:
        async with self._session.post(
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            resp.raise_for_status()
            result = await resp.json(content_type=None)
            if result.get("message") not in ("success", None) and result.get("code") not in (
                200,
                "200",
                0,
                "0",
            ):
                _LOGGER.warning("Carrier API unexpected response: %s", result)
            return result

    async def get_dt(self) -> dict[str, Any]:
        """Fetch device status (dt map)."""
        result = await self._post(API_CONTROL, self._base_payload("dt"))
        response = result.get("response") or {}
        dt = response.get("dt") or {}
        return {
            "lastdate": response.get("lastdate"),
            "model": response.get("model"),
            "revision": response.get("revision"),
            "deviceid": response.get("deviceid"),
            "dt": {str(k): v for k, v in dt.items()},
        }

    async def get_weather(self) -> dict[str, Any]:
        """Fetch outdoor weather used by the app (temp matches app outdoor)."""
        result = await self._post(API_WEATHER, self._base_payload("weather"))
        response = result.get("response") or {}
        return {
            "location": response.get("location"),
            "temperature": response.get("temperature"),
            "humidity": response.get("humidity"),
            "cloud": response.get("cloud"),
            "icon": response.get("icon"),
        }

    async def get_status(self) -> dict[str, Any]:
        """Coordinator payload (device dt only)."""
        return await self.get_dt()

    async def set_value(self, key: str, val: str | int) -> dict[str, Any]:
        """Write a single control key."""
        data = self._base_payload("control")
        data["key"] = str(key)
        data["val"] = str(val)
        result = await self._post(API_CONTROL, data)
        _LOGGER.debug("Carrier control key=%s val=%s -> %s", key, val, result)
        return result

    async def async_test_connection(self) -> dict[str, Any]:
        """Validate credentials by reading dt."""
        data = await self.get_dt()
        if not data.get("dt"):
            raise ConnectionError("Empty dt response")
        return data
