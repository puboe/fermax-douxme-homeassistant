"""API package for Fermax DuoxMe integration."""

from .auth import FermaxAuth, TokenData
from .client import FermaxApiClient
from .models import (
    AccessDoor,
    CallRecord,
    DeviceInfo,
    DoorId,
    Pairing,
    Panel,
    User,
)

__all__ = [
    "FermaxApiClient",
    "FermaxAuth",
    "TokenData",
    "AccessDoor",
    "CallRecord",
    "DeviceInfo",
    "DoorId",
    "Pairing",
    "Panel",
    "User",
]
