"""Lock platform for Fermax DuoxMe."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import AccessDoor, DoorId
from .const import DOMAIN
from .coordinator import FermaxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fermax lock entities.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: FermaxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    entities: list[FermaxLock] = []

    # Create lock entity for each visible door on each device
    if coordinator.data:
        for device_id, device_data in coordinator.data.devices.items():
            pairing = device_data.pairing

            for door in pairing.all_visible_doors:
                entities.append(
                    FermaxLock(
                        coordinator=coordinator,
                        device_id=device_id,
                        door=door,
                        device_tag=pairing.tag,
                    )
                )

    async_add_entities(entities)


class FermaxLock(CoordinatorEntity[FermaxDataUpdateCoordinator], LockEntity):
    """Representation of a Fermax door lock."""

    _attr_has_entity_name = True
    _attr_supported_features = LockEntityFeature(0)

    def __init__(
        self,
        coordinator: FermaxDataUpdateCoordinator,
        device_id: str,
        door: AccessDoor,
        device_tag: str,
    ) -> None:
        """Initialize the lock.

        Args:
            coordinator: Data update coordinator
            device_id: Device ID
            door: Door information
            device_tag: Device tag name
        """
        super().__init__(coordinator)

        self._device_id = device_id
        self._door = door
        self._device_tag = device_tag
        self._is_unlocking = False

        # Generate a unique door name
        door_name = door.title if door.title else door.door_type
        if not door_name or door_name == door.door_type:
            door_name = f"Door {door.door_type}"

        self._attr_name = door_name
        self._attr_unique_id = (
            f"{device_id}_{door.door_type}_{door.door_id.block}_{door.door_id.number}"
        )

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
    def is_locked(self) -> bool:
        """Return true if the lock is locked.

        Note: Fermax doors don't report lock state, so we always show locked
        except briefly after unlocking.
        """
        return not self._is_unlocking

    @property
    def is_locking(self) -> bool:
        """Return true if lock is locking."""
        return False

    @property
    def is_unlocking(self) -> bool:
        """Return true if lock is unlocking."""
        return self._is_unlocking

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the door.

        Note: Fermax doors auto-lock, so this is a no-op.
        """
        _LOGGER.debug("Lock called on %s - doors auto-lock", self._attr_unique_id)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the door.

        This opens the door briefly (door auto-locks after a few seconds).
        """
        self._is_unlocking = True
        self.async_write_ha_state()

        try:
            success = await self.coordinator.client.open_door(
                self._device_id, self._door.door_id
            )

            if success:
                _LOGGER.info(
                    "Successfully opened door %s on device %s",
                    self._door.door_type,
                    self._device_id,
                )
            else:
                _LOGGER.error(
                    "Failed to open door %s on device %s",
                    self._door.door_type,
                    self._device_id,
                )

        finally:
            # Door auto-locks, so reset state after a short delay
            self._is_unlocking = False
            self.async_write_ha_state()
