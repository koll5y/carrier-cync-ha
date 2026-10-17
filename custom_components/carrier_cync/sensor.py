"""Sensors for Carrier Cync — indoor/outdoor unit (dt) only."""

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
                KEY_ROOM_TEMP,  # 3E 실내기
                UnitOfTemperature.CELSIUS,
                SensorDeviceClass.TEMPERATURE,
            ),
            CarrierDtSensor(
                coordinator,
                entry,
                "room_humidity",
                "실내습도",
                KEY_ROOM_HUMIDITY,  # 3J 실내기
                PERCENTAGE,
                SensorDeviceClass.HUMIDITY,
            ),
            CarrierDtSensor(
                coordinator,
                entry,
                "outdoor_temp",
                "실외온도",
                KEY_OUTDOOR_TEMP_UNIT,  # 1L 실외기
                UnitOfTemperature.CELSIUS,
                SensorDeviceClass.TEMPERATURE,
            ),
            CarrierDtSensor(
                coordinator,
                entry,
                "outdoor_humidity",
                "실외습도",
                KEY_OUTDOOR_HUMI_UNIT,  # 1A 실외기(실측 후보)
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
    """Sensor from indoor/outdoor unit dt fields."""

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

    @property
    def extra_state_attributes(self):
        return {"carrier_dt_key": self._dt_key}
