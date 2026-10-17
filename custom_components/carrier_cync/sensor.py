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
    KEY_OUTDOOR_TEMP,
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
            CarrierSensor(
                coordinator,
                entry,
                "room_temp",
                "실내온도",
                KEY_ROOM_TEMP,
                UnitOfTemperature.CELSIUS,
                SensorDeviceClass.TEMPERATURE,
            ),
            CarrierSensor(
                coordinator,
                entry,
                "room_humidity",
                "실내습도",
                KEY_ROOM_HUMIDITY,
                PERCENTAGE,
                SensorDeviceClass.HUMIDITY,
            ),
            CarrierSensor(
                coordinator,
                entry,
                "outdoor_temp",
                "실외온도",
                KEY_OUTDOOR_TEMP,
                UnitOfTemperature.CELSIUS,
                SensorDeviceClass.TEMPERATURE,
            ),
        ]
    )


class CarrierSensor(CoordinatorEntity, SensorEntity):
    """Simple dt field sensor."""

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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=entry.data.get(CONF_NAME) or "Carrier Cync",
            manufacturer="Carrier",
            model=entry.data.get(CONF_DEVICE_MODEL, "SA"),
        )

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
