"""Sensor platform for Fermax DuoxMe."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FermaxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fermax sensor entities.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: FermaxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    entities: list[FermaxSensor] = []

    # Create sensors for each device
    if coordinator.data:
        for device_id, device_data in coordinator.data.devices.items():
            tag = device_data.pairing.tag

            # Wireless signal sensor
            entities.append(
                FermaxWirelessSignalSensor(
                    coordinator=coordinator,
                    device_id=device_id,
                    device_tag=tag,
                )
            )

    async_add_entities(entities)


class FermaxSensor(CoordinatorEntity[FermaxDataUpdateCoordinator], SensorEntity):
    """Base class for Fermax sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FermaxDataUpdateCoordinator,
        device_id: str,
        device_tag: str,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: Data update coordinator
            device_id: Device ID
            device_tag: Device tag name (user-defined name from Fermax app)
        """
        super().__init__(coordinator)

        self._device_id = device_id
        self._device_tag = device_tag

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_tag,
            manufacturer="Fermax",
            model="DuoxMe",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get_device(self._device_id) is not None
        )


class FermaxWirelessSignalSensor(FermaxSensor):
    """Sensor for wireless signal strength."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_name = "Signal Strength"
    _attr_icon = "mdi:wifi"

    def __init__(
        self,
        coordinator: FermaxDataUpdateCoordinator,
        device_id: str,
        device_tag: str,
    ) -> None:
        """Initialize the signal sensor."""
        super().__init__(coordinator, device_id, device_tag)
        self._attr_unique_id = f"{device_id}_signal"

    @property
    def native_value(self) -> int | None:
        """Return the signal strength.

        The API returns 0-5, we convert to percentage (0-100).
        """
        if self.coordinator.data:
            device_data = self.coordinator.data.get_device(self._device_id)
            if device_data and device_data.device_info:
                # Convert 0-5 scale to percentage
                signal = device_data.wireless_signal
                return min(100, signal * 20)
        return None
