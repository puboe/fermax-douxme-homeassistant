"""Tests for API models."""

import pytest
from datetime import datetime

from custom_components.fermax_duoxme.api.models import (
    DoorId,
    AccessDoor,
    Pairing,
    DeviceInfo,
    CallRecord,
    User,
    Panel,
)


class TestDoorId:
    """Tests for DoorId class."""

    def test_from_dict(self):
        """Test creating DoorId from dict."""
        data = {"block": 0, "subblock": -1, "number": 0}
        door_id = DoorId.from_dict(data)

        assert door_id.block == 0
        assert door_id.subblock == -1
        assert door_id.number == 0

    def test_from_dict_missing_fields(self):
        """Test creating DoorId with missing fields uses defaults."""
        data = {}
        door_id = DoorId.from_dict(data)

        assert door_id.block == 0
        assert door_id.subblock == -1
        assert door_id.number == 0

    def test_to_dict(self):
        """Test converting DoorId to dict."""
        door_id = DoorId(block=1, subblock=2, number=3)
        result = door_id.to_dict()

        assert result == {"block": 1, "subblock": 2, "number": 3}


class TestAccessDoor:
    """Tests for AccessDoor class."""

    def test_from_access_door_map(self):
        """Test creating AccessDoor from accessDoorMap entry."""
        data = {
            "accessId": {"block": 0, "subblock": -1, "number": 0},
            "title": "F1",
            "visible": True,
        }
        door = AccessDoor.from_access_door_map("ZERO", data)

        assert door.door_type == "ZERO"
        assert door.title == "F1"
        assert door.visible is True
        assert door.door_id.block == 0

    def test_from_panel_access_door(self):
        """Test creating AccessDoor from panelAccessDoors entry."""
        data = {
            "doorId": {"block": 0, "subblock": 0, "number": 0},
            "title": "Panel Door",
            "isVisible": True,
        }
        door = AccessDoor.from_panel_access_door(data)

        assert door.door_type == "PANEL"
        assert door.title == "Panel Door"
        assert door.visible is True


class TestPairing:
    """Tests for Pairing class."""

    def test_from_dict_minimal(self):
        """Test creating Pairing with minimal data."""
        data = {
            "id": "pairing123",
            "deviceId": "device456",
            "tag": "My Door",
        }
        pairing = Pairing.from_dict(data)

        assert pairing.id == "pairing123"
        assert pairing.device_id == "device456"
        assert pairing.tag == "My Door"
        assert pairing.access_doors == []
        assert pairing.panel_access_doors == []

    def test_from_dict_with_doors(self):
        """Test creating Pairing with access doors."""
        data = {
            "id": "pairing123",
            "deviceId": "device456",
            "tag": "My Door",
            "accessDoorMap": {
                "ZERO": {
                    "accessId": {"block": 0, "subblock": -1, "number": 0},
                    "title": "F1",
                    "visible": True,
                },
                "ONE": {
                    "accessId": {"block": 0, "subblock": -1, "number": 1},
                    "title": "F2",
                    "visible": False,
                },
            },
        }
        pairing = Pairing.from_dict(data)

        assert len(pairing.access_doors) == 2
        visible_doors = pairing.all_visible_doors
        assert len(visible_doors) == 1
        assert visible_doors[0].title == "F1"

    def test_all_visible_doors_ignores_panel(self):
        """Test that panelAccessDoors are ignored, only accessDoorMap used."""
        data = {
            "id": "pairing1",
            "deviceId": "dev1",
            "accessDoorMap": {
                "ZERO": {
                    "accessId": {"block": 1, "subblock": 0, "number": 1},
                    "title": "Door ZERO",
                    "visible": True
                }
            },
            "panelAccessDoors": [
                {
                    "doorId": {"block": 1, "subblock": 0, "number": 1},
                    "title": "Panel Door",
                    "isVisible": True
                }
            ]
        }
        pairing = Pairing.from_dict(data)
        
        visible_doors = pairing.all_visible_doors
        assert len(visible_doors) == 1
        assert visible_doors[0].title == "Door ZERO"
        assert visible_doors[0].door_type == "ZERO"




class TestDeviceInfo:
    """Tests for DeviceInfo class."""

    def test_from_dict(self):
        """Test creating DeviceInfo from dict."""
        data = {
            "deviceId": "device123",
            "connectionState": "Connected",
            "status": "ENABLED",
            "wirelessSignal": 4,
            "photocaller": True,
        }
        device = DeviceInfo.from_dict(data)

        assert device.device_id == "device123"
        assert device.connection_state == "Connected"
        assert device.is_connected is True
        assert device.wireless_signal == 4
        assert device.photocaller is True

    def test_is_connected_case_insensitive(self):
        """Test is_connected works with different cases."""
        data = {"connectionState": "CONNECTED"}
        device = DeviceInfo.from_dict(data)
        assert device.is_connected is True

        data = {"connectionState": "disconnected"}
        device = DeviceInfo.from_dict(data)
        assert device.is_connected is False


class TestCallRecord:
    """Tests for CallRecord class."""

    def test_from_dict(self):
        """Test creating CallRecord from dict."""
        data = {
            "registryId": "call123",
            "deviceId": "device456",
            "callDate": "2025-01-10T15:30:00+01:00",
            "registerCall": "M",
            "isAutoon": False,
            "photoId": "photo789",
            "roomId": "room001",
        }
        record = CallRecord.from_dict(data)

        assert record.registry_id == "call123"
        assert record.device_id == "device456"
        assert record.register_call == "M"
        assert record.is_missed is True
        assert record.is_answered is False
        assert record.has_photo is True
        assert record.photo_id == "photo789"

    def test_from_dict_no_photo(self):
        """Test CallRecord with null photoId."""
        data = {
            "registryId": "call123",
            "deviceId": "device456",
            "callDate": "2025-01-10T15:30:00+01:00",
            "registerCall": "P",
            "isAutoon": False,
            "photoId": None,
            "roomId": "room001",
        }
        record = CallRecord.from_dict(data)

        assert record.has_photo is False
        assert record.is_missed is False
        assert record.is_answered is True


class TestUser:
    """Tests for User class."""

    def test_from_dict(self):
        """Test creating User from dict."""
        data = {
            "id": "user123",
            "email": "test@example.com",
            "locale": "en",
            "enabled": True,
            "provider": "email",
        }
        user = User.from_dict(data)

        assert user.id == "user123"
        assert user.email == "test@example.com"
        assert user.locale == "en"
        assert user.enabled is True


class TestPanel:
    """Tests for Panel class."""

    def test_from_dict(self):
        """Test creating Panel from dict."""
        data = {
            "serialNumber": "SN123456",
            "installationId": "inst789",
            "family": "DUOX",
            "type": "Panel",
            "subtype": "Access",
            "deployed": True,
            "status": True,
        }
        panel = Panel.from_dict(data)

        assert panel.serial_number == "SN123456"
        assert panel.installation_id == "inst789"
        assert panel.family == "DUOX"
        assert panel.deployed is True
