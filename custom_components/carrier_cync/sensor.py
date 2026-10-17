"""Sensors for Carrier Cync."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
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
    KEY_POWER,
    KEY_ROOM_HUMIDITY,
    KEY_ROOM_TEMP_READ,
    POWER_AUTO_DRY,
    POWER_ON,
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
            CarrierDtSensor(
                coordinator, entry, "odu_temp", "실외기온도",
                KEY_OUTDOOR_TEMP_UNIT, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE,
            ),
            CarrierDtSensor(
                coordinator, entry, "odu_humidity", "실외기습도",
                KEY_OUTDOOR_HUMI_UNIT, PERCENTAGE, SensorDeviceClass.HUMIDITY,
            ),
            CarrierPowerStatusSensor(coordinator, entry),
            CarrierEnergySensor(
                coordinator, entry, "energy_now", "현재전력",
                "now_kw", UnitOfPower.KILO_WATT, SensorDeviceClass.POWER,
                SensorStateClass.MEASUREMENT,
            ),
            CarrierEnergySensor(
                coordinator, entry, "energy_month", "이번달에너지",
                "month_kwh", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY,
                SensorStateClass.TOTAL,
            ),
            CarrierEnergySensor(
                coordinator, entry, "energy_last_month", "저번달에너지",
                "last_month_kwh", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY,
                SensorStateClass.TOTAL,
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


class CarrierPowerStatusSensor(CoordinatorEntity, SensorEntity):
    """운전 / 꺼짐 / 자동건조중."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        device_id = entry.data[CONF_DEVICE_ID]
        self._attr_name = "전원상태"
        self._attr_unique_id = f"{device_id}_power_status"
        self._attr_icon = "mdi:power"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self):
        dt = (self.coordinator.data or {}).get("dt") or {}
        try:
            power = int(dt.get(KEY_POWER, 0))
        except (TypeError, ValueError):
            power = 0
        if power == POWER_ON:
            return "운전"
        if power == POWER_AUTO_DRY:
            return "자동건조중"
        return "꺼짐"

    @property
    def extra_state_attributes(self):
        dt = (self.coordinator.data or {}).get("dt") or {}
        return {"carrier_2a": dt.get(KEY_POWER)}


class CarrierEnergySensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self, coordinator, entry, key, name, energy_field, unit, device_class, state_class
    ) -> None:
        super().__init__(coordinator)
        device_id = entry.data[CONF_DEVICE_ID]
        self._field = energy_field
        self._attr_name = name
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = _device_info(entry)
        if device_class == SensorDeviceClass.POWER:
            self._attr_icon = "mdi:flash"
        else:
            self._attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self):
        energy = (self.coordinator.data or {}).get("energy") or {}
        val = energy.get(self._field)
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None
