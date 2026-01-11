"""Pytest configuration for Fermax DuoxMe tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import Home Assistant test fixtures
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

from custom_components.fermax_duoxme.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Door",
        data={
            "username": "test@example.com",
            "password": "testpass",
            "devices": [
                {
                    "device_id": "device123",
                    "tag": "Test Door",
                    "address": "123 Main St",
                    "enabled": True,
                }
            ],
        },
        options={
            "polling_interval": 30,
        },
        unique_id="test@example.com",
    )


@pytest.fixture
def mock_pairing():
    """Create a mock Pairing object."""
    from custom_components.fermax_duoxme.api.models import Pairing
    
    return Pairing.from_dict({
        "id": "pairing123",
        "deviceId": "device123",
        "userId": "user456",
        "userEmail": "test@example.com",
        "tag": "Test Door",
        "installationId": "inst789",
        "address": "123 Main St",
        "status": "ENABLED",
        "isMaster": True,
        "enabled": True,
        "type": "WIFI",
        "accessDoorMap": {
            "ZERO": {
                "accessId": {"block": 0, "subblock": -1, "number": 0},
                "title": "F1",
                "visible": True,
            },
            "ONE": {
                "accessId": {"block": 0, "subblock": -1, "number": 1},
                "title": "F2",
                "visible": True,
            },
        },
    })


@pytest.fixture
def mock_device_info():
    """Create a mock DeviceInfo object."""
    from custom_components.fermax_duoxme.api.models import DeviceInfo
    
    return DeviceInfo.from_dict({
        "deviceId": "device123",
        "connectionState": "Connected",
        "status": "ENABLED",
        "installationId": "inst789",
        "family": "DUOX",
        "type": "WIFI",
        "subtype": "STANDARD",
        "unitNumber": 1,
        "connectable": True,
        "photocaller": True,
        "wirelessSignal": 4,
        "isMonitor": False,
        "streamingMode": "STANDARD",
    })


@pytest.fixture
def mock_auth():
    """Create a mock FermaxAuth."""
    auth = MagicMock()
    auth.is_authenticated = True
    auth.ensure_valid_token = AsyncMock()
    auth.authenticate = AsyncMock()
    auth.refresh_token = AsyncMock()
    auth.get_auth_header = MagicMock(return_value={"Authorization": "Bearer test_token"})
    auth.token_data = MagicMock()
    auth.token_data.to_dict = MagicMock(return_value={
        "access_token": "test_token",
        "refresh_token": "test_refresh",
        "token_type": "Bearer",
        "expires_in": 345600,
        "created_at": "2026-01-10T00:00:00",
    })
    return auth


@pytest.fixture
def mock_api_client(mock_pairing, mock_device_info):
    """Create a mock FermaxApiClient."""
    client = MagicMock()
    client.get_pairings = AsyncMock(return_value=[mock_pairing])
    client.get_device = AsyncMock(return_value=mock_device_info)
    client.get_services = AsyncMock(return_value=["opendoor", "camera"])
    client.get_panels = AsyncMock(return_value=[])
    client.open_door = AsyncMock(return_value=True)
    client.get_photo = AsyncMock(return_value=None)
    client.get_user = AsyncMock()
    return client
