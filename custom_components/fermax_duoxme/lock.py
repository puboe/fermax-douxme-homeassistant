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

from homeassistant.helpers import entity_registry as er
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

    known_entities: dict[str, FermaxLock] = {}

    @callback
    def _async_update_entities() -> None:
        """Update entities based on coordinator data."""
        if not coordinator.data:
            return

        current_doors: dict[str, tuple[str, AccessDoor, str]] = {}

        # Identify all doors (visible or not)
        for device_id, device_data in coordinator.data.devices.items():
            pairing = device_data.pairing
            for door in pairing.all_doors:
                # Generate the same unique ID mechanism as FermaxLock
                unique_id = f"{device_id}_{door.door_type}_{door.door_id.block}_{door.door_id.number}"
                current_doors[unique_id] = (device_id, door, pairing.tag)

        # Add new entities
        new_entities: list[FermaxLock] = []
        for unique_id, (device_id, door, tag) in current_doors.items():
            if unique_id not in known_entities:
                entity = FermaxLock(coordinator, device_id, door, tag)
                known_entities[unique_id] = entity
                new_entities.append(entity)

        if new_entities:
            async_add_entities(new_entities)

        # Remove entities that are no longer in the door list at all (removed from config?)
        # Note: Hidden doors are still in 'all_doors' so they won't be removed here, just marked unavailable
        to_remove: list[str] = []
        for unique_id, entity in known_entities.items():
            if unique_id not in current_doors:
                hass.async_create_task(entity.async_remove())
                to_remove.append(unique_id)
            else:
                # Update visibility
                # If the door becomes visible/invisible, we must update the registry
                # because disabled entities don't receive updates to re-enable themselves.
                _, door, _ = current_doors[unique_id]
                registry = er.async_get(hass)
                if entity.entity_id and (entry := registry.async_get(entity.entity_id)):
                     if not door.visible:
                         # Disable if not already disabled by integration
                         if entry.disabled_by != er.RegistryEntryDisabler.INTEGRATION:
                             registry.async_update_entity(
                                 entity.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION
                             )
                             _LOGGER.debug("Disabling (hiding) lock %s", entity.entity_id)
                     elif entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
                         # Enable if disabled by integration
                         registry.async_update_entity(entity.entity_id, disabled_by=None)
                         _LOGGER.debug("Enabling (showing) lock %s", entity.entity_id)

        for unique_id in to_remove:
            del known_entities[unique_id]

    # Register listener and perform initial update
    entry.async_on_unload(coordinator.async_add_listener(_async_update_entities))
    _async_update_entities()


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
        self._attr_name = self._get_door_name(door)
        self._attr_unique_id = (
            f"{device_id}_{door.door_type}_{door.door_id.block}_{door.door_id.number}"
        )

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return self._door.visible


    @staticmethod
    def _get_door_name(door: AccessDoor) -> str:
        """Get the display name for a door."""
        door_name = door.title if door.title else door.door_type
        if not door_name or door_name == door.door_type:
            door_name = f"Door {door.door_type}"
        return door_name

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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Find our door in the new data
        if not self.coordinator.data:
            return

        device_data = self.coordinator.data.devices.get(self._device_id)
        if not device_data:
            return

        # Find the specific door
        target_door = None
        for door in device_data.pairing.all_doors:
            # Match by semantic ID
            if (
                door.door_type == self._door.door_type
                and door.door_id.block == self._door.door_id.block
                and door.door_id.number == self._door.door_id.number
            ):
                target_door = door
                break

        if target_door:
            # Check for changes
            prev_door = self._door
            self._door = target_door
            
            # Update name if changed
            new_name = self._get_door_name(target_door)
            if new_name != self._attr_name:
                _LOGGER.debug(
                    "Updating door name for %s: '%s' -> '%s' (API title: '%s')",
                    self._attr_unique_id,
                    self._attr_name,
                    new_name,
                    target_door.title,
                )
                self._attr_name = new_name

            # Update availability based on visibility
            # Visibility updates are now handled in the global coordinator listener
            # to ensure disabled entities can be re-enabled.

        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available

    
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
