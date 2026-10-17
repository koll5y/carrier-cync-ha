"""Carrier Cync cloud API client."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_CONTROL

_LOGGER = logging.getLogger(__name__)


class CarrierCyncApi:
    """Minimal client for control.php dt/control."""

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

    async def _post(self, data: dict[str, str]) -> dict[str, Any]:
        async with self._session.post(
            API_CONTROL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            resp.raise_for_status()
            result = await resp.json(content_type=None)
            if str(result.get("code")) not in ("200", "0") and result.get("message") not in (
                "success",
                None,
            ):
                # some responses use code 200 + message success
                if result.get("message") != "success" and result.get("code") != 200:
                    _LOGGER.warning("Carrier API unexpected response: %s", result)
            return result

    async def get_dt(self) -> dict[str, Any]:
        """Fetch device status (dt map)."""
        result = await self._post(self._base_payload("dt"))
        response = result.get("response") or {}
        dt = response.get("dt") or {}
        return {
            "lastdate": response.get("lastdate"),
            "model": response.get("model"),
            "revision": response.get("revision"),
            "deviceid": response.get("deviceid"),
            "dt": {str(k): v for k, v in dt.items()},
        }

    async def set_value(self, key: str, val: str | int) -> dict[str, Any]:
        """Write a single control key."""
        data = self._base_payload("control")
        data["key"] = str(key)
        data["val"] = str(val)
        return await self._post(data)

    async def async_test_connection(self) -> dict[str, Any]:
        """Validate credentials by reading dt."""
        data = await self.get_dt()
        if not data.get("dt"):
            raise ConnectionError("Empty dt response")
        return data
