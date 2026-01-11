"""Binary sensor platform for Fermax DuoxMe."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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
    """Set up Fermax binary sensor entities.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: FermaxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    entities: list[FermaxBinarySensor] = []

    # Create connectivity binary sensor for each device
    if coordinator.data:
        for device_id, device_data in coordinator.data.devices.items():
            entities.append(
                FermaxConnectivitySensor(
                    coordinator=coordinator,
                    device_id=device_id,
                    device_tag=device_data.pairing.tag,
                )
            )

    async_add_entities(entities)


class FermaxBinarySensor(
    CoordinatorEntity[FermaxDataUpdateCoordinator], BinarySensorEntity
):
    """Base class for Fermax binary sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FermaxDataUpdateCoordinator,
        device_id: str,
        device_tag: str,
    ) -> None:
        """Initialize the binary sensor.

        Args:
            coordinator: Data update coordinator
            device_id: Device ID
            device_tag: Device tag name
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


class FermaxConnectivitySensor(FermaxBinarySensor):
    """Binary sensor for device connectivity status."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_name = "Status"

    def __init__(
        self,
        coordinator: FermaxDataUpdateCoordinator,
        device_id: str,
        device_tag: str,
    ) -> None:
        """Initialize the connectivity sensor.

        Args:
            coordinator: Data update coordinator
            device_id: Device ID
            device_tag: Device tag name
        """
        super().__init__(coordinator, device_id, device_tag)
        self._attr_unique_id = f"{device_id}_status"

    @property
    def is_on(self) -> bool:
        """Return true if the device is connected."""
        if self.coordinator.data:
            device_data = self.coordinator.data.get_device(self._device_id)
            if device_data:
                return device_data.is_connected
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get_device(self._device_id) is not None
        )
