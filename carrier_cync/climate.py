"""Climate platform for Carrier Cync."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_MODEL,
    CONF_NAME,
    DOMAIN,
    KEY_FAN,
    KEY_MODE,
    KEY_POWER,
    KEY_ROOM_HUMIDITY,
    KEY_ROOM_TEMP,
    KEY_SET_TEMP_STATE,
    KEY_SET_TEMP_WRITE,
    MODE_COOL,
    MODE_DRY,
    MODE_FAN,
    MODE_HEAT,
    MODE_PMV_COOL,
    MODE_PMV_HEAT,
)

_LOGGER = logging.getLogger(__name__)

PRESET_NONE = "none"
PRESET_PMV = "pmv"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate entity."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CarrierCyncClimate(data["coordinator"], data["api"], entry)])


class CarrierCyncClimate(CoordinatorEntity, ClimateEntity):
    """Carrier Cync climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]
    _attr_preset_modes = [PRESET_NONE, PRESET_PMV]
    _attr_min_temp = 17
    _attr_max_temp = 30
    _attr_target_temperature_step = 1

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        device_id = entry.data[CONF_DEVICE_ID]
        name = entry.data.get(CONF_NAME) or "Carrier Cync"
        self._attr_name = name
        self._attr_unique_id = f"{device_id}_climate"
        model = entry.data.get(CONF_DEVICE_MODEL, "SA")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=name,
            manufacturer="Carrier",
            model=model,
        )

    def _dt(self) -> dict:
        data = self.coordinator.data or {}
        return data.get("dt") or {}

    def _int(self, key: str, default: int = 0) -> int:
        try:
            return int(self._dt().get(key, default))
        except (TypeError, ValueError):
            return default

    @property
    def current_temperature(self) -> float | None:
        return float(self._int(KEY_ROOM_TEMP, 0)) or None

    @property
    def current_humidity(self) -> int | None:
        val = self._int(KEY_ROOM_HUMIDITY, 0)
        return val if val else None

    @property
    def target_temperature(self) -> float | None:
        return float(self._int(KEY_SET_TEMP_STATE, 25))

    @property
    def hvac_mode(self) -> HVACMode:
        if self._int(KEY_POWER) == 0:
            return HVACMode.OFF
        mode = self._int(KEY_MODE)
        if mode in (MODE_COOL, MODE_PMV_COOL):
            return HVACMode.COOL
        if mode in (MODE_HEAT, MODE_PMV_HEAT):
            return HVACMode.HEAT
        if mode == MODE_DRY:
            return HVACMode.DRY
        if mode == MODE_FAN:
            return HVACMode.FAN_ONLY
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        mapping = {
            HVACMode.COOL: HVACAction.COOLING,
            HVACMode.HEAT: HVACAction.HEATING,
            HVACMode.DRY: HVACAction.DRYING,
            HVACMode.FAN_ONLY: HVACAction.FAN,
        }
        return mapping.get(self.hvac_mode, HVACAction.IDLE)

    @property
    def preset_mode(self) -> str | None:
        mode = self._int(KEY_MODE)
        if mode in (MODE_PMV_COOL, MODE_PMV_HEAT):
            return PRESET_PMV
        return PRESET_NONE

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._api.set_value(KEY_POWER, 0)
        else:
            mode_map = {
                HVACMode.COOL: MODE_COOL,
                HVACMode.HEAT: MODE_HEAT,
                HVACMode.DRY: MODE_DRY,
                HVACMode.FAN_ONLY: MODE_FAN,
            }
            target = mode_map.get(hvac_mode, MODE_COOL)
            await self._api.set_value(KEY_POWER, 1)
            await self._api.set_value(KEY_MODE, target)
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        await self._api.set_value(KEY_SET_TEMP_WRITE, int(float(temp) * 2))
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        current = self._int(KEY_MODE)
        is_heat = current in (MODE_HEAT, MODE_PMV_HEAT)
        if preset_mode == PRESET_PMV:
            await self._api.set_value(KEY_POWER, 1)
            await self._api.set_value(
                KEY_MODE, MODE_PMV_HEAT if is_heat else MODE_PMV_COOL
            )
        else:
            await self._api.set_value(
                KEY_MODE, MODE_HEAT if is_heat else MODE_COOL
            )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        await self._api.set_value(KEY_POWER, 1)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self._api.set_value(KEY_POWER, 0)
        await self.coordinator.async_request_refresh()
