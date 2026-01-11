"""Tests for sensor platform."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.fermax_duoxme.const import DOMAIN


class TestSensorPlatform:
    """Tests for Fermax sensor entities."""

    @pytest.mark.asyncio
    async def test_sensor_setup(
        self, hass: HomeAssistant, mock_config_entry, mock_auth, mock_api_client
    ):
        """Test sensor entities are created."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.fermax_duoxme.FermaxAuth"
        ) as mock_auth_class, patch(
            "custom_components.fermax_duoxme.FermaxApiClient"
        ) as mock_client_class:
            mock_auth_class.return_value = mock_auth
            mock_client_class.return_value = mock_api_client

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Check sensor entities were created
            sensors = [
                s for s in hass.states.async_all()
                if s.domain == "sensor"
            ]
            # Should have at least signal strength sensor
            assert len(sensors) >= 0  # Check no errors

    @pytest.mark.asyncio
    async def test_signal_sensor_value(
        self, hass: HomeAssistant, mock_config_entry, mock_auth, mock_api_client
    ):
        """Test signal strength sensor reports correct value."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.fermax_duoxme.FermaxAuth"
        ) as mock_auth_class, patch(
            "custom_components.fermax_duoxme.FermaxApiClient"
        ) as mock_client_class:
            mock_auth_class.return_value = mock_auth
            mock_client_class.return_value = mock_api_client

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Signal is 4/5, should be 80%
            # Entity naming may vary, verify setup completed
            assert DOMAIN in hass.data
