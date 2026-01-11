"""OAuth2 authentication for Fermax DuoxMe API."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from ..const import (
    API_BASE_URL,
    APP_BUILD,
    APP_VERSION,
    CLIENT_ID,
    CLIENT_SECRET,
    OAUTH_URL,
    ACCESS_TOKEN_DEFAULT_LIFETIME,
)

_LOGGER = logging.getLogger(__name__)

# OAuth2 endpoints
OAUTH_TOKEN_URL = f"{OAUTH_URL}/oauth/token"


@dataclass
class TokenData:
    """OAuth2 token data."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenData:
        """Create TokenData from OAuth response."""
        return cls(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", ACCESS_TOKEN_DEFAULT_LIFETIME),
            created_at=datetime.now(),
        )

    @property
    def expires_at(self) -> datetime:
        """Calculate token expiration time."""
        return self.created_at + timedelta(seconds=self.expires_in)

    @property
    def is_expired(self) -> bool:
        """Check if access token is expired."""
        # Consider expired 5 minutes before actual expiry
        buffer = timedelta(minutes=5)
        return datetime.now() >= (self.expires_at - buffer)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for storage."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_stored_dict(cls, data: dict[str, Any]) -> TokenData:
        """Create TokenData from stored dict."""
        created_at_str = data.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str)
        except (ValueError, TypeError):
            created_at = datetime.now()

        return cls(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", ACCESS_TOKEN_DEFAULT_LIFETIME),
            created_at=created_at,
        )


class FermaxAuthError(Exception):
    """Base exception for authentication errors."""


class InvalidCredentialsError(FermaxAuthError):
    """Raised when credentials are invalid."""


class TokenRefreshError(FermaxAuthError):
    """Raised when token refresh fails."""


class FermaxAuth:
    """Handles OAuth2 authentication for Fermax API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        client_id: str = CLIENT_ID,
        client_secret: str = CLIENT_SECRET,
    ) -> None:
        """Initialize the auth handler."""
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_data: TokenData | None = None

    @property
    def _basic_auth_header(self) -> str:
        """Generate Basic auth header for OAuth requests."""
        credentials = f"{self._client_id}:{self._client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    @property
    def _common_headers(self) -> dict[str, str]:
        """Common headers for API requests."""
        return {
            "app-version": APP_VERSION,
            "app-build": APP_BUILD,
            "Content-Type": "application/x-www-form-urlencoded",
        }

    @property
    def token_data(self) -> TokenData | None:
        """Get current token data."""
        return self._token_data

    @token_data.setter
    def token_data(self, value: TokenData | None) -> None:
        """Set token data (for restoring from storage)."""
        self._token_data = value

    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid authentication."""
        return self._token_data is not None and not self._token_data.is_expired

    async def authenticate(self, username: str, password: str) -> TokenData:
        """Authenticate with username and password.

        Args:
            username: User's email address
            password: User's password

        Returns:
            TokenData with access and refresh tokens

        Raises:
            InvalidCredentialsError: If credentials are invalid
            FermaxAuthError: For other authentication failures
        """
        headers = {
            **self._common_headers,
            "Authorization": self._basic_auth_header,
        }

        data = {
            "grant_type": "password",
            "username": username,
            "password": password,
        }

        try:
            async with self._session.post(
                OAUTH_TOKEN_URL, headers=headers, data=data
            ) as response:
                if response.status == 400:
                    error_data = await response.json()
                    error = error_data.get("error", "")
                    if error == "invalid_grant":
                        _LOGGER.warning("Invalid credentials: %s", error_data)
                        raise InvalidCredentialsError("Invalid username or password")
                    _LOGGER.error("Authentication failed: %s (Data: %s)", error, error_data)
                    raise FermaxAuthError(f"Authentication failed: {error}")

                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("Authentication failed with status %s. Response: %s", response.status, text)
                    raise FermaxAuthError(
                        f"Authentication failed with status {response.status}"
                    )

                token_response = await response.json()
                self._token_data = TokenData.from_dict(token_response)
                _LOGGER.debug("Successfully authenticated with Fermax API")
                return self._token_data

        except aiohttp.ClientError as err:
            raise FermaxAuthError(f"Network error during authentication: {err}") from err

    async def refresh_token(self) -> TokenData:
        """Refresh the access token using the refresh token.

        Returns:
            TokenData with new access token

        Raises:
            TokenRefreshError: If refresh fails
            FermaxAuthError: If no refresh token available
        """
        if self._token_data is None:
            raise FermaxAuthError("No token data available for refresh")

        headers = {
            **self._common_headers,
            "Authorization": self._basic_auth_header,
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._token_data.refresh_token,
        }

        try:
            async with self._session.post(
                OAUTH_TOKEN_URL, headers=headers, data=data
            ) as response:
                if response.status == 400:
                    error_data = await response.json()
                    error = error_data.get("error", "")
                    raise TokenRefreshError(f"Token refresh failed: {error}")

                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("Token refresh failed with status %s. Response: %s", response.status, text)
                    raise TokenRefreshError(
                        f"Token refresh failed with status {response.status}"
                    )

                token_response = await response.json()
                self._token_data = TokenData.from_dict(token_response)
                _LOGGER.debug("Successfully refreshed Fermax API token")
                return self._token_data

        except aiohttp.ClientError as err:
            raise TokenRefreshError(f"Network error during token refresh: {err}") from err

    async def ensure_valid_token(self) -> str:
        """Ensure we have a valid access token, refreshing if needed.

        Returns:
            Valid access token

        Raises:
            FermaxAuthError: If no token and can't refresh
        """
        if self._token_data is None:
            raise FermaxAuthError("Not authenticated")

        if self._token_data.is_expired:
            _LOGGER.debug("Access token expired, refreshing...")
            await self.refresh_token()

        return self._token_data.access_token

    def get_auth_header(self) -> dict[str, str]:
        """Get authorization header for API requests.

        Returns:
            Dict with Authorization header

        Raises:
            FermaxAuthError: If not authenticated
        """
        if self._token_data is None:
            raise FermaxAuthError("Not authenticated")

        return {
            "Authorization": f"{self._token_data.token_type} {self._token_data.access_token}"
        }
