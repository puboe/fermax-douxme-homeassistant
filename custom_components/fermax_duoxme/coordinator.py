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
    MAX_CONSECUTIVE_FAILURES,
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
        self._consecutive_failures = 0
        self._last_data: FermaxData | None = None

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

        Implements failure tolerance - only raises UpdateFailed after
        MAX_CONSECUTIVE_FAILURES consecutive failures. Returns the last
        successful data during transient failures.

        Returns:
            FermaxData with current device states

        Raises:
            UpdateFailed: If update fails after MAX_CONSECUTIVE_FAILURES attempts
        """
        try:
            data = FermaxData()

            # Get all pairings
            pairings = await self._client.get_pairings()

            if not pairings:
                _LOGGER.warning("No pairings found for user")
                # Reset failure counter on successful communication
                self._consecutive_failures = 0
                self._last_data = data
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

            # Success - reset failure counter and store data
            self._consecutive_failures = 0
            self._last_data = data
            return data

        except FermaxAuthError as err:
            # Auth errors should fail immediately - no tolerance
            self._consecutive_failures = MAX_CONSECUTIVE_FAILURES
            raise UpdateFailed(f"Authentication error: {err}") from err

        except Exception as err:
            self._consecutive_failures += 1
            
            if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                _LOGGER.error(
                    "API update failed after %d consecutive attempts: %s",
                    self._consecutive_failures,
                    err,
                )
                raise UpdateFailed(f"Error communicating with API: {err}") from err
            
            _LOGGER.warning(
                "API update failed (attempt %d/%d): %s. Returning last known data.",
                self._consecutive_failures,
                MAX_CONSECUTIVE_FAILURES,
                err,
            )
            
            # Return last successful data to keep entities available
            if self._last_data is not None:
                return self._last_data
            
            # No previous data - must raise to indicate failure
            raise UpdateFailed(f"Error communicating with API: {err}") from err
