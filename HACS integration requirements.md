# Fermax DuoxMe Home Assistant Integration - Technical Requirements

> **Version**: 1.0.0-draft  
> **Last Updated**: January 10, 2026  
> **Status**: Planning

---

## 1. Overview

### 1.1 Purpose
A custom Home Assistant integration for Fermax DuoxMe/Blue video door intercoms, enabling door control, device monitoring, call history, and PhotoCaller camera support.

### 1.2 Approach
**Build from scratch** using the `bluecon` library as a reference for:
- API structure and authentication patterns
- FCM push notification handling (future phase)

> [!NOTE]
> The `bluecon` library hasn't been updated in 2+ years and is likely non-functional. We will implement our own API client based on the documented API contracts.

### 1.3 Scope

| Feature | Phase 1 (MVP) | Phase 2 (Future) |
|---------|:-------------:|:----------------:|
| OAuth2 Authentication | ✅ | - |
| Token Refresh | ✅ | - |
| Door Control (Lock entities) | ✅ | - |
| Device Online/Offline | ✅ | - |
| Wireless Signal Sensor | ✅ | - |
| Multi-Device Support | ✅ | - |
| Config Flow + Options | ✅ | - |
| PhotoCaller Camera (entity ready) | ✅ | - |
| Mute Notifications Switch | ❌ | ✅ |
| Call History Sensors | ❌ | ✅ |
| Call History Logbook Events | ❌ | ✅ |
| PhotoCaller (with photos) | ❌ | ✅ |
| FCM Real-time Notifications | ❌ | ✅ |
| Auto-On (Camera Preview) | ❌ | ✅ |
| Subscription Plan Info | ❌ | ✅ |
| Live Video Streaming | ❌ | ✅ |

> [!NOTE]
> Call history, mute switch, and PhotoCaller photos require FCM token registration. These will be implemented in Phase 2 along with real-time notifications.

---

## 2. Architecture

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Home Assistant Integration Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │  Config Flow     │────▶│  OAuth2 Client   │                 │
│  │  (credentials)   │     │  (token mgmt)    │                 │
│  └──────────────────┘     └────────┬─────────┘                 │
│                                    │                            │
│  ┌──────────────────┐              │                            │
│  │  Options Flow    │              │                            │
│  │  (polling, etc)  │              │                            │
│  └──────────────────┘              │                            │
│                                    ▼                            │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │  Data Coordinator│◀───▶│  Fermax API      │                 │
│  │  (polling)       │     │  Client          │                 │
│  └────────┬─────────┘     └──────────────────┘                 │
│           │                                                     │
│           ▼                                                     │
│  ┌────────────────────────────────────────────┐                │
│  │  Entities                                   │                │
│  │  • Lock (per door: F1, F2, GENERAL, etc)   │                │
│  │  • Binary Sensor (device online/offline)   │                │
│  │  • Sensor (wireless signal, call count)    │                │
│  │  • Switch (mute notifications)             │                │
│  │  • Camera (PhotoCaller still images)       │                │
│  └────────────────────────────────────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  POLLING MODE (Phase 1)                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Every [configurable] seconds (default: 30):                    │
│                                                                 │
│  Coordinator ──▶ GET /deviceaction/api/v1/device/{id}          │
│              ──▶ GET /callManager/api/v1/callregistry/...       │
│              ──▶ GET /notification/api/v1/mutedevice/me         │
│                                                                 │
│  Updates: device status, signal, call history, mute state       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Functional Requirements

### 3.1 Authentication

| ID | Requirement | Priority |
|----|-------------|----------|
| AUTH-01 | OAuth2 password grant flow via `/oauth/token` | Must |
| AUTH-02 | Secure storage of refresh token in HA config entry | Must |
| AUTH-03 | Automatic token refresh before expiry (~4 days) | Must |
| AUTH-04 | Handle 401 responses by refreshing token | Must |
| AUTH-05 | Re-authenticate if refresh token fails | Must |

### 3.2 Device Discovery

| ID | Requirement | Priority |
|----|-------------|----------|
| DEV-01 | Fetch all pairings via `/pairing/api/v4/pairings/me` | Must |
| DEV-02 | Support multiple paired devices per account | Must |
| DEV-03 | Fetch device details for each pairing | Must |
| DEV-04 | Fetch panels associated with each device | Must |
| DEV-05 | Allow user to include/exclude specific devices | Should |

### 3.3 Lock Entities (Door Control)

| ID | Requirement | Priority |
|----|-------------|----------|
| LOCK-01 | Create lock entity for each visible door in `panelAccessDoors` | Must |
| LOCK-02 | Create lock entity for each visible door in `accessDoorMap` (F1, F2, GENERAL) | Must |
| LOCK-03 | `unlock` action calls `/directed-opendoor` with correct `block/subblock/number` | Must |
| LOCK-04 | Lock state always shows "locked" (no feedback from API) | Must |
| LOCK-05 | Momentary unlock behavior (auto-relock after ~3 seconds) | Should |

### 3.4 Binary Sensor (Device Status)

| ID | Requirement | Priority |
|----|-------------|----------|
| BIN-01 | Create binary sensor for device connectivity | Must |
| BIN-02 | State based on `connectionState` field ("Connected" = on) | Must |
| BIN-03 | Device class: `connectivity` | Must |

### 3.5 Sensor Entities

| ID | Requirement | Priority |
|----|-------------|----------|
| SENS-01 | Wireless signal strength sensor (0-100 scale from `wirelessSignal`) | Must |
| SENS-02 | Last call timestamp sensor | Must |
| SENS-03 | Missed calls count sensor | Must |
| SENS-04 | Total calls count sensor | Should |

### 3.6 Switch Entity (Mute Notifications)

| ID | Requirement | Priority |
|----|-------------|----------|
| SW-01 | Switch to toggle notification muting | Must |
| SW-02 | Read state from `/mutedevice/me` (returns boolean) | Must |
| SW-03 | Toggle via appropriate API endpoint | Must |

### 3.7 Camera Entity (PhotoCaller)

| ID | Requirement | Priority |
|----|-------------|----------|
| CAM-01 | Create camera entity if `photocaller: true` on device | Must |
| CAM-02 | Display last captured still image from doorbell ring | Must |
| CAM-03 | Refresh image when new call with `photoId` is detected | Must |
| CAM-04 | Fetch photo via PhotoCaller API using `photoId` from call registry | Must |
| CAM-05 | Store photo locally for offline viewing | Should |

### 3.8 Call History & Photos

| ID | Requirement | Priority |
|----|-------------|----------|
| LOG-01 | Fire HA events for new calls detected in poll | Must |
| LOG-02 | Event type: `fermax_call` with call details | Must |
| LOG-03 | Include: `callDate`, `registerCall`, `isAutoon`, `deviceId`, `photoId` | Must |
| LOG-04 | HA Logbook shows call history entries | Must |
| LOG-05 | If `photoId` is not null, fetch and attach photo to event | Must |
| LOG-06 | Create media source for browsing call photos | Should |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement | Priority |
|----|-------------|----------|
| PERF-01 | Default polling interval: 30 seconds | Must |
| PERF-02 | Configurable polling interval: 15-300 seconds | Should |
| PERF-03 | Batch API calls per device to minimize requests | Should |
| PERF-04 | Respect FREE tier rate limits (4 door opens/day) | Must |

### 4.2 Reliability

| ID | Requirement | Priority |
|----|-------------|----------|
| REL-01 | Graceful handling of API timeout/errors | Must |
| REL-02 | Exponential backoff on repeated failures | Should |
| REL-03 | Entity availability reflects API reachability | Must |

### 4.3 Security

| ID | Requirement | Priority |
|----|-------------|----------|
| SEC-01 | Credentials stored securely in HA config entry | Must |
| SEC-02 | No logging of tokens or passwords | Must |
| SEC-03 | HTTPS only for all API calls | Must |

---

## 5. Configuration

### 5.1 Config Flow (Initial Setup)

**Step 1: Credentials**
```yaml
username: user@example.com  # Email
password: ********          # Password
```

**Step 2: Device Selection** (if multiple pairings)
```yaml
devices:
  - deviceId: "00009208516a2dac001d00c3"
    name: "Front Door"
    enabled: true
  - deviceId: "00009208516a2dac001d00c4"
    name: "Back Gate"
    enabled: false
```

### 5.2 Options Flow (Post-Setup)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `polling_interval` | int | 30 | Seconds between API polls |
| `enabled_devices` | list | all | Which devices to monitor |
| `create_door_entities` | bool | true | Create lock entities for each door |

---

## 6. Entity Naming Convention

| Entity Type | Entity ID Format | Friendly Name |
|-------------|------------------|---------------|
| Lock | `lock.fermax_{device_tag}_{door_name}` | `{Tag} {Door Name}` |
| Binary Sensor | `binary_sensor.fermax_{device_tag}_status` | `{Tag} Status` |
| Sensor (Signal) | `sensor.fermax_{device_tag}_signal` | `{Tag} Signal` |
| Sensor (Calls) | `sensor.fermax_{device_tag}_missed_calls` | `{Tag} Missed Calls` |
| Switch (Mute) | `switch.fermax_{device_tag}_mute` | `{Tag} Mute` |
| Camera | `camera.fermax_{device_tag}` | `{Tag} Camera` |

> `{device_tag}` is the user-defined name from the pairing (e.g., "Sardenya", "Front Door")

---

## 7. API Client Design

### 7.1 Class Structure

```python
class FermaxApiClient:
    """Handles all Fermax API communication."""
    
    async def authenticate(username, password) -> TokenData
    async def refresh_token(refresh_token) -> TokenData
    async def get_user() -> UserProfile
    async def get_pairings() -> list[Pairing]
    async def get_device(device_id) -> DeviceInfo
    async def get_panels(device_id) -> list[Panel]
    async def get_services(device_id) -> list[str]
    async def open_door(device_id, door_id: DoorId) -> bool
    async def get_call_history(token, type) -> list[CallRecord]
    async def get_mute_status(device_id, token) -> bool
    async def set_mute_status(device_id, token, muted) -> bool
    async def get_photo_by_id(photo_id) -> bytes | None  # Call record photo
    async def get_last_photo(device_id) -> bytes | None  # Most recent photo
```

> [!TIP]
> **PhotoCaller endpoint discovered from bluecon library:**
> ```
> GET /callManager/api/v1/photocall?photoId={photoId}
> ```
> Response: `{ "image": { "data": "<base64_encoded_jpeg>" } }`

### 7.2 Data Models

```python
@dataclass
class DoorId:
    block: int
    subblock: int
    number: int

@dataclass
class TokenData:
    access_token: str
    refresh_token: str
    expires_at: datetime

@dataclass
class Pairing:
    id: str
    device_id: str
    tag: str
    address: str
    access_door_map: dict[str, DoorConfig]
    panel_access_doors: list[PanelDoor]
```

---

## 8. Future Enhancements (Phase 2+)

### 8.1 FCM Real-time Notifications

```
┌─────────────────────────────────────────────────────────────────┐
│  FCM + POLLING HYBRID (Phase 2)                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Fermax Cloud ──FCM Push──▶ push_receiver ──▶ HA Event         │
│                              (local listener)     │             │
│                                                   ▼             │
│                                          "doorbell_ring"        │
│                                          "call_ended"           │
│                                                                 │
│  Benefits:                                                      │
│  • Instant doorbell notifications                               │
│  • Less frequent API polling needed                             │
│  • Better user experience                                       │
│                                                                 │
│  Implementation:                                                │
│  • Use push_receiver library for FCM                            │
│  • Register FCM token via /apptoken endpoint                    │
│  • Fire HA events on incoming push notifications                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Auto-On (Camera Preview)

- Trigger camera preview without doorbell ring
- Requires FCM token for receiving video stream data
- Would need WebRTC implementation for live video

### 8.3 Subscription Plan Info

- Display current plan (FREE/UNLIMITED)
- Show remaining door opens for FREE tier
- Sensor entity with plan details

---

## 9. File Structure

```
custom_components/fermax_duoxme/
├── __init__.py           # Integration setup
├── manifest.json         # HACS manifest
├── config_flow.py        # Config & options flow
├── const.py              # Constants
├── coordinator.py        # Data update coordinator
├── api/
│   ├── __init__.py
│   ├── client.py         # API client
│   ├── auth.py           # OAuth2 handling
│   └── models.py         # Data models
├── lock.py               # Lock platform
├── binary_sensor.py      # Binary sensor platform
├── sensor.py             # Sensor platform
├── switch.py             # Switch platform
├── camera.py             # Camera platform
├── strings.json          # Translations
└── translations/
    ├── en.json
    └── es.json
```

---

## 10. Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `aiohttp` | ≥3.13.3 | Async HTTP client |
| `PyJWT` | ≥2.10.1 | JWT token decoding (optional) |

---

## 11. Testing Requirements

| Test Type | Coverage |
|-----------|----------|
| Unit Tests | API client, data models, token refresh |
| Integration Tests | Config flow, coordinator updates |
| Mock API | Fixtures with sample API responses |

---

## 12. Documentation

- [ ] README.md with installation instructions
- [ ] HACS repository setup (hacs.json)
- [ ] Configuration examples
- [ ] Troubleshooting guide
- [ ] API rate limit warnings (FREE tier)

---

## 13. References

- [API Contracts](./API_CONTRACTS.md) - Full API documentation
- [bluecon library](https://github.com/AfonsoFGarcia/bluecon) - Reference implementation
- [hass-bluecon](https://github.com/AfonsoFGarcia/hass-bluecon) - Existing HA integration (reference)
