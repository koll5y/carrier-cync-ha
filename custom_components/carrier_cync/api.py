"""Carrier Cync cloud API client."""

from __future__ import annotations

import json
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
            timeout=aiohttp.ClientTimeout(total=12),
        ) as resp:
            resp.raise_for_status()
            result = await resp.json(content_type=None)
            if isinstance(result, str):
                result = json.loads(result)
            if result.get("message") not in ("success", None) and result.get("code") not in (
                200,
                "200",
                0,
                "0",
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

    def _response_dict(self, result: dict[str, Any]) -> dict[str, Any]:
        resp = result.get("response")
        if isinstance(resp, str):
            try:
                resp = json.loads(resp)
            except json.JSONDecodeError:
                resp = None
        return resp if isinstance(resp, dict) else {}

    @staticmethod
    def _num(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def get_energy(self, term: str) -> dict[str, Any]:
        data = self._base_payload("energy")
        data["term"] = term
        result = await self._post(API_STATISTIC, data)
        resp = self._response_dict(result)
        if not resp:
            _LOGGER.warning(
                "Energy term=%s empty response code=%s message=%s",
                term,
                result.get("code"),
                result.get("message"),
            )
        return resp

    async def get_status(self) -> dict[str, Any]:
        data = await self.get_dt()
        energy: dict[str, Any] = {
            "now_kw": None,
            "month_kwh": None,
            "last_month_kwh": None,
            "error": None,
        }
        try:
            # 병렬 호출 시 서버가 빈 응답을 주는 경우가 있어 순서대로 조회
            emin = await self.get_energy("min")
            eday = await self.get_energy("day")
            emon = await self.get_energy("month")
            energy["now_kw"] = self._num(emin.get("now"))
            day_items = eday.get("items") or []
            mon_items = emon.get("items") or []
            if day_items and isinstance(day_items[-1], dict):
                energy["month_kwh"] = self._num(day_items[-1].get("value"))
            if mon_items and isinstance(mon_items[-1], dict):
                energy["last_month_kwh"] = self._num(mon_items[-1].get("value"))
            if energy["now_kw"] is None and energy["month_kwh"] is None:
                energy["error"] = "statistic.php returned no now/items"
                _LOGGER.warning("Carrier energy empty: min=%s day_items=%s", emin.get("now"), len(day_items))
            else:
                _LOGGER.info(
                    "Carrier energy now=%s month=%s last=%s",
                    energy["now_kw"],
                    energy["month_kwh"],
                    energy["last_month_kwh"],
                )
        except Exception as err:
            energy["error"] = str(err)
            _LOGGER.warning("Energy fetch failed: %s", err)

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
