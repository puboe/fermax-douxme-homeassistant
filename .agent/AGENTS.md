# Fermax DuoxMe Home Assistant Integration - Agent Guide

> **For AI Agents working on this codebase**  
> **Last Updated**: January 2026

---

## Quick Overview

This is a **Home Assistant custom integration** for Fermax DuoxMe video door intercoms. It enables door control, device monitoring, and camera support through the Fermax cloud API.

| Aspect | Details |
|--------|---------|
| **Language** | Python 3.x (async) |
| **Framework** | Home Assistant Custom Component |
| **Distribution** | HACS (Home Assistant Community Store) |
| **API Type** | REST with OAuth2 + JWT |
| **IoT Class** | Cloud Polling (30s default) |

---

## Project Structure

```
fermax-douxme-homeassistant/
├── custom_components/fermax_duoxme/   # Main integration code
│   ├── __init__.py           # Integration setup, entry points
│   ├── manifest.json         # HACS/HA manifest
│   ├── config_flow.py        # Config & options UI flow
│   ├── const.py              # Constants (domain, keys, defaults)
│   ├── coordinator.py        # DataUpdateCoordinator (polling)
│   ├── api/                   # API client layer
│   │   ├── __init__.py
│   │   ├── client.py         # FermaxApiClient class
│   │   ├── auth.py           # OAuth2 token handling
│   │   └── models.py         # Data models (Pairing, Device, etc.)
│   ├── lock.py               # Lock platform (door control)
│   ├── binary_sensor.py      # Binary sensor (device status)
│   ├── sensor.py             # Sensors (signal strength)
│   ├── camera.py             # Camera platform (PhotoCaller)
│   ├── strings.json          # Base translations
│   ├── translations/         # Locale files (en, es, it, pt, de)
│   └── docs/                  # API and requirements docs
├── tests/                     # Pytest test suite
├── README.md                  # User-facing documentation
├── hacs.json                  # HACS repository config
└── pytest.ini                 # Test configuration
```

---

## Development Commands

```bash
# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install pytest pytest-asyncio pytest-homeassistant-custom-component aiohttp PyTurboJPEG

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=custom_components/fermax_duoxme --cov-report=term-missing

# Run specific test
pytest tests/test_models.py -v
```

---

## Key Concepts

### Entity Types Created

| Entity | ID Format | Purpose |
|--------|-----------|---------|
| **Lock** | `lock.fermax_{tag}_{door}` | Door control (unlock only) |
| **Binary Sensor** | `binary_sensor.fermax_{tag}_status` | Device connectivity |
| **Sensor** | `sensor.fermax_{tag}_signal_strength` | WiFi signal (0-100%) |
| **Camera** | `camera.fermax_{tag}` | PhotoCaller images |

> `{tag}` = user-defined device name from Fermax app (e.g., "Front Door")

### Door Types
- **ZERO** (F1) - Primary door relay
- **ONE** (F2) - Secondary door relay  
- **GENERAL** - Building main entrance

### Visibility Logic
Locks are only created for doors with `visible: true` in the API. Non-visible doors are created but disabled by default in the entity registry.

---

## API Reference Summary

### Base URL
```
https://pro-duoxme.fermax.io
```

### Authentication
OAuth2 with JWT Bearer tokens.

```
Token Endpoint: https://oauth-pro-duoxme.fermax.io/oauth/token
Client ID: dpv7iqz6ee5mazm1iq9dw1d42slyut48kj0mp5fvo58j5ih
Client Secret: c7ylkqpujwah85yhnprv0wdvyzutlcnkw4sz90buldbulk1
```

### Key Endpoints

| Purpose | Method | Path |
|---------|--------|------|
| Login | POST | `/oauth/token` (grant_type=password) |
| Refresh Token | POST | `/oauth/token` (grant_type=refresh_token) |
| User Profile | GET | `/user/api/v1/users/me` |
| Get Pairings | GET | `/pairing/api/v4/pairings/me` |
| Device Details | GET | `/deviceaction/api/v1/device/{deviceId}` |
| Device Panels | GET | `/deviceaction/api/v1/device/{deviceId}/panels` |
| **Open Door** | POST | `/deviceaction/api/v1/device/{deviceId}/directed-opendoor?unitId={deviceId}` |
| Device Services | GET | `/services2/api/v1/services/{deviceId}?deviceType=wifi` |

### Open Door Request Body
```json
{
  "block": 0,
  "subblock": -1,
  "number": 0
}
```

### Required Headers
```http
Authorization: Bearer <jwt_token>
app-version: 4.2.5
app-build: 2
Content-Type: application/json
User-Agent: Blue/4.2.5 (com.fermax.bluefermax; build:2; HomeAssistant) Python-aiohttp
```

---

## Architecture Patterns

### DataUpdateCoordinator
The integration uses Home Assistant's `DataUpdateCoordinator` pattern:
- Single coordinator per config entry
- Polls API every 30 seconds (configurable)
- All entities subscribe to coordinator updates
- Handles token refresh transparently

### Unique IDs
- **Config Entry**: Based on user ID from API
- **Devices**: `{device_id}` from pairing
- **Entities**: `{device_id}_{entity_type}` or `{device_id}_{door_key}`

### Token Storage
Tokens are stored in `entry.data`:
```python
{
    CONF_USERNAME: "user@example.com",
    CONF_PASSWORD: "***",  # Encrypted by HA
    "access_token": "...",
    "refresh_token": "...",
    "expires_at": timestamp
}
```

---

## Testing Patterns

### Fixtures (`tests/conftest.py`)
- `mock_api_client` - Mocked FermaxApiClient
- `mock_pairing_data` - Sample API response data
- `mock_config_entry` - Pre-configured MockConfigEntry

### Key Test Files
| File | Tests |
|------|-------|
| `test_auth.py` | OAuth2 token flow |
| `test_client.py` | API client methods |
| `test_config_flow.py` | Setup wizard UI |
| `test_coordinator.py` | Data polling logic |
| `test_lock.py` | Lock entity behavior |
| `test_lock_visibility.py` | Door visibility logic |
| `test_models.py` | Data model parsing |

### Mocking HA Dependencies
```python
# Mock the HTTP session
with patch.object(hass, "async_get_clientsession", return_value=mock_session):
    ...

# Mock async_setup_entry
with patch("custom_components.fermax_duoxme.async_setup_entry", return_value=True):
    ...
```

---

## Common Workflows

### Adding a New Entity Type

1. Create `{platform}.py` (e.g., `switch.py`)
2. Add platform to `PLATFORMS` in `const.py`
3. Create entity class extending `CoordinatorEntity`
4. Implement required properties (`unique_id`, `name`, etc.)
5. Add platform setup in `async_setup_entry`
6. Add translations to `strings.json` and `translations/`
7. Write tests in `tests/test_{platform}.py`

### Modifying API Client

1. Update method in `api/client.py`
2. Update models in `api/models.py` if response changes
3. Update coordinator if data structure changes
4. Run `pytest tests/test_client.py tests/test_models.py`

### Changing Config Options

1. Update `OPTIONS_SCHEMA` in `config_flow.py`
2. Handle new options in `coordinator.py`
3. Add translations for new option labels
4. Update tests in `test_config_flow.py`

---

## Important Constraints

### API Limitations
- **Polling**: No real-time push (30s delay)
- **No live video**: Only PhotoCaller still images
- **Token validity**: ~4 days access, ~5 years refresh

### HACS Requirements
- Must have `manifest.json` with proper `version` field
- Must have `hacs.json` in repo root
- Must follow [HACS guidelines](https://hacs.xyz/docs/publish/integration)

### Home Assistant Patterns
- Always use `async` methods
- Use `hass.async_add_executor_job()` for blocking I/O
- Entity state updates via coordinator
- Use `entity_registry_enabled_default` for disabled entities

---

## Debugging Tips

### Enable Debug Logging
```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.fermax_duoxme: debug
```


### Common Issues
| Issue | Cause | Fix |
|-------|-------|-----|
| "Invalid credentials" | Wrong email/password | Use same as DuoxMe app |
| "No devices found" | Device not paired | Pair in mobile app first |
| Entity shows "unavailable" | API timeout/error | Check coordinator logs |

---

## Phase 2 Features (Future)

These require FCM push notification support:
- Mute Notifications Switch
- Call History Sensors
- PhotoCaller with actual photos
- Real-time doorbell notifications
- Auto-On camera preview
- Live video streaming (WebRTC)

---

## Reference Documents

- [API_CONTRACTS.md](custom_components/fermax_duoxme/docs/API_CONTRACTS.md) - Full API documentation
- [HACS integration requirements.md](custom_components/fermax_duoxme/docs/HACS%20integration%20requirements.md) - Technical requirements
- [bluecon library](https://github.com/AfonsoFGarcia/bluecon) - Reference implementation
- [hass-bluecon](https://github.com/AfonsoFGarcia/hass-bluecon) - Similar HA integration

---

## Code Style

- Follow Home Assistant coding standards
- Use `async`/`await` for all I/O operations
- Type hints are encouraged
- Docstrings for public methods
- Keep entity classes focused and simple
