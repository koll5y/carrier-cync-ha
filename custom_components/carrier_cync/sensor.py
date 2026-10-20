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
            CarrierPowerStatusSensor(coordinator, entry),
            CarrierEnergySensor(
                coordinator, entry, "energy_now", "현재전력",
                "now_kw", UnitOfPower.KILO_WATT, SensorDeviceClass.POWER,
            ),
            CarrierEnergySensor(
                coordinator, entry, "energy_month", "이번달에너지",
                "month_kwh", UnitOfEnergy.KILO_WATT_HOUR, None,
            ),
            CarrierEnergySensor(
                coordinator, entry, "energy_last_month", "저번달에너지",
                "last_month_kwh", UnitOfEnergy.KILO_WATT_HOUR, None,
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
            v = float(raw)
        except (TypeError, ValueError):
            return None
        # 3A is stored as 0.1 C (e.g. 220 -> 22.0)
        if v >= 100:
            return round(v / 10.0, 1)
        return v


class CarrierDtSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, key, name, dt_key, unit, device_class) -> None:
        super().__init__(coordinator)
        device_id = entry.data[CONF_DEVICE_ID]
        self._dt_key = dt_key
        self._attr_name = name
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        if device_class is not None:
            self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self):
        dt = (self.coordinator.data or {}).get("dt") or {}
        raw = dt.get(self._dt_key)
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None


class CarrierPowerStatusSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        device_id = entry.data[CONF_DEVICE_ID]
        self._attr_name = "전원상태"
        self._attr_unique_id = f"{device_id}_power_status"
        self._attr_device_info = _device_info(entry)
        self._attr_icon = "mdi:power"

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
    """Energy / power from statistic.php."""

    def __init__(
        self, coordinator, entry, key, name, energy_field, unit, device_class
    ) -> None:
        super().__init__(coordinator)
        device_id = entry.data[CONF_DEVICE_ID]
        self._field = energy_field
        self._attr_name = name
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        if device_class is not None:
            self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = _device_info(entry)
        self._attr_icon = "mdi:flash"
        self._attr_suggested_display_precision = 3

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

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

    @property
    def extra_state_attributes(self):
        energy = (self.coordinator.data or {}).get("energy") or {}
        return {
            "raw": energy.get(self._field),
            "error": energy.get("error"),
        }
