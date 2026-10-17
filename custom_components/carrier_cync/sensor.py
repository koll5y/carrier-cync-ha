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
    KEY_ROOM_TEMP_READ,
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
            CarrierRoomTempSensor(coordinator, entry),
            CarrierDtSensor(
                coordinator, entry, "room_humidity", "실내습도",
                KEY_ROOM_HUMIDITY, PERCENTAGE, SensorDeviceClass.HUMIDITY,
            ),
            CarrierWeatherSensor(
                coordinator, entry, "outdoor_temp", "실외온도",
                "temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE,
            ),
            CarrierWeatherSensor(
                coordinator, entry, "outdoor_humidity", "실외습도",
                "humidity", PERCENTAGE, SensorDeviceClass.HUMIDITY,
            ),
            CarrierDtSensor(
                coordinator, entry, "odu_temp", "실외기온도",
                KEY_OUTDOOR_TEMP_UNIT, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE,
            ),
            CarrierDtSensor(
                coordinator, entry, "odu_humidity", "실외기습도",
                KEY_OUTDOOR_HUMI_UNIT, PERCENTAGE, SensorDeviceClass.HUMIDITY,
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


class CarrierRoomTempSensor(CoordinatorEntity, SensorEntity):
    """Indoor temp from 3A/10."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        device_id = entry.data[CONF_DEVICE_ID]
        self._attr_name = "실내온도"
        self._attr_unique_id = f"{device_id}_room_temp"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self):
        dt = (self.coordinator.data or {}).get("dt") or {}
        raw = dt.get(KEY_ROOM_TEMP_READ, dt.get("3A"))
        if raw is None:
            return None
        try:
            return round(float(raw) / 10.0, 1)
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self):
        return {"carrier_dt_key": "3A", "scale": "value/10"}


class CarrierDtSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, key, name, dt_key, unit, device_class) -> None:
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
    def __init__(self, coordinator, entry, key, name, weather_field, unit, device_class) -> None:
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
    def available(self) -> bool:
        weather = (self.coordinator.data or {}).get("weather") or {}
        return self._field in weather and weather.get(self._field) is not None

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
            "source": "weather.php",
        }
