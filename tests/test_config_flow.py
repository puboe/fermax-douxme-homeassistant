"""Tests for config flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType

from custom_components.fermax_duoxme.const import DOMAIN


class TestConfigFlow:
    """Tests for FermaxDuoxmeConfigFlow."""

    @pytest.mark.asyncio
    async def test_form_shows_initially(self, hass):
        """Test that the form is shown initially."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    @pytest.mark.asyncio
    async def test_form_invalid_auth(self, hass):
        """Test handling of invalid auth."""
        with patch(
            "custom_components.fermax_duoxme.config_flow.async_get_clientsession"
        ) as mock_session, patch(
            "custom_components.fermax_duoxme.config_flow.FermaxAuth"
        ) as mock_auth_class:
            from custom_components.fermax_duoxme.api.auth import InvalidCredentialsError
            
            mock_session.return_value = MagicMock()
            mock_auth = MagicMock()
            mock_auth.authenticate = AsyncMock(
                side_effect=InvalidCredentialsError("Invalid")
            )
            mock_auth_class.return_value = mock_auth

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_USERNAME: "bad@example.com",
                    CONF_PASSWORD: "wrongpass",
                },
            )

            assert result2["type"] == FlowResultType.FORM
            assert result2["errors"] == {"base": "invalid_auth"}

    @pytest.mark.asyncio
    async def test_form_success_single_device(self, hass, mock_pairing, mock_auth):
        """Test successful config flow with single device."""
        with patch(
            "custom_components.fermax_duoxme.config_flow.async_get_clientsession"
        ) as mock_session, patch(
            "custom_components.fermax_duoxme.config_flow.FermaxAuth"
        ) as mock_auth_class, patch(
            "custom_components.fermax_duoxme.config_flow.FermaxApiClient"
        ) as mock_client_class:
            mock_session.return_value = MagicMock()
            mock_auth_class.return_value = mock_auth
            
            mock_client = MagicMock()
            mock_client.get_pairings = AsyncMock(return_value=[mock_pairing])
            mock_client_class.return_value = mock_client

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "testpass",
                },
            )

            # With single device, should create entry directly
            assert result2["type"] == FlowResultType.CREATE_ENTRY
            assert result2["title"] == "Test Door"
            assert result2["data"][CONF_USERNAME] == "test@example.com"

    @pytest.mark.asyncio
    async def test_form_no_devices(self, hass, mock_auth):
        """Test handling of no devices found."""
        with patch(
            "custom_components.fermax_duoxme.config_flow.async_get_clientsession"
        ) as mock_session, patch(
            "custom_components.fermax_duoxme.config_flow.FermaxAuth"
        ) as mock_auth_class, patch(
            "custom_components.fermax_duoxme.config_flow.FermaxApiClient"
        ) as mock_client_class:
            mock_session.return_value = MagicMock()
            mock_auth_class.return_value = mock_auth
            
            mock_client = MagicMock()
            mock_client.get_pairings = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_client

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "testpass",
                },
            )

            assert result2["type"] == FlowResultType.FORM
            assert result2["errors"] == {"base": "no_devices"}
