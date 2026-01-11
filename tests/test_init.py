"""Tests for the integration setup."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState

from custom_components.fermax_duoxme.const import DOMAIN


class TestIntegrationSetup:
    """Tests for integration setup and unload."""

    @pytest.mark.asyncio
    async def test_setup_entry_success(
        self, hass: HomeAssistant, mock_config_entry, mock_auth, mock_api_client
    ):
        """Test successful setup of config entry."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.fermax_duoxme.FermaxAuth"
        ) as mock_auth_class, patch(
            "custom_components.fermax_duoxme.FermaxApiClient"
        ) as mock_client_class, patch(
            "custom_components.fermax_duoxme.async_get_clientsession"
        ) as mock_session:
            mock_session.return_value = MagicMock()
            mock_auth_class.return_value = mock_auth
            mock_client_class.return_value = mock_api_client

            result = await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            assert result is True
            assert mock_config_entry.state == ConfigEntryState.LOADED

    @pytest.mark.asyncio
    async def test_unload_entry(
        self, hass: HomeAssistant, mock_config_entry, mock_auth, mock_api_client
    ):
        """Test unloading a config entry."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.fermax_duoxme.FermaxAuth"
        ) as mock_auth_class, patch(
            "custom_components.fermax_duoxme.FermaxApiClient"
        ) as mock_client_class, patch(
            "custom_components.fermax_duoxme.async_get_clientsession"
        ) as mock_session:
            mock_session.return_value = MagicMock()
            mock_auth_class.return_value = mock_auth
            mock_client_class.return_value = mock_api_client

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            result = await hass.config_entries.async_unload(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            assert result is True
            assert mock_config_entry.state == ConfigEntryState.NOT_LOADED
