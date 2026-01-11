"""The Fermax DuoxMe integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FermaxApiClient, FermaxAuth, TokenData
from .api.auth import FermaxAuthError, InvalidCredentialsError, TokenRefreshError
from .const import DOMAIN, PLATFORMS
from .coordinator import FermaxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Config entry data keys
CONF_TOKEN_DATA = "token_data"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fermax DuoxMe from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        True if setup was successful
    """
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    auth = FermaxAuth(session)

    # Restore token data from config entry if available
    token_data_dict = entry.data.get(CONF_TOKEN_DATA)
    if token_data_dict:
        auth.token_data = TokenData.from_stored_dict(token_data_dict)
        _LOGGER.debug("Restored token data from config entry")

    # If token is expired or missing, re-authenticate
    if not auth.is_authenticated:
        username = entry.data.get(CONF_USERNAME)
        password = entry.data.get(CONF_PASSWORD)

        if not username or not password:
            raise ConfigEntryAuthFailed("Missing credentials")

        try:
            await auth.authenticate(username, password)
            # Save new token data
            new_data = {**entry.data, CONF_TOKEN_DATA: auth.token_data.to_dict()}
            hass.config_entries.async_update_entry(entry, data=new_data)
            _LOGGER.debug("Re-authenticated and saved new token")
        except InvalidCredentialsError as err:
            raise ConfigEntryAuthFailed("Invalid credentials") from err
        except FermaxAuthError as err:
            raise ConfigEntryNotReady(f"Authentication failed: {err}") from err

    # Create API client
    client = FermaxApiClient(session, auth)

    # Create coordinator
    coordinator = FermaxDataUpdateCoordinator(hass, client, entry)

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to fetch initial data: {err}") from err

    # Store coordinator and client for platforms
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
        "auth": auth,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        True if unload was successful
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update.

    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry to new version.

    Args:
        hass: Home Assistant instance
        config_entry: Config entry

    Returns:
        True if migration was successful
    """
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    # No migrations needed yet
    return True
