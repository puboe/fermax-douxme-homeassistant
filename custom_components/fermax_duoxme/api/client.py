"""Fermax DuoxMe API client."""

from __future__ import annotations

import base64
import logging
from typing import Any

import aiohttp

from ..const import (
    API_BASE_URL,
    APP_BUILD,
    APP_VERSION,
    CALL_REGISTRY_ALL,
)
from .auth import FermaxAuth, FermaxAuthError
from .models import (
    CallRecord,
    DeviceInfo,
    DoorId,
    Pairing,
    Panel,
    User,
)

_LOGGER = logging.getLogger(__name__)


class FermaxApiError(Exception):
    """Base exception for API errors."""


class FermaxApiClient:
    """Client for Fermax DuoxMe API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        auth: FermaxAuth,
    ) -> None:
        """Initialize the API client.

        Args:
            session: aiohttp client session
            auth: FermaxAuth instance for authentication
        """
        self._session = session
        self._auth = auth

    @property
    def _common_headers(self) -> dict[str, str]:
        """Common headers for API requests."""
        return {
            "app-version": APP_VERSION,
            "app-build": APP_BUILD,
            "Content-Type": "application/json",
            "Accept": "*/*",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        retry_on_auth_error: bool = True,
    ) -> Any:
        """Make an authenticated API request.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body data
            retry_on_auth_error: Whether to retry after refreshing token

        Returns:
            Parsed JSON response

        Raises:
            FermaxApiError: For API errors
            FermaxAuthError: For authentication errors
        """
        url = f"{API_BASE_URL}{endpoint}"

        # Ensure we have a valid token
        await self._auth.ensure_valid_token()

        headers = {
            **self._common_headers,
            **self._auth.get_auth_header(),
        }

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data,
            ) as response:
                # Handle 401 - try to refresh token and retry
                if response.status == 401 and retry_on_auth_error:
                    _LOGGER.debug("Got 401, attempting token refresh")
                    await self._auth.refresh_token()
                    return await self._request(
                        method,
                        endpoint,
                        params=params,
                        json_data=json_data,
                        retry_on_auth_error=False,
                    )

                if response.status == 404:
                    return None

                if response.status == 409:
                    # Conflict - e.g., autoon already in progress
                    raise FermaxApiError("Resource conflict (409)")

                if response.status >= 400:
                    error_text = await response.text()
                    raise FermaxApiError(
                        f"API error {response.status}: {error_text}"
                    )

                # Handle empty responses
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return await response.json()
                else:
                    return await response.text()

        except aiohttp.ClientError as err:
            raise FermaxApiError(f"Network error: {err}") from err

    # === User Endpoints ===

    async def get_user(self) -> User:
        """Get current user information.

        Returns:
            User object with profile information
        """
        data = await self._request("GET", "/user/api/v1/users/me")
        return User.from_dict(data)

    # === Pairing Endpoints ===

    async def get_pairings(self) -> list[Pairing]:
        """Get all device pairings for the user.

        Returns:
            List of Pairing objects
        """
        data = await self._request("GET", "/pairing/api/v4/pairings/me")
        if not isinstance(data, list):
            return []
        return [Pairing.from_dict(item) for item in data]

    # === Device Endpoints ===

    async def get_device(self, device_id: str) -> DeviceInfo | None:
        """Get device information.

        Args:
            device_id: The device ID

        Returns:
            DeviceInfo object or None if not found
        """
        data = await self._request(
            "GET", f"/deviceaction/api/v1/device/{device_id}"
        )
        if data is None:
            return None
        return DeviceInfo.from_dict(data)

    async def get_panels(self, device_id: str) -> list[Panel]:
        """Get panels associated with a device.

        Args:
            device_id: The device ID

        Returns:
            List of Panel objects
        """
        data = await self._request(
            "GET", f"/deviceaction/api/v1/device/{device_id}/panels"
        )
        if not isinstance(data, list):
            return []
        return [Panel.from_dict(item) for item in data]

    async def get_services(self, device_id: str) -> list[str]:
        """Get available services for a device.

        Args:
            device_id: The device ID

        Returns:
            List of service names
        """
        data = await self._request(
            "GET",
            f"/services2/api/v1/services/{device_id}",
            params={"deviceType": "wifi"},
        )
        if not isinstance(data, list):
            return []
        return data

    # === Door Control ===

    async def open_door(self, device_id: str, door_id: DoorId) -> bool:
        """Open a door.

        Args:
            device_id: The device ID
            door_id: Door identifier

        Returns:
            True if successful
        """
        try:
            result = await self._request(
                "POST",
                f"/deviceaction/api/v1/device/{device_id}/directed-opendoor",
                params={"unitId": device_id},
                json_data=door_id.to_dict(),
            )
            # Response is "la puerta abierta" on success
            return result is not None
        except FermaxApiError as err:
            _LOGGER.error("Failed to open door: %s", err)
            return False

    # === Call History ===

    async def get_call_history(
        self,
        fcm_token: str,
        call_type: str = CALL_REGISTRY_ALL,
    ) -> list[CallRecord]:
        """Get call history.

        Args:
            fcm_token: FCM push notification token
            call_type: Type filter (all, missed_call, autoon)

        Returns:
            List of CallRecord objects
        """
        data = await self._request(
            "GET",
            "/callManager/api/v1/callregistry/participant",
            params={
                "appToken": fcm_token,
                "callRegistryType": call_type,
            },
        )
        if not isinstance(data, list):
            return []
        return [CallRecord.from_dict(item) for item in data]

    async def delete_call_records(
        self,
        registry_ids: list[str],
        fcm_token: str,
    ) -> bool:
        """Delete call registry entries.

        Args:
            registry_ids: List of registry IDs to delete
            fcm_token: FCM token

        Returns:
            True if successful
        """
        try:
            result = await self._request(
                "DELETE",
                "/callManager/api/v1/callregistry/participants",
                json_data={
                    "participantIds": registry_ids,
                    "fcmToken": fcm_token,
                },
            )
            if isinstance(result, dict):
                return result.get("hidden", False)
            return False
        except FermaxApiError as err:
            _LOGGER.error("Failed to delete call records: %s", err)
            return False

    # === PhotoCaller ===

    async def get_photo(self, photo_id: str) -> bytes | None:
        """Get a photo from a call record.

        Args:
            photo_id: The photo ID from call registry

        Returns:
            Image bytes or None if not found
        """
        try:
            data = await self._request(
                "GET",
                "/callManager/api/v1/photocall",
                params={"photoId": photo_id},
            )
            if data is None:
                return None
            if isinstance(data, dict) and "image" in data:
                image_data = data["image"].get("data", "")
                if image_data:
                    return base64.b64decode(image_data)
            return None
        except FermaxApiError as err:
            _LOGGER.error("Failed to get photo: %s", err)
            return None

    async def get_last_photo(self, device_id: str, fcm_token: str) -> bytes | None:
        """Get the most recent photo for a device.

        Args:
            device_id: The device ID
            fcm_token: FCM token for call history

        Returns:
            Image bytes or None if no photos available
        """
        call_records = await self.get_call_history(fcm_token)

        # Filter to records with photos for this device
        records_with_photos = [
            r for r in call_records
            if r.device_id == device_id and r.has_photo
        ]

        if not records_with_photos:
            return None

        # Get the most recent
        latest = max(records_with_photos, key=lambda r: r.call_date)
        return await self.get_photo(latest.photo_id)  # type: ignore

    # === Notifications ===

    async def get_mute_status(
        self,
        device_id: str,
        fcm_token: str,
    ) -> bool:
        """Get notification mute status.

        Args:
            device_id: The device ID
            fcm_token: FCM token

        Returns:
            True if muted, False if not muted
        """
        result = await self._request(
            "GET",
            "/notification/api/v1/mutedevice/me",
            params={
                "deviceId": device_id,
                "token": fcm_token,
            },
        )
        # Response is raw boolean
        if isinstance(result, bool):
            return result
        if isinstance(result, str):
            return result.lower() == "true"
        return False

    async def register_app_token(
        self,
        fcm_token: str,
        active: bool = True,
        device_model: str = "HomeAssistant",
        locale: str = "en",
    ) -> bool:
        """Register or update FCM token.

        Args:
            fcm_token: FCM push notification token
            active: Whether to activate notifications
            device_model: Device model name
            locale: User locale

        Returns:
            True if successful
        """
        try:
            result = await self._request(
                "POST",
                "/notification/api/v1/apptoken",
                json_data={
                    "token": fcm_token,
                    "os": "Android",
                    "osVersion": "HomeAssistant",
                    "appVersion": APP_VERSION,
                    "appBuild": APP_BUILD,
                    "phoneMobile": device_model,
                    "locale": locale,
                    "active": active,
                },
            )
            # Response is "Token Updated"
            return result is not None
        except FermaxApiError as err:
            _LOGGER.error("Failed to register app token: %s", err)
            return False
