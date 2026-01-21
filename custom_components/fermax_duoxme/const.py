"""Constants for the Fermax DuoxMe integration."""

from typing import Final

# Integration domain
DOMAIN: Final = "fermax_duoxme"

# API Configuration
API_BASE_URL: Final = "https://pro-duoxme.fermax.io"
OAUTH_URL: Final = "https://oauth-pro-duoxme.fermax.io"

# OAuth2 credentials (public, extracted from app)
CLIENT_ID: Final = "dpv7iqz6ee5mazm1iq9dw1d42slyut48kj0mp5fvo58j5ih"
CLIENT_SECRET: Final = "c7ylkqpujwah85yhnprv0wdvyzutlcnkw4sz90buldbulk1"

# API headers
APP_VERSION: Final = "4.2.5"
APP_BUILD: Final = "2"

# Default configuration
DEFAULT_POLLING_INTERVAL: Final = 30  # seconds
MIN_POLLING_INTERVAL: Final = 15
MAX_POLLING_INTERVAL: Final = 300

# Failure tolerance - number of consecutive failures before marking entities unavailable
MAX_CONSECUTIVE_FAILURES: Final = 3

# Token lifetimes (from API documentation)
ACCESS_TOKEN_DEFAULT_LIFETIME: Final = 345599 # ~4 days
REFRESH_TOKEN_LIFETIME_YEARS: Final = 5

# Platforms
PLATFORMS: Final = [
    "lock",
    "binary_sensor",
    "sensor",
]

# Configuration keys
CONF_POLLING_INTERVAL: Final = "polling_interval"
CONF_DEVICES: Final = "devices"

# Attributes
ATTR_DEVICE_ID: Final = "device_id"
ATTR_INSTALLATION_ID: Final = "installation_id"
ATTR_WIRELESS_SIGNAL: Final = "wireless_signal"
ATTR_CONNECTION_STATE: Final = "connection_state"

# Door types
DOOR_TYPE_ZERO: Final = "ZERO"
DOOR_TYPE_ONE: Final = "ONE"
DOOR_TYPE_GENERAL: Final = "GENERAL"

# Call registry types
CALL_REGISTRY_ALL: Final = "all"
CALL_REGISTRY_MISSED: Final = "missed_call"
CALL_REGISTRY_AUTOON: Final = "autoon"

# Event types
EVENT_FERMAX_CALL: Final = "fermax_call"
