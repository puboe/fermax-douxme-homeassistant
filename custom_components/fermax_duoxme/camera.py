"""Camera platform for Fermax DuoxMe."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FermaxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Minimum time between image refreshes
SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fermax camera entities.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: FermaxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    entities: list[FermaxCamera] = []

    # Create camera entity for each device with PhotoCaller enabled
    if coordinator.data:
        for device_id, device_data in coordinator.data.devices.items():
            # Only create camera if PhotoCaller is enabled
            if device_data.has_photocaller:
                entities.append(
                    FermaxCamera(
                        coordinator=coordinator,
                        device_id=device_id,
                        device_tag=device_data.pairing.tag,
                    )
                )
            else:
                _LOGGER.debug(
                    "Skipping camera for device %s - PhotoCaller not enabled",
                    device_id,
                )

    async_add_entities(entities)


class FermaxCamera(CoordinatorEntity[FermaxDataUpdateCoordinator], Camera):
    """Representation of a Fermax PhotoCaller camera.

    Note: PhotoCaller images are captured when someone rings the doorbell.
    Currently, fetching photos requires FCM token registration which will
    be implemented in a future update. For now, the camera entity is created
    but will not show images until FCM support is added.
    """

    _attr_has_entity_name = True
    _attr_name = "Camera"

    def __init__(
        self,
        coordinator: FermaxDataUpdateCoordinator,
        device_id: str,
        device_tag: str,
    ) -> None:
        """Initialize the camera.

        Args:
            coordinator: Data update coordinator
            device_id: Device ID
            device_tag: Device tag name (user's name for the device in Fermax app)
        """
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)

        self._device_id = device_id
        self._device_tag = device_tag
        self._last_image: bytes | None = None
        self._last_photo_id: str | None = None

        self._attr_unique_id = f"{device_id}_camera"

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
    def brand(self) -> str:
        """Return the camera brand."""
        return "Fermax"

    @property
    def model(self) -> str:
        """Return the camera model."""
        return "PhotoCaller"

    @property
    def is_streaming(self) -> bool:
        """Return false - we only show still images."""
        return False

    @property
    def is_recording(self) -> bool:
        """Return false - we don't record."""
        return False

    @property
    def motion_detection_enabled(self) -> bool:
        """Return false - no motion detection."""
        return False

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the latest camera image.

        Note: Currently returns None as FCM token registration is required
        to fetch call history and photo IDs. This will be implemented in
        a future update.

        Args:
            width: Requested width (not used)
            height: Requested height (not used)

        Returns:
            Image bytes or None if no image available
        """
        # TODO: Implement photo fetching when FCM support is added
        # For now, return the last cached image if any
        return self._last_image

    async def async_set_photo(self, photo_id: str) -> None:
        """Set the camera image from a photo ID.

        This method can be called externally (e.g., from an automation
        or service) to set the camera image.

        Args:
            photo_id: Photo ID from call registry
        """
        if photo_id and photo_id != self._last_photo_id:
            _LOGGER.debug(
                "Fetching photo %s for device %s",
                photo_id,
                self._device_id,
            )
            image = await self.coordinator.client.get_photo(photo_id)
            if image:
                self._last_image = image
                self._last_photo_id = photo_id
                self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        attrs: dict[str, Any] = {
            "photocaller_enabled": True,
            "note": "Photo fetching requires FCM support (coming soon)",
        }

        if self._last_photo_id:
            attrs["last_photo_id"] = self._last_photo_id

        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get_device(self._device_id) is not None
        )
