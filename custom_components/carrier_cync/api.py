"""Carrier Cync cloud API client."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_CONTROL, API_STATISTIC

_LOGGER = logging.getLogger(__name__)


class CarrierCyncApi:
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
                200, "200", 0, "0",
            ):
                _LOGGER.warning("Carrier API unexpected response: %s", result)
            return result

    async def get_dt(self) -> dict[str, Any]:
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

    async def get_energy(self, term: str) -> dict[str, Any]:
        data = self._base_payload("energy")
        data["term"] = term
        result = await self._post(API_STATISTIC, data)
        return result.get("response") or {}

    async def get_status(self) -> dict[str, Any]:
        data = await self.get_dt()
        energy: dict[str, Any] = {}
        try:
            emin = await self.get_energy("min")
            energy["now_kw"] = float(emin.get("now") or 0)
        except Exception as err:
            _LOGGER.warning("Energy min failed: %s", err)
            energy["now_kw"] = None
        try:
            eday = await self.get_energy("day")
            items = eday.get("items") or []
            energy["month_kwh"] = round(
                sum(float(i.get("value") or 0) for i in items), 3
            )
        except Exception as err:
            _LOGGER.warning("Energy day failed: %s", err)
            energy["month_kwh"] = None
        try:
            emon = await self.get_energy("month")
            items = emon.get("items") or []
            # 마지막 항목 = 직전 완료 월(이번 달이 목록에 없을 때)
            energy["last_month_kwh"] = (
                round(float(items[-1].get("value") or 0), 3) if items else None
            )
            energy["month_items"] = [
                {"label": i.get("label"), "value": i.get("value")} for i in items[-6:]
            ]
        except Exception as err:
            _LOGGER.warning("Energy month failed: %s", err)
            energy["last_month_kwh"] = None
        data["energy"] = energy
        return data

    async def set_value(self, key: str, val: str | int) -> dict[str, Any]:
        data = self._base_payload("control")
        data["key"] = str(key)
        data["val"] = str(val)
        result = await self._post(API_CONTROL, data)
        _LOGGER.debug("Carrier control key=%s val=%s -> %s", key, val, result)
        return result

    async def async_test_connection(self) -> dict[str, Any]:
        data = await self.get_dt()
        if not data.get("dt"):
            raise ConnectionError("Empty dt response")
        return data
