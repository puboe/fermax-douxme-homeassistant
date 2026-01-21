"""Tests for coordinator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.fermax_duoxme.coordinator import DeviceData, FermaxData
from custom_components.fermax_duoxme.api.models import Pairing, DeviceInfo


class TestDeviceData:
    """Tests for DeviceData class."""

    def test_is_connected_true(self):
        """Test is_connected when device is connected."""
        pairing = Pairing.from_dict({
            "id": "p1",
            "deviceId": "d1",
            "tag": "Test",
        })
        device_info = DeviceInfo.from_dict({
            "connectionState": "Connected",
        })
        device_data = DeviceData(pairing=pairing, device_info=device_info)

        assert device_data.is_connected is True

    def test_is_connected_false(self):
        """Test is_connected when device is disconnected."""
        pairing = Pairing.from_dict({
            "id": "p1",
            "deviceId": "d1",
            "tag": "Test",
        })
        device_info = DeviceInfo.from_dict({
            "connectionState": "Disconnected",
        })
        device_data = DeviceData(pairing=pairing, device_info=device_info)

        assert device_data.is_connected is False

    def test_is_connected_no_device_info(self):
        """Test is_connected when device_info is None."""
        pairing = Pairing.from_dict({
            "id": "p1",
            "deviceId": "d1",
            "tag": "Test",
        })
        device_data = DeviceData(pairing=pairing)

        assert device_data.is_connected is False

    def test_wireless_signal(self):
        """Test wireless_signal property."""
        pairing = Pairing.from_dict({
            "id": "p1",
            "deviceId": "d1",
            "tag": "Test",
        })
        device_info = DeviceInfo.from_dict({
            "wirelessSignal": 4,
        })
        device_data = DeviceData(pairing=pairing, device_info=device_info)

        assert device_data.wireless_signal == 4

    def test_wireless_signal_no_device_info(self):
        """Test wireless_signal when device_info is None."""
        pairing = Pairing.from_dict({
            "id": "p1",
            "deviceId": "d1",
            "tag": "Test",
        })
        device_data = DeviceData(pairing=pairing)

        assert device_data.wireless_signal == 0

    def test_has_photocaller_true(self):
        """Test has_photocaller when enabled."""
        pairing = Pairing.from_dict({
            "id": "p1",
            "deviceId": "d1",
            "tag": "Test",
        })
        device_info = DeviceInfo.from_dict({
            "photocaller": True,
        })
        device_data = DeviceData(pairing=pairing, device_info=device_info)

        assert device_data.has_photocaller is True

    def test_has_photocaller_false(self):
        """Test has_photocaller when disabled."""
        pairing = Pairing.from_dict({
            "id": "p1",
            "deviceId": "d1",
            "tag": "Test",
        })
        device_info = DeviceInfo.from_dict({
            "photocaller": False,
        })
        device_data = DeviceData(pairing=pairing, device_info=device_info)

        assert device_data.has_photocaller is False


class TestFermaxData:
    """Tests for FermaxData class."""

    def test_get_device_found(self):
        """Test get_device when device exists."""
        pairing = Pairing.from_dict({
            "id": "p1",
            "deviceId": "d1",
            "tag": "Test",
        })
        device_data = DeviceData(pairing=pairing)
        fermax_data = FermaxData(devices={"d1": device_data})

        result = fermax_data.get_device("d1")
        assert result is device_data

    def test_get_device_not_found(self):
        """Test get_device when device doesn't exist."""
        fermax_data = FermaxData()

        result = fermax_data.get_device("nonexistent")
        assert result is None

    def test_multiple_devices(self):
        """Test FermaxData with multiple devices."""
        pairing1 = Pairing.from_dict({"id": "p1", "deviceId": "d1", "tag": "Door1"})
        pairing2 = Pairing.from_dict({"id": "p2", "deviceId": "d2", "tag": "Door2"})
        
        device1 = DeviceData(pairing=pairing1)
        device2 = DeviceData(pairing=pairing2)
        
        fermax_data = FermaxData(devices={
            "d1": device1,
            "d2": device2,
        })

        assert len(fermax_data.devices) == 2
        assert fermax_data.get_device("d1").pairing.tag == "Door1"
        assert fermax_data.get_device("d2").pairing.tag == "Door2"


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.options = {}
    return entry


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock()
    client.get_pairings = AsyncMock()
    client.get_device = AsyncMock()
    client.get_services = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_pairing_data():
    """Create a mock pairing."""
    return Pairing.from_dict({
        "id": "p1",
        "deviceId": "d1",
        "tag": "Test",
        "enabled": True,
    })


@pytest.fixture
def mock_device():
    """Create a mock device info."""
    return DeviceInfo.from_dict({
        "connectionState": "Connected",
        "wirelessSignal": 4,
    })


class TestCoordinatorFailureTolerance:
    """Tests for coordinator failure tolerance behavior."""

    async def test_single_failure_returns_cached_data(
        self, mock_hass, mock_entry, mock_client, mock_pairing_data, mock_device
    ):
        """Test that a single failure returns cached data instead of raising."""
        from custom_components.fermax_duoxme.coordinator import FermaxDataUpdateCoordinator

        coordinator = FermaxDataUpdateCoordinator(mock_hass, mock_client, mock_entry)

        # First call succeeds - populate cache
        mock_client.get_pairings.return_value = [mock_pairing_data]
        mock_client.get_device.return_value = mock_device

        data = await coordinator._async_update_data()
        assert data is not None
        assert coordinator._consecutive_failures == 0
        assert coordinator._last_data is not None

        # Second call fails - should return cached data
        mock_client.get_pairings.side_effect = Exception("API timeout")

        data = await coordinator._async_update_data()
        assert data is coordinator._last_data
        assert coordinator._consecutive_failures == 1

    async def test_two_failures_still_returns_cached_data(
        self, mock_hass, mock_entry, mock_client, mock_pairing_data, mock_device
    ):
        """Test that two consecutive failures still return cached data."""
        from custom_components.fermax_duoxme.coordinator import FermaxDataUpdateCoordinator

        coordinator = FermaxDataUpdateCoordinator(mock_hass, mock_client, mock_entry)

        # First call succeeds
        mock_client.get_pairings.return_value = [mock_pairing_data]
        mock_client.get_device.return_value = mock_device
        await coordinator._async_update_data()

        # Next two calls fail
        mock_client.get_pairings.side_effect = Exception("API timeout")

        data = await coordinator._async_update_data()
        assert coordinator._consecutive_failures == 1

        data = await coordinator._async_update_data()
        assert coordinator._consecutive_failures == 2
        assert data is coordinator._last_data

    async def test_three_failures_raises_update_failed(
        self, mock_hass, mock_entry, mock_client, mock_pairing_data, mock_device
    ):
        """Test that three consecutive failures raise UpdateFailed."""
        from custom_components.fermax_duoxme.coordinator import FermaxDataUpdateCoordinator
        from homeassistant.helpers.update_coordinator import UpdateFailed

        coordinator = FermaxDataUpdateCoordinator(mock_hass, mock_client, mock_entry)

        # First call succeeds
        mock_client.get_pairings.return_value = [mock_pairing_data]
        mock_client.get_device.return_value = mock_device
        await coordinator._async_update_data()

        # Next three calls fail
        mock_client.get_pairings.side_effect = Exception("API timeout")

        await coordinator._async_update_data()  # failure 1
        await coordinator._async_update_data()  # failure 2

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()  # failure 3 - raises

        assert coordinator._consecutive_failures == 3

    async def test_success_resets_failure_counter(
        self, mock_hass, mock_entry, mock_client, mock_pairing_data, mock_device
    ):
        """Test that a successful call resets the failure counter."""
        from custom_components.fermax_duoxme.coordinator import FermaxDataUpdateCoordinator

        coordinator = FermaxDataUpdateCoordinator(mock_hass, mock_client, mock_entry)

        # First call succeeds
        mock_client.get_pairings.return_value = [mock_pairing_data]
        mock_client.get_device.return_value = mock_device
        await coordinator._async_update_data()

        # Two failures
        mock_client.get_pairings.side_effect = Exception("API timeout")
        await coordinator._async_update_data()
        await coordinator._async_update_data()
        assert coordinator._consecutive_failures == 2

        # Success resets counter
        mock_client.get_pairings.side_effect = None
        mock_client.get_pairings.return_value = [mock_pairing_data]
        await coordinator._async_update_data()
        assert coordinator._consecutive_failures == 0

    async def test_auth_error_fails_immediately(
        self, mock_hass, mock_entry, mock_client, mock_pairing_data, mock_device
    ):
        """Test that authentication errors fail immediately without tolerance."""
        from custom_components.fermax_duoxme.coordinator import FermaxDataUpdateCoordinator
        from custom_components.fermax_duoxme.api.auth import FermaxAuthError
        from homeassistant.helpers.update_coordinator import UpdateFailed

        coordinator = FermaxDataUpdateCoordinator(mock_hass, mock_client, mock_entry)

        # First call succeeds
        mock_client.get_pairings.return_value = [mock_pairing_data]
        mock_client.get_device.return_value = mock_device
        await coordinator._async_update_data()

        # Auth error should fail immediately
        mock_client.get_pairings.side_effect = FermaxAuthError("Token expired")

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    async def test_no_cached_data_raises_on_first_failure(
        self, mock_hass, mock_entry, mock_client
    ):
        """Test that failure with no cached data raises UpdateFailed."""
        from custom_components.fermax_duoxme.coordinator import FermaxDataUpdateCoordinator
        from homeassistant.helpers.update_coordinator import UpdateFailed

        coordinator = FermaxDataUpdateCoordinator(mock_hass, mock_client, mock_entry)

        # First call fails - no cached data available
        mock_client.get_pairings.side_effect = Exception("API timeout")

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

