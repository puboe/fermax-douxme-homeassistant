"""Tests for authentication."""

import pytest
from datetime import datetime, timedelta

from custom_components.fermax_duoxme.api.auth import (
    TokenData,
    FermaxAuthError,
    InvalidCredentialsError,
    TokenRefreshError,
)


class TestTokenData:
    """Tests for TokenData class."""

    def test_from_dict(self):
        """Test creating TokenData from OAuth response."""
        data = {
            "access_token": "access123",
            "refresh_token": "refresh456",
            "token_type": "Bearer",
            "expires_in": 345600,
        }
        token = TokenData.from_dict(data)

        assert token.access_token == "access123"
        assert token.refresh_token == "refresh456"
        assert token.token_type == "Bearer"
        assert token.expires_in == 345600

    def test_is_expired_false(self):
        """Test token is not expired when created."""
        token = TokenData(
            access_token="test",
            refresh_token="test",
            token_type="Bearer",
            expires_in=345600,
            created_at=datetime.now(),
        )
        assert token.is_expired is False

    def test_is_expired_true(self):
        """Test token is expired after expiry time."""
        token = TokenData(
            access_token="test",
            refresh_token="test",
            token_type="Bearer",
            expires_in=0,  # Already expired
            created_at=datetime.now() - timedelta(seconds=1),
        )
        assert token.is_expired is True

    def test_expires_at(self):
        """Test expires_at calculation."""
        now = datetime.now()
        token = TokenData(
            access_token="test",
            refresh_token="test",
            token_type="Bearer",
            expires_in=3600,
            created_at=now,
        )
        expected = now + timedelta(seconds=3600)
        # Allow 1 second tolerance
        assert abs((token.expires_at - expected).total_seconds()) < 1

    def test_to_dict_and_from_stored_dict(self):
        """Test round-trip serialization."""
        original = TokenData(
            access_token="access123",
            refresh_token="refresh456",
            token_type="Bearer",
            expires_in=3600,
            created_at=datetime.now(),
        )

        stored = original.to_dict()
        restored = TokenData.from_stored_dict(stored)

        assert restored.access_token == original.access_token
        assert restored.refresh_token == original.refresh_token
        assert restored.token_type == original.token_type
        assert restored.expires_in == original.expires_in


class TestFermaxAuthExceptions:
    """Tests for auth exception classes."""

    def test_fermax_auth_error(self):
        """Test FermaxAuthError is catchable."""
        with pytest.raises(FermaxAuthError):
            raise FermaxAuthError("Test error")

    def test_invalid_credentials_error_inherits(self):
        """Test InvalidCredentialsError is a FermaxAuthError."""
        with pytest.raises(FermaxAuthError):
            raise InvalidCredentialsError("Invalid")

    def test_token_refresh_error_inherits(self):
        """Test TokenRefreshError is a FermaxAuthError."""
        with pytest.raises(FermaxAuthError):
            raise TokenRefreshError("Refresh failed")
