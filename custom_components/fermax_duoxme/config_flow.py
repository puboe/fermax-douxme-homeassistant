"""Config flow for Fermax DuoxMe integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FermaxApiClient, FermaxAuth
from .api.auth import FermaxAuthError, InvalidCredentialsError
from .const import (
    CONF_DEVICES,
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    MAX_POLLING_INTERVAL,
    MIN_POLLING_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Config entry data keys
CONF_TOKEN_DATA = "token_data"

# Step IDs
STEP_USER = "user"
STEP_DEVICES = "devices"


class FermaxDuoxmeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fermax DuoxMe."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._username: str | None = None
        self._password: str | None = None
        self._auth: FermaxAuth | None = None
        self._client: FermaxApiClient | None = None
        self._devices: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - user credentials.

        Args:
            user_input: User input from the form

        Returns:
            FlowResult for next step or form with errors
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]

            # Try to authenticate
            session = async_get_clientsession(self.hass)
            self._auth = FermaxAuth(session)

            try:
                await self._auth.authenticate(self._username, self._password)
                self._client = FermaxApiClient(session, self._auth)

                # Get pairings to validate and show device selection
                pairings = await self._client.get_pairings()

                if not pairings:
                    errors["base"] = "no_devices"
                else:
                    # Store devices for next step
                    self._devices = [
                        {
                            "device_id": p.device_id,
                            "tag": p.tag,
                            "address": p.address,
                            "enabled": True,
                        }
                        for p in pairings
                    ]

                    # If only one device, skip device selection
                    if len(self._devices) == 1:
                        return await self._async_create_entry()

                    # Show device selection step
                    return await self.async_step_devices()

            except InvalidCredentialsError:
                errors["base"] = "invalid_auth"
            except FermaxAuthError as err:
                _LOGGER.error("Authentication error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id=STEP_USER,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device selection step.

        Args:
            user_input: User input from the form

        Returns:
            FlowResult for entry creation or form
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Update device enabled status based on selection
            selected_devices = user_input.get(CONF_DEVICES, [])
            for device in self._devices:
                device["enabled"] = device["device_id"] in selected_devices

            # Ensure at least one device is selected
            if not any(d["enabled"] for d in self._devices):
                errors["base"] = "no_devices_selected"
            else:
                return await self._async_create_entry()

        # Build device selection options
        device_options = {
            device["device_id"]: f"{device['tag']} ({device['address']})"
            for device in self._devices
        }

        # Default to all devices selected
        default_selected = [d["device_id"] for d in self._devices]

        return self.async_show_form(
            step_id=STEP_DEVICES,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICES, default=default_selected
                    ): vol.All(
                        vol.Coerce(list),
                        [vol.In(device_options)],
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "device_count": str(len(self._devices)),
            },
        )

    async def _async_create_entry(self) -> FlowResult:
        """Create the config entry.

        Returns:
            FlowResult with created entry
        """
        # Check if already configured with same username
        await self.async_set_unique_id(self._username)
        self._abort_if_unique_id_configured()

        # Build entry data
        entry_data = {
            CONF_USERNAME: self._username,
            CONF_PASSWORD: self._password,
            CONF_DEVICES: self._devices,
        }

        # Add token data if available
        if self._auth and self._auth.token_data:
            entry_data[CONF_TOKEN_DATA] = self._auth.token_data.to_dict()

        # Use first device tag as title, or username
        title = self._username
        enabled_devices = [d for d in self._devices if d.get("enabled", True)]
        if enabled_devices:
            title = enabled_devices[0].get("tag", self._username)

        return self.async_create_entry(title=title, data=entry_data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler.

        Args:
            config_entry: The config entry

        Returns:
            OptionsFlow instance
        """
        return FermaxDuoxmeOptionsFlow(config_entry)


class FermaxDuoxmeOptionsFlow(OptionsFlow):
    """Handle options flow for Fermax DuoxMe."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow.

        Args:
            config_entry: The config entry
        """
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options.

        Args:
            user_input: User input from the form

        Returns:
            FlowResult with updated options or form
        """
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current options
        current_polling = self._config_entry.options.get(
            CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLLING_INTERVAL,
                        default=current_polling,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_POLLING_INTERVAL,
                            max=MAX_POLLING_INTERVAL,
                        ),
                    ),
                }
            ),
        )
