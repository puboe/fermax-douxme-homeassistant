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
