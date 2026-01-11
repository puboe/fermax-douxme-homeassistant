"""Data update coordinator for Fermax DuoxMe."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FermaxApiClient, DeviceInfo, Pairing
from .api.auth import FermaxAuthError
from .const import (
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class DeviceData:
    """Data for a single device."""

    pairing: Pairing
    device_info: DeviceInfo | None = None
    services: list[str] = field(default_factory=list)

    @property
    def is_connected(self) -> bool:
        """Check if device is connected."""
        if self.device_info:
            return self.device_info.is_connected
        return False

    @property
    def wireless_signal(self) -> int:
        """Get wireless signal strength."""
        if self.device_info:
            return self.device_info.wireless_signal
        return 0

    @property
    def has_photocaller(self) -> bool:
        """Check if device has PhotoCaller enabled."""
        if self.device_info:
            return self.device_info.photocaller
        return False


@dataclass
class FermaxData:
    """Data from Fermax API."""

    devices: dict[str, DeviceData] = field(default_factory=dict)

    def get_device(self, device_id: str) -> DeviceData | None:
        """Get device data by ID."""
        return self.devices.get(device_id)


class FermaxDataUpdateCoordinator(DataUpdateCoordinator[FermaxData]):
    """Coordinator to manage data updates from Fermax API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: FermaxApiClient,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            client: Fermax API client
            entry: Config entry
        """
        self._client = client
        self._entry = entry

        # Get polling interval from options or use default
        polling_interval = entry.options.get(
            CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=polling_interval),
        )

    @property
    def client(self) -> FermaxApiClient:
        """Get the API client."""
        return self._client

    async def _async_update_data(self) -> FermaxData:
        """Fetch data from API.

        Returns:
            FermaxData with current device states

        Raises:
            UpdateFailed: If update fails
        """
        try:
            data = FermaxData()

            # Get all pairings
            pairings = await self._client.get_pairings()

            if not pairings:
                _LOGGER.warning("No pairings found for user")
                return data

            # For each pairing, get device info
            for pairing in pairings:
                if not pairing.enabled:
                    continue

                device_id = pairing.device_id
                device_data = DeviceData(pairing=pairing)

                # Get device info
                device_info = await self._client.get_device(device_id)
                device_data.device_info = device_info

                # Get services
                services = await self._client.get_services(device_id)
                device_data.services = services

                data.devices[device_id] = device_data

                _LOGGER.debug(
                    "Updated device %s (%s): connected=%s, signal=%s",
                    pairing.tag,
                    device_id,
                    device_data.is_connected,
                    device_data.wireless_signal,
                )

            return data

        except FermaxAuthError as err:
            raise UpdateFailed(f"Authentication error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
