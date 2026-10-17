"""Sensors for Carrier Cync."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_MODEL,
    CONF_NAME,
    DOMAIN,
    KEY_OUTDOOR_HUMI_UNIT,
    KEY_OUTDOOR_TEMP_UNIT,
    KEY_ROOM_HUMIDITY,
    KEY_ROOM_TEMP,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    async_add_entities(
        [
            CarrierDtSensor(
                coordinator,
                entry,
                "room_temp",
                "실내온도",
                KEY_ROOM_TEMP,
                UnitOfTemperature.CELSIUS,
                SensorDeviceClass.TEMPERATURE,
            ),
            CarrierDtSensor(
                coordinator,
                entry,
                "room_humidity",
                "실내습도",
                KEY_ROOM_HUMIDITY,
                PERCENTAGE,
                SensorDeviceClass.HUMIDITY,
            ),
            # 앱 실외 표시와 맞추기: weather.php
            CarrierWeatherSensor(
                coordinator,
                entry,
                "outdoor_temp",
                "실외온도",
                "temperature",
                UnitOfTemperature.CELSIUS,
                SensorDeviceClass.TEMPERATURE,
            ),
            CarrierWeatherSensor(
                coordinator,
                entry,
                "outdoor_humidity",
                "실외습도",
                "humidity",
                PERCENTAGE,
                SensorDeviceClass.HUMIDITY,
            ),
            # 참고용 (실외기 dt 값 — 앱 날씨 숫자와 다를 수 있음)
            CarrierDtSensor(
                coordinator,
                entry,
                "outdoor_temp_unit",
                "실외온도(실외기)",
                KEY_OUTDOOR_TEMP_UNIT,
                UnitOfTemperature.CELSIUS,
                SensorDeviceClass.TEMPERATURE,
            ),
            CarrierDtSensor(
                coordinator,
                entry,
                "outdoor_humidity_unit",
                "실외습도(실외기)",
                KEY_OUTDOOR_HUMI_UNIT,
                PERCENTAGE,
                SensorDeviceClass.HUMIDITY,
            ),
        ]
    )


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    device_id = entry.data[CONF_DEVICE_ID]
    return DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        name=entry.data.get(CONF_NAME) or "Carrier Cync",
        manufacturer="Carrier",
        model=entry.data.get(CONF_DEVICE_MODEL, "SA"),
    )


class CarrierDtSensor(CoordinatorEntity, SensorEntity):
    """Sensor from dt map."""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        dt_key: str,
        unit: str,
        device_class: SensorDeviceClass,
    ) -> None:
        super().__init__(coordinator)
        device_id = entry.data[CONF_DEVICE_ID]
        self._dt_key = dt_key
        self._attr_name = name
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self):
        dt = (self.coordinator.data or {}).get("dt") or {}
        val = dt.get(self._dt_key)
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None


class CarrierWeatherSensor(CoordinatorEntity, SensorEntity):
    """Sensor from weather.php (app outdoor display source)."""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        weather_field: str,
        unit: str,
        device_class: SensorDeviceClass,
    ) -> None:
        super().__init__(coordinator)
        device_id = entry.data[CONF_DEVICE_ID]
        self._field = weather_field
        self._attr_name = name
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self):
        weather = (self.coordinator.data or {}).get("weather") or {}
        val = weather.get(self._field)
        if val is None:
            return None
        try:
            return round(float(val), 1)
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self):
        weather = (self.coordinator.data or {}).get("weather") or {}
        return {
            "location": weather.get("location"),
            "cloud": weather.get("cloud"),
        }
