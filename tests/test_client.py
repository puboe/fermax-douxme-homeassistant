"""Tests for API client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
import base64

from custom_components.fermax_duoxme.api.client import FermaxApiClient, FermaxApiError
from custom_components.fermax_duoxme.api.models import DoorId


def create_mock_response(status=200, json_data=None, text_data=None, content_type="application/json"):
    """Create a properly configured mock response for aiohttp."""
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.headers = {"Content-Type": content_type}
    mock_response.json = AsyncMock(return_value=json_data)
    mock_response.text = AsyncMock(return_value=text_data or "")
    return mock_response


class MockContextManager:
    """Async context manager wrapper for mock responses."""
    
    def __init__(self, response):
        self.response = response
    
    async def __aenter__(self):
        return self.response
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


class TestFermaxApiClient:
    """Tests for FermaxApiClient class."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def mock_auth(self):
        """Create a mock FermaxAuth."""
        auth = MagicMock()
        auth.ensure_valid_token = AsyncMock()
        auth.get_auth_header = MagicMock(return_value={"Authorization": "Bearer test"})
        auth.refresh_token = AsyncMock()
        return auth

    @pytest.fixture
    def client(self, mock_session, mock_auth):
        """Create a FermaxApiClient instance."""
        return FermaxApiClient(mock_session, mock_auth)

    def test_common_headers(self, client):
        """Test common headers are correct."""
        headers = client._common_headers
        assert "app-version" in headers
        assert "app-build" in headers
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_get_pairings_success(self, client, mock_session):
        """Test successful get_pairings call."""
        mock_response = create_mock_response(json_data=[
            {
                "id": "pairing123",
                "deviceId": "device456",
                "tag": "Test Door",
                "accessDoorMap": {},
            }
        ])
        mock_session.request = MagicMock(return_value=MockContextManager(mock_response))

        pairings = await client.get_pairings()

        assert len(pairings) == 1
        assert pairings[0].id == "pairing123"
        assert pairings[0].device_id == "device456"
        assert pairings[0].tag == "Test Door"

    @pytest.mark.asyncio
    async def test_get_pairings_empty(self, client, mock_session):
        """Test get_pairings with no pairings."""
        mock_response = create_mock_response(json_data=[])
        mock_session.request = MagicMock(return_value=MockContextManager(mock_response))

        pairings = await client.get_pairings()
        assert pairings == []

    @pytest.mark.asyncio
    async def test_get_device_success(self, client, mock_session):
        """Test successful get_device call."""
        mock_response = create_mock_response(json_data={
            "deviceId": "device123",
            "connectionState": "Connected",
            "wirelessSignal": 4,
            "photocaller": True,
        })
        mock_session.request = MagicMock(return_value=MockContextManager(mock_response))

        device = await client.get_device("device123")

        assert device is not None
        assert device.device_id == "device123"
        assert device.is_connected is True
        assert device.wireless_signal == 4

    @pytest.mark.asyncio
    async def test_get_device_not_found(self, client, mock_session):
        """Test get_device with 404 response."""
        mock_response = create_mock_response(status=404)
        mock_session.request = MagicMock(return_value=MockContextManager(mock_response))

        device = await client.get_device("nonexistent")
        assert device is None

    @pytest.mark.asyncio
    async def test_open_door_success(self, client, mock_session):
        """Test successful door open."""
        mock_response = create_mock_response(
            status=200,
            text_data="la puerta abierta",
            content_type="text/plain"
        )
        mock_session.request = MagicMock(return_value=MockContextManager(mock_response))

        door_id = DoorId(block=0, subblock=-1, number=0)
        result = await client.open_door("device123", door_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_get_photo_success(self, client, mock_session):
        """Test successful photo retrieval."""
        # Create a small test image
        test_image = b"\x89PNG\r\n\x1a\n\x00\x00"
        encoded = base64.b64encode(test_image).decode()

        mock_response = create_mock_response(json_data={
            "image": {"data": encoded}
        })
        mock_session.request = MagicMock(return_value=MockContextManager(mock_response))

        photo = await client.get_photo("photo123")

        assert photo is not None
        assert photo == test_image

    @pytest.mark.asyncio
    async def test_get_photo_not_found(self, client, mock_session):
        """Test photo retrieval with 404."""
        mock_response = create_mock_response(status=404)
        mock_session.request = MagicMock(return_value=MockContextManager(mock_response))

        photo = await client.get_photo("nonexistent")
        assert photo is None

    @pytest.mark.asyncio
    async def test_get_user_success(self, client, mock_session):
        """Test successful get_user call."""
        mock_response = create_mock_response(json_data={
            "id": "user123",
            "email": "test@example.com",
            "locale": "en",
            "enabled": True,
        })
        mock_session.request = MagicMock(return_value=MockContextManager(mock_response))

        user = await client.get_user()

        assert user.id == "user123"
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_api_error_handling(self, client, mock_session):
        """Test API error handling for 500 status."""
        mock_response = create_mock_response(status=500, text_data="Internal Server Error")
        mock_session.request = MagicMock(return_value=MockContextManager(mock_response))

        with pytest.raises(FermaxApiError) as exc_info:
            await client.get_user()

        assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_services_success(self, client, mock_session):
        """Test successful get_services call."""
        mock_response = create_mock_response(json_data=["opendoor", "camera", "notifications"])
        mock_session.request = MagicMock(return_value=MockContextManager(mock_response))

        services = await client.get_services("device123")

        assert len(services) == 3
        assert "opendoor" in services

    @pytest.mark.asyncio
    async def test_get_panels_success(self, client, mock_session):
        """Test successful get_panels call."""
        mock_response = create_mock_response(json_data=[
            {
                "serialNumber": "SN123",
                "installationId": "inst456",
                "family": "DUOX",
                "type": "Panel",
            }
        ])
        mock_session.request = MagicMock(return_value=MockContextManager(mock_response))

        panels = await client.get_panels("device123")

        assert len(panels) == 1
        assert panels[0].serial_number == "SN123"
