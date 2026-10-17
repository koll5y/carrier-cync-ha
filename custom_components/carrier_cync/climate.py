"""Climate platform for Carrier Cync."""

from __future__ import annotations

import asyncio
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
    KEY_MODE,
    KEY_POWER,
    KEY_ROOM_HUMIDITY,
    KEY_ROOM_TEMP_READ,
    KEY_ROOM_TEMP_ALT,
    KEY_SET_TEMP_STATE,
    KEY_SET_TEMP_WRITE,
    MODE_COOL,
    MODE_DRY,
    MODE_FAN,
    MODE_HEAT,
    MODE_PMV_COOL,
    MODE_PMV_HEAT,
    POWER_AUTO_DRY,
    POWER_ON,
)

_LOGGER = logging.getLogger(__name__)

PRESET_NONE = "none"
PRESET_PMV = "pmv"

# 클라우드가 control 반영 후 dt에 보이기까지 수 초 걸림
_REFRESH_DELAY = 3.5



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

    def _is_pmv(self) -> bool:
        return self._int(KEY_MODE) in (MODE_PMV_COOL, MODE_PMV_HEAT)

    def _power(self) -> int:
        return self._int(KEY_POWER, 0)

    def _is_running(self) -> bool:
        """Only 2A==1 is normal run. 0=off, 2=auto-dry after off."""
        return self._power() == POWER_ON


    @property
    def current_temperature(self) -> float | None:
        """실내온도: 3A/10 (앱과 일치). 3E는 모드에 따라 희망온도를 따라감."""
        dt = self._dt()
        raw = dt.get(KEY_ROOM_TEMP_READ, dt.get("3A"))
        if raw is None:
            return None
        try:
            return round(float(raw) / 10.0, 1)
        except (TypeError, ValueError):
            return None

    @property
    def current_humidity(self) -> int | None:
        """실내기 현재습도 (3J)."""
        dt = self._dt()
        raw = dt.get("3J", dt.get(KEY_ROOM_HUMIDITY))
        if raw is None:
            return None
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return None

    @property
    def target_temperature(self) -> float | None:
        """희망온도 (3D). PMV 모드에서는 단계값이라 숨김."""
        if self._is_pmv():
            return None
        dt = self._dt()
        raw = dt.get("3D", dt.get(KEY_SET_TEMP_STATE))
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """앱 대조: 3E=실내, 3D=희망 — 카드 큰 숫자는 보통 희망온도."""
        power = self._power()
        status = "on" if power == POWER_ON else (
            "auto_dry" if power == POWER_AUTO_DRY else "off"
        )
        return {
            "carrier_2a_power": power,
            "carrier_power_status": status,
            "carrier_2b_mode": self._int(KEY_MODE),
            "희망온도_3D": self._int(KEY_SET_TEMP_STATE),
            "실내온도_3A_x10": self._int(KEY_ROOM_TEMP_READ),
            "실내온도_3E_참고": self._int(KEY_ROOM_TEMP_ALT),
            "실내습도_3J": self._int(KEY_ROOM_HUMIDITY),
            "carrier_pmv": self._is_pmv(),
        }



    @property
    def hvac_mode(self) -> HVACMode:
        # 자동건조(2A=2) 포함, 정상 운전(1)이 아니면 꺼짐
        if not self._is_running():
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
        if self._power() == POWER_AUTO_DRY:
            return HVACAction.DRYING  # 앱: 자동 건조중
        if not self._is_running():
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


    def _patch_dt(self, **keys: int) -> None:
        """Optimistically update coordinator cache so UI does not snap back."""
        data = dict(self.coordinator.data or {})
        dt = dict(data.get("dt") or {})
        for key, val in keys.items():
            dt[str(key)] = val
        data["dt"] = dt
        self.coordinator.async_set_updated_data(data)

    def _set_pending(self, expect: dict[str, int], hold_seconds: float = 20.0) -> None:
        """Hold expected keys until server dt matches (blocks stale poll overwrite)."""
        import time

        entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id)
        if entry_data is not None:
            entry_data["pending"] = {
                "expect": {str(k): int(v) for k, v in expect.items()},
                "until": time.monotonic() + hold_seconds,
            }

    async def _wait_confirmed(
        self,
        expect: dict[str, int],
        timeout: float = 15.0,
        interval: float = 1.0,
    ) -> bool:
        """Poll dt until expected keys match, then publish confirmed state."""
        import time

        self._set_pending(expect, hold_seconds=timeout + 5)
        self._patch_dt(**expect)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                data = await self._api.get_dt()
            except Exception:
                _LOGGER.exception("Confirm poll failed")
                await asyncio.sleep(interval)
                continue
            dt = data.get("dt") or {}
            ok = True
            for key, val in expect.items():
                try:
                    if int(dt.get(str(key), -999)) != int(val):
                        ok = False
                        break
                except (TypeError, ValueError):
                    ok = False
                    break
            if ok:
                merged = dict(self.coordinator.data or {})
                merged.update(data)
                self.coordinator.async_set_updated_data(merged)
                entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id)
                if entry_data is not None:
                    entry_data["pending"] = None
                _LOGGER.info("Carrier control confirmed: %s", expect)
                return True
            # keep optimistic UI
            self._patch_dt(**expect)
            await asyncio.sleep(interval)

        _LOGGER.warning("Carrier control not confirmed within %ss: %s", timeout, expect)
        await self.coordinator.async_request_refresh()
        return False

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        mode = hvac_mode.value if isinstance(hvac_mode, HVACMode) else str(hvac_mode)
        mode = mode.lower().strip()

        if mode == "off":
            await self._api.set_value(KEY_POWER, 0)
            await self._wait_confirmed({KEY_POWER: 0}, timeout=15)
            return

        mode_map = {
            "cool": MODE_COOL,
            "heat": MODE_HEAT,
            "dry": MODE_DRY,
            "fan_only": MODE_FAN,
            "fan-only": MODE_FAN,
        }
        if mode not in mode_map:
            _LOGGER.warning("Unknown hvac_mode %r, ignored", mode)
            return
        target = mode_map[mode]

        try:
            if not self._is_running():
                await self._api.set_value(KEY_POWER, POWER_ON)
                await asyncio.sleep(0.5)
            await self._api.set_value(KEY_MODE, target)
            if target == MODE_FAN:
                await asyncio.sleep(0.4)
                await self._api.set_value(KEY_MODE, MODE_FAN)
            _LOGGER.info("Carrier mode command %s (2B=%s)", mode, target)
        except Exception:
            _LOGGER.exception("Carrier set_hvac_mode failed")
            raise

        await self._wait_confirmed({KEY_POWER: POWER_ON, KEY_MODE: target}, timeout=15)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        if self._is_pmv():
            _LOGGER.debug("Skip set_temperature while PMV mode")
            return
        write_val = int(float(temp) * 2)
        await self._api.set_value(KEY_SET_TEMP_WRITE, write_val)
        # 희망온도 읽기 키 3D 가 맞을 때까지 대기
        await self._wait_confirmed({KEY_SET_TEMP_STATE: int(float(temp))}, timeout=12)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        current = self._int(KEY_MODE)
        is_heat = current in (MODE_HEAT, MODE_PMV_HEAT)
        if preset_mode == PRESET_PMV:
            target = MODE_PMV_HEAT if is_heat else MODE_PMV_COOL
            if not self._is_running():
                await self._api.set_value(KEY_POWER, POWER_ON)
                await asyncio.sleep(0.5)
            await self._api.set_value(KEY_MODE, target)
            await asyncio.sleep(0.4)
            await self._api.set_value(KEY_SET_TEMP_STATE, 0)
            await self._wait_confirmed(
                {KEY_POWER: POWER_ON, KEY_MODE: target}, timeout=15
            )
        else:
            target = MODE_HEAT if is_heat else MODE_COOL
            await self._api.set_value(KEY_MODE, target)
            await self._wait_confirmed(
                {KEY_POWER: POWER_ON, KEY_MODE: target}, timeout=15
            )

    async def async_turn_on(self) -> None:
        await self._api.set_value(KEY_POWER, POWER_ON)
        await self._wait_confirmed({KEY_POWER: POWER_ON}, timeout=12)

    async def async_turn_off(self) -> None:
        await self._api.set_value(KEY_POWER, 0)
        # 자동건조(2A=2) 도 꺼짐 표시이므로 0 또는 2 허용은 wait에서 0만 확인
        # 자동건조 진입 시 2가 될 수 있어 power!=1 이면 성공으로 처리
        import time

        self._set_pending({KEY_POWER: 0}, hold_seconds=20)
        self._patch_dt(**{KEY_POWER: 0})
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                data = await self._api.get_dt()
            except Exception:
                await asyncio.sleep(1)
                continue
            dt = data.get("dt") or {}
            try:
                p = int(dt.get(KEY_POWER, 1))
            except (TypeError, ValueError):
                p = 1
            if p != POWER_ON:
                if p != 0:
                    dt = dict(dt)
                    dt[KEY_POWER] = 0  # UI는 off
                    data = dict(data)
                    data["dt"] = dt
                merged = dict(self.coordinator.data or {})
                merged.update(data)
                if p == POWER_AUTO_DRY:
                    merged.setdefault("dt", {})[KEY_POWER] = POWER_AUTO_DRY
                self.coordinator.async_set_updated_data(merged)
                entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id)
                if entry_data is not None:
                    entry_data["pending"] = None
                return
            self._patch_dt(**{KEY_POWER: 0})
            await asyncio.sleep(1)
        await self.coordinator.async_request_refresh()
