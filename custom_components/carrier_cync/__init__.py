"""Carrier Cync integration."""

from __future__ import annotations

import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CarrierCyncApi
from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_MODEL,
    CONF_MEMBER_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Carrier Cync from a config entry."""
    session = async_get_clientsession(hass)
    api = CarrierCyncApi(
        session,
        member_id=entry.data[CONF_MEMBER_ID],
        device_id=entry.data[CONF_DEVICE_ID],
        device_model=entry.data.get(CONF_DEVICE_MODEL, "SA"),
    )

    scan = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    entry_data: dict = {"api": api, "pending": None}

    async def async_update() -> dict:
        try:
            data = await api.get_status()
        except Exception as err:
            raise UpdateFailed(f"Carrier Cync update failed: {err}") from err

        # 명령 직후 서버 반영 전 stale dt 가 UI를 되돌리지 않도록 보류
        pending = entry_data.get("pending")
        if pending and time.monotonic() < pending["until"]:
            dt = dict(data.get("dt") or {})
            expect = pending.get("expect") or {}
            matched = True
            for key, val in expect.items():
                try:
                    if int(dt.get(key, -999)) != int(val):
                        matched = False
                        break
                except (TypeError, ValueError):
                    matched = False
                    break
            if matched:
                entry_data["pending"] = None
                _LOGGER.debug("Pending control confirmed: %s", expect)
            else:
                dt.update({str(k): v for k, v in expect.items()})
                data = dict(data)
                data["dt"] = dt
        elif pending:
            entry_data["pending"] = None

        return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"carrier_cync_{entry.data[CONF_DEVICE_ID]}",
        update_method=async_update,
        update_interval=timedelta(seconds=int(scan)),
    )

    entry_data["coordinator"] = coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry_data

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
