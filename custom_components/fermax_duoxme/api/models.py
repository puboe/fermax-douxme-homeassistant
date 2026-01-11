"""Data models for Fermax DuoxMe API responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DoorId:
    """Represents a door identifier for opening doors."""

    block: int
    subblock: int
    number: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DoorId:
        """Create DoorId from API response dict."""
        return cls(
            block=int(data.get("block", 0)),
            subblock=int(data.get("subblock", -1)),
            number=int(data.get("number", 0)),
        )

    def to_dict(self) -> dict[str, int]:
        """Convert to dict for API request."""
        return {
            "block": self.block,
            "subblock": self.subblock,
            "number": self.number,
        }


@dataclass
class AccessDoor:
    """Represents a door that can be opened."""

    door_id: DoorId
    title: str
    visible: bool
    door_type: str  # ZERO, ONE, GENERAL, or panel door

    @classmethod
    def from_access_door_map(
        cls, door_type: str, data: dict[str, Any]
    ) -> AccessDoor:
        """Create AccessDoor from accessDoorMap entry."""
        access_id = data.get("accessId", {})
        return cls(
            door_id=DoorId.from_dict(access_id),
            title=data.get("title", "") or door_type,
            visible=data.get("visible", False),
            door_type=door_type,
        )

    @classmethod
    def from_panel_access_door(cls, data: dict[str, Any]) -> AccessDoor:
        """Create AccessDoor from panelAccessDoors entry."""
        door_id_data = data.get("doorId", {})
        return cls(
            door_id=DoorId.from_dict(door_id_data),
            title=data.get("title", "") or "Panel Door",
            visible=data.get("isVisible", True),
            door_type="PANEL",
        )


@dataclass
class Pairing:
    """Represents a device pairing."""

    id: str
    device_id: str
    user_id: str
    user_email: str
    tag: str
    installation_id: str
    address: str
    status: str
    is_master: bool
    enabled: bool
    pairing_type: str  # WIFI, etc.
    access_doors: list[AccessDoor] = field(default_factory=list)
    panel_access_doors: list[AccessDoor] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Pairing:
        """Create Pairing from API response dict."""
        # Parse accessDoorMap
        access_doors = []
        access_door_map = data.get("accessDoorMap", {})
        for door_type, door_data in access_door_map.items():
            access_doors.append(
                AccessDoor.from_access_door_map(door_type, door_data)
            )

        # Parse panelAccessDoors
        panel_access_doors = []
        for panel_door in data.get("panelAccessDoors", []):
            panel_access_doors.append(
                AccessDoor.from_panel_access_door(panel_door)
            )

        return cls(
            id=data.get("id", ""),
            device_id=data.get("deviceId", ""),
            user_id=data.get("userId", ""),
            user_email=data.get("userEmail", ""),
            tag=data.get("tag", ""),
            installation_id=data.get("installationId", ""),
            address=data.get("address", ""),
            status=data.get("status", ""),
            is_master=data.get("isMaster", False),
            enabled=data.get("enabled", True),
            pairing_type=data.get("type", ""),
            access_doors=access_doors,
            panel_access_doors=panel_access_doors,
        )

    @property
    def all_visible_doors(self) -> list[AccessDoor]:
        """Get all visible doors from both accessDoorMap and panelAccessDoors."""
        visible = [d for d in self.access_doors if d.visible]
        visible.extend([d for d in self.panel_access_doors if d.visible])
        return visible


@dataclass
class DeviceInfo:
    """Represents device information."""

    device_id: str
    connection_state: str
    status: str
    installation_id: str
    family: str
    device_type: str
    subtype: str
    unit_number: int
    connectable: bool
    photocaller: bool
    wireless_signal: int
    is_monitor: bool
    streaming_mode: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceInfo:
        """Create DeviceInfo from API response dict."""
        return cls(
            device_id=data.get("deviceId", ""),
            connection_state=data.get("connectionState", ""),
            status=data.get("status", ""),
            installation_id=data.get("installationId", ""),
            family=data.get("family", ""),
            device_type=data.get("type", ""),
            subtype=data.get("subtype", ""),
            unit_number=data.get("unitNumber", 0),
            connectable=data.get("connectable", False),
            photocaller=data.get("photocaller", False),
            wireless_signal=data.get("wirelessSignal", 0),
            is_monitor=data.get("isMonitor", False),
            streaming_mode=data.get("streamingMode", ""),
        )

    @property
    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self.connection_state.lower() == "connected"


@dataclass
class CallRecord:
    """Represents a call history record."""

    registry_id: str
    device_id: str
    call_date: datetime
    register_call: str  # M = missed, P = picked up
    is_autoon: bool
    photo_id: str | None
    room_id: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CallRecord:
        """Create CallRecord from API response dict."""
        call_date_str = data.get("callDate", "")
        try:
            # Parse ISO 8601 datetime with timezone
            call_date = datetime.fromisoformat(call_date_str)
        except (ValueError, TypeError):
            call_date = datetime.now()

        return cls(
            registry_id=data.get("registryId", ""),
            device_id=data.get("deviceId", ""),
            call_date=call_date,
            register_call=data.get("registerCall", ""),
            is_autoon=data.get("isAutoon", False),
            photo_id=data.get("photoId"),
            room_id=data.get("roomId", ""),
        )

    @property
    def is_missed(self) -> bool:
        """Check if this was a missed call."""
        return self.register_call == "M"

    @property
    def is_answered(self) -> bool:
        """Check if this call was answered."""
        return self.register_call == "P"

    @property
    def has_photo(self) -> bool:
        """Check if this call has an associated photo."""
        return self.photo_id is not None


@dataclass
class User:
    """Represents user information."""

    id: str
    email: str
    locale: str
    enabled: bool
    provider: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User:
        """Create User from API response dict."""
        return cls(
            id=data.get("id", ""),
            email=data.get("email", ""),
            locale=data.get("locale", "en"),
            enabled=data.get("enabled", True),
            provider=data.get("provider", ""),
        )


@dataclass
class Panel:
    """Represents a panel/door unit."""

    serial_number: str
    installation_id: str
    family: str
    panel_type: str
    subtype: str
    deployed: bool
    status: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Panel:
        """Create Panel from API response dict."""
        return cls(
            serial_number=data.get("serialNumber", ""),
            installation_id=data.get("installationId", ""),
            family=data.get("family", ""),
            panel_type=data.get("type", ""),
            subtype=data.get("subtype", ""),
            deployed=data.get("deployed", False),
            status=data.get("status", False),
        )
