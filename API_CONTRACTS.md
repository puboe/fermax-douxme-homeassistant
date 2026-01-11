# Fermax DuoxMe API Contracts

> **Document Version**: 1.0  
> **Last Updated**: January 10, 2026  
> **Purpose**: API reference for building a Home Assistant HACS integration

This document describes the API contracts for the Fermax DuoxMe intercom system, derived from network analysis of the official mobile application.

---

## Overview

### Base URL
```
https://pro-duoxme.fermax.io
```

### Architecture
The API is organized into multiple microservices:

| Service | Base Path | Purpose |
|---------|-----------|---------|
| **User** | `/user/api/v1` | User account management |
| **Pairing** | `/pairing/api/v4` | Device pairing/registration |
| **Device Action** | `/deviceaction/api/v1` & `/api/v2` | Device control (door open, auto-on) |
| **Services** | `/services2/api/v1` | Service capabilities per device |
| **Notification** | `/notification/api/v1` | Push notification management |
| **Call Manager** | `/callManager/api/v1` | Call registry and history |
| **Subscription** | `/subscriptionnowifi/api/v1` | Subscription plans |

### Authentication

The API uses **OAuth2 with JWT Bearer tokens**.

#### OAuth2 Configuration
| Property | Value |
|----------|-------|
| **Issuer** | `https://oauth-pro-duoxme.fermax.io` |
| **Token Type** | JWT (HS256) |
| **Token Lifetime** | ~4 days (345,600 seconds) |
| **Client ID** | `clientId` |

#### JWT Token Structure

```json
{
  "sub": "user_email@example.com",
  "aud": ["<client_id>", "restservice"],
  "nbf": 1768066106,
  "sub_type": "user",
  "user_name": "<base32_encoded_user_identifier>",
  "sub_id": "userId",
  "iss": "https://oauth-pro-duoxme.fermax.io",
  "exp": 1768411706,
  "iat": 1768066106,
  "jti": "jtiId",
  "client_id": "clientId",
  "authorities": ["ROLE_USER"]
}
```

> [!IMPORTANT]
> The `sub_id` field contains the **UUID of the user**. This may be needed for certain API calls.

#### OAuth2 Token Endpoint

```http
POST https://oauth-pro-duoxme.fermax.io/oauth/token
```

##### Authentication
Uses **HTTP Basic Auth** with client credentials:
```
Authorization: Basic base64(clientId:clientSecret)
```

| Credential | Description |
|------------|-------------|
| **Client ID** | `dpv7iqz6ee5mazm1iq9dw1d42slyut48kj0mp5fvo58j5ih` |
| **Client Secret** | `c7ylkqpujwah85yhnprv0wdvyzutlcnkw4sz90buldbulk1` |

> [!CAUTION]
> These are static credentials embedded in the mobile app. They are NOT user-specific and should be treated as public knowledge. The security is in the user's password.

##### Request Headers
```http
Host: oauth-pro-duoxme.fermax.io
Authorization: Basic ZHB2N2lxejZlZTVtYXptMWlxOWR3MWQ0MnNseXV0NDhrajBtcDVmdm81OGo1aWg6Yzd5bGtxcHVqd2FoODV5aG5wcnYwd2R2eXp1dGxjbmt3NHN6OTBidWxkYnVsazE=
Content-Type: application/x-www-form-urlencoded; charset=utf-8
app-version: 4.2.5
app-build: 2
User-Agent: Blue/4.2.5 (com.fermax.bluefermax; build:2; iOS 26.2.0) Alamofire/5.10.2
```

##### Password Grant (Login)
Used for initial authentication with username/password:

```http
POST /oauth/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=password&username=user%40example.com&password=yourpassword
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `grant_type` | string | Yes | Must be `password` |
| `username` | string | Yes | User's email (URL encoded) |
| `password` | string | Yes | User's password |

##### Refresh Token Grant
Used to obtain a new access token without re-entering credentials:

```http
POST /oauth/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&refresh_token=<refresh_token>
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `grant_type` | string | Yes | Must be `refresh_token` |
| `refresh_token` | string | Yes | The refresh token from a previous auth |

##### Response Schema (Actual)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "scope": "legacy",
  "token_type": "Bearer",
  "expires_in": 345599,
  "jti": "deprecated"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `access_token` | string | JWT token for API calls (~4 days validity) |
| `refresh_token` | string | Token to refresh access (~5 years validity!) |
| `scope` | string | OAuth scope (always `legacy`) |
| `token_type` | string | Always `Bearer` |
| `expires_in` | integer | Access token lifetime in seconds |
| `jti` | string | JWT ID (marked as `deprecated`) |

> [!TIP]
> The **refresh token has a very long validity (~5 years)**. For a Home Assistant integration, store the refresh token securely and use it to obtain new access tokens when they expire.

##### Token Lifetimes
| Token | Lifetime | Notes |
|-------|----------|-------|
| Access Token | ~4 days (345,600 sec) | Used for API calls |
| Refresh Token | ~5 years | Store securely for re-authentication |

##### cURL Example
```bash
curl -X POST 'https://oauth-pro-duoxme.fermax.io/oauth/token' \
  -H 'Authorization: Basic ZHB2N2lxejZlZTVtYXptMWlxOWR3MWQ0MnNseXV0NDhrajBtcDVmdm81OGo1aWg6Yzd5bGtxcHVqd2FoODV5aG5wcnYwd2R2eXp1dGxjbmt3NHN6OTBidWxkYnVsazE=' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -d 'grant_type=password&username=user%40example.com&password=yourpassword'
```

### Required Headers

All API requests must include these headers:

```http
Host: pro-duoxme.fermax.io
Authorization: Bearer <jwt_access_token>
Content-Type: application/json
Accept: */*
app-version: 4.2.5
app-build: 2
phone-os: 26.2
phone-model: iPad Pro (12.9-inch) (3rd generation)
User-Agent: Blue/4.2.5 (com.fermax.bluefermax; build:2; iOS 26.2.0) Alamofire/5.10.2
Accept-Language: es-ES;q=1.0, en-ES;q=0.9
Accept-Encoding: br;q=1.0, gzip;q=0.9, deflate;q=0.8
Connection: keep-alive
Pragma: no-cache
Cache-Control: no-cache
```

#### Header Descriptions

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | **Yes** | Bearer JWT token from OAuth2 |
| `app-version` | **Yes** | App version string (e.g., `4.2.5`) |
| `app-build` | **Yes** | App build number (e.g., `2`) |
| `phone-os` | Likely | iOS/Android version |
| `phone-model` | Likely | Device model name |
| `User-Agent` | **Yes** | Full user agent string including app name and Alamofire version |
| `traceparent` | No | OpenTelemetry W3C trace context (optional) |
| `Content-Type` | **Yes** | `application/json` for POST/PUT requests |

> [!TIP]
> For a Home Assistant integration, you can likely simplify the headers. The minimum required headers appear to be: `Authorization`, `app-version`, `app-build`, `User-Agent`, and `Content-Type`.

#### User-Agent Format
```
Blue/<version> (com.fermax.bluefermax; build:<build_number>; <OS> <os_version>) Alamofire/<alamofire_version>
```

**Example for Home Assistant:**
```
Blue/4.2.5 (com.fermax.bluefermax; build:2; HomeAssistant) Python-HTTPX/0.27.0
```

### Device Identifier Format
Device IDs follow a specific format:
```
00009208516a2dac001d00c3
```
This appears to be a unique hardware identifier (24 hex characters).

---

## API Endpoints

---

## 1. User Service

### 1.1 Get Current User

Retrieves the authenticated user's profile information.

```http
GET /user/api/v1/users/me
```

#### Request
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| - | - | - | No parameters required |

#### Response
| Field | Type | Description |
|-------|------|-------------|
| `Content-Type` | Header | `application/json` |
| Response Size | - | ~396 bytes |

#### Example Request
```http
GET /user/api/v1/users/me HTTP/1.1
Host: pro-duoxme.fermax.io
Authorization: Bearer <token>
```

#### cURL
```bash
curl 'https://pro-duoxme.fermax.io/user/api/v1/users/me' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -H 'Content-Type: application/json'
```

#### Success Response
- **Status Code**: `200 OK`

#### Response Schema (Actual)
```json
{
  "id": "userId",
  "email": "user@example.com",
  "locale": "es",
  "acceptSharing": false,
  "acceptPrivacy": true,
  "enabled": true,
  "createdAt": "2024-04-09T15:09:20.444+00:00",
  "country": null,
  "city": null,
  "area": null,
  "zone": null,
  "subzone": null,
  "pin": null,
  "pinDate": null,
  "uniqueSession": false,
  "provider": "DUOXME",
  "origin": "DUOXME",
  "name": null,
  "activePremiumSubscription": false
}
```

---

## 2. Pairing Service

### 2.1 Get User's Pairings

Retrieves all devices paired/linked to the current user's account.

```http
GET /pairing/api/v4/pairings/me
```

#### Request
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| - | - | - | No parameters required |

#### Response
| Field | Type | Description |
|-------|------|-------------|
| `Content-Type` | Header | `application/json` |
| Response Size | - | ~1140 bytes |

#### Example Request
```http
GET /pairing/api/v4/pairings/me HTTP/1.1
Host: pro-duoxme.fermax.io
Authorization: Bearer <token>
```

#### cURL
```bash
curl 'https://pro-duoxme.fermax.io/pairing/api/v4/pairings/me' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -H 'Content-Type: application/json'
```

#### Success Response
- **Status Code**: `200 OK`

#### Response Schema (Actual)
Returns an **array** of pairing objects (not wrapped in a `pairings` key):

```json
[
  {
    "id": "pairingId",
    "deviceId": "deviceId",
    "userId": "userId",
    "userEmail": "user@example.com",
    "tag": "Example",
    "logicalId": "logicalId",
    "installationId": "installationId",
    "numBlock": 0,
    "numSubblock": 0,
    "numUnit": 22,
    "status": "PAIRED",
    "isMaster": true,
    "enabled": true,
    "isDisabled": false,
    "createdAt": 1752664379689,
    "updatedAt": 1752664397869,
    "appBuild": 6,
    "appVersion": "4.2.0",
    "phoneModel": "iPhone17,1",
    "phoneOS": "18.5",
    "home": null,
    "address": "Your address",
    "type": "WIFI",
    "accessDoorMap": {
      "ZERO": {
        "title": "",
        "accessId": { "block": 200, "subblock": -1, "number": 0 },
        "visible": true
      },
      "ONE": {
        "title": "",
        "accessId": { "block": 200, "subblock": -1, "number": 1 },
        "visible": false
      },
      "GENERAL": {
        "title": "",
        "accessId": { "block": 100, "subblock": -1, "number": 0 },
        "visible": false
      }
    },
    "panelAccessDoors": [
      {
        "deviceId": "deviceId",
        "title": "",
        "isVisible": true,
        "doorId": { "block": 0, "subblock": -1, "number": 0 }
      }
    ],
    "guest": false,
    "master": true,
    "simpleLogicalId": "000022",
    "updating": false,
    "subscriptionNoWifi": null
  }
]
```

> [!NOTE]
> This endpoint returns all paired devices for the user. Use the `deviceId` from this response for subsequent device-specific API calls.

---

## 3. Device Action Service

The Device Action service is the core service for controlling the intercom hardware.

### 3.1 Get Device Details

Retrieves detailed information about a specific device.

```http
GET /deviceaction/api/v1/device/{deviceId}
```

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceId` | string | Yes | The unique device identifier |

#### Response
| Field | Type | Description |
|-------|------|-------------|
| `Content-Type` | Header | `application/json` |
| Response Size | - | ~575 bytes |

#### Example Request
```http
GET /deviceaction/api/v1/device/00009208516a2dac001d00c3 HTTP/1.1
Host: pro-duoxme.fermax.io
Authorization: Bearer <token>
```

#### cURL
```bash
curl 'https://pro-duoxme.fermax.io/deviceaction/api/v1/device/<DEVICE_ID>' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -H 'Content-Type: application/json'
```

#### Success Response
- **Status Code**: `200 OK`

#### Response Schema (Actual)
```json
{
  "deviceId": "00009208516a2dac001d00c3",
  "connectionState": "Connected",
  "status": "ACTIVATED",
  "installationId": "inst_example123456789",
  "family": "MONITOR",
  "type": "VEO",
  "subtype": "WIFI",
  "numBlock": 0,
  "numSubblock": 0,
  "unitNumber": 22,
  "connectable": true,
  "iccid": "",
  "divertService": "blueStream",
  "photocaller": true,
  "photocallerInstaller": null,
  "wirelessSignal": 4,
  "isTerminal": true,
  "streamingMode": "video_call",
  "isPanel": false,
  "isPanelOrEdibox": false,
  "isMonitorOrGuardUnit": true,
  "isBlueStream": true,
  "isPhone": false,
  "isMonitor": true,
  "isHighEndDevice": false,
  "isSimphonyDevice": false
}
```

---

### 3.2 Get Device Panels

Retrieves information about all panels/doors associated with a device.

```http
GET /deviceaction/api/v1/device/{deviceId}/panels
```

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceId` | string | Yes | The unique device identifier |

#### Response
| Field | Type | Description |
|-------|------|-------------|
| `Content-Type` | Header | `application/json` |
| Response Size | - | ~745 bytes |

#### Example Request
```http
GET /deviceaction/api/v1/device/00009208516a2dac001d00c3/panels HTTP/1.1
Host: pro-duoxme.fermax.io
Authorization: Bearer <token>
```

#### cURL
```bash
curl 'https://pro-duoxme.fermax.io/deviceaction/api/v1/device/<DEVICE_ID>/panels' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -H 'Content-Type: application/json'
```

#### Success Response
- **Status Code**: `200 OK`

#### Response Schema (Actual)
Returns an **array** of panel objects:

```json
[
  {
    "serialNumber": "1234567890abcdef12345678",
    "ol": "OL  XXXXXXXXXXXXX",
    "manufacturingDate": "2025-04-17T09:20:47.367Z",
    "deployed": true,
    "status": true,
    "installationId": "inst_example123456789",
    "family": "PANEL",
    "type": "CORA",
    "subtype": "4G",
    "versionHW": "01",
    "versionSW": null,
    "build": "8",
    "ipAdress": null,
    "latitude": 40.00000000000000,
    "longitude": 0.000000000000000,
    "accuracy": 0,
    "continent": "Europe",
    "city": "Barcelona",
    "countryIso2": null,
    "countryGPRS": "ES",
    "numBlock": 0,
    "numSubblock": -1,
    "unitNumber": 0,
    "iccid": "00000000000000000000",
    "connectable": true,
    "name": "",
    "divertService": "blueStream",
    "photocaller": false,
    "photocallerInstaller": null,
    "wirelessSignal": 42,
    "isConnectableMonitor": false,
    "simpleLogicalId": "00-100",
    "isPanel": true,
    "isMonitor": false
  }
]
```

> [!IMPORTANT]
> The panels endpoint is called frequently by the mobile app. This suggests it's used to refresh the UI state and check panel availability.

---

### 3.3 Open Door (Directed)

Opens a specific door. This is the primary action for remote door unlocking.

```http
POST /deviceaction/api/v1/device/{deviceId}/directed-opendoor?unitId={unitId}
```

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceId` | string | Yes | The unique device identifier |

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `unitId` | string | Yes | The unit/apartment identifier (often same as deviceId) |

#### Request Body
| Field | Type | Description |
|-------|------|-------------|
| Request Size | - | ~38 bytes |

#### Request Body Schema (Actual)
The request body specifies which door to open using the `doorId` object structure (same format as in `panelAccessDoors` from the pairings response):

```json
{
  "block": 0,
  "subblock": -1,
  "number": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `block` | integer | Block identifier (from `accessDoorMap` or `panelAccessDoors`) |
| `subblock` | integer | Subblock identifier (typically `-1`) |
| `number` | integer | Door number within the block |

> [!TIP]
> The `doorId` values can be obtained from the `panelAccessDoors` array in the pairings response, or from the `accessDoorMap` object.

#### Response
| Field | Type | Description |
|-------|------|-------------|
| `Content-Type` | Header | `text/plain;charset=UTF-8` |
| Response Size | - | 17 bytes |

#### Example Request
```http
POST /deviceaction/api/v1/device/{deviceId}/directed-opendoor?unitId={deviceId} HTTP/1.1
Host: pro-duoxme.fermax.io
Authorization: Bearer <token>
Content-Type: application/json

{
  "block": 0,
  "subblock": -1,
  "number": 0
}
```

#### cURL
```bash
curl -X POST 'https://pro-duoxme.fermax.io/deviceaction/api/v1/device/<DEVICE_ID>/directed-opendoor?unitId=<DEVICE_ID>' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -H 'Content-Type: application/json' \
  -d '{"block":0,"subblock":-1,"number":0}'
```

#### Success Response (Actual)
- **Status Code**: `200 OK`
- **Body**: `la puerta abierta` (Spanish for "the door is open")

> [!CAUTION]
> This endpoint physically unlocks the door. Implement proper authorization checks and rate limiting in your Home Assistant integration.

---

### 3.4 Auto-On (Camera/Video Preview)

Triggers the "Auto-On" feature which activates the video feed from a panel camera without a doorbell ring.

```http
POST /deviceaction/api/v2/device/{deviceId}/autoon
```

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceId` | string | Yes | The unique device identifier |

#### Request Body
| Field | Type | Description |
|-------|------|-------------|
| Request Size | - | ~207 bytes |

#### Request Body Schema (Actual)
```json
{
  "directedToBluestream": "<FCM_PUSH_TOKEN>",
  "deviceID": "<monitor_device_id>"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `directedToBluestream` | string | Firebase Cloud Messaging token for receiving the video stream notification |
| `deviceID` | string | The monitor/terminal device ID (same as in URL path) |

> [!IMPORTANT]
> The `directedToBluestream` field requires a valid FCM push token. For a Home Assistant integration, you would need to implement push notification receiving to get the video stream data.

#### Response
| Field | Type | Description |
|-------|------|-------------|
| `Content-Type` | Header | `application/json` |
| Response Size | - | ~498 bytes (success) / ~277 bytes (conflict) |

#### Example Request
```http
POST /deviceaction/api/v2/device/{deviceId}/autoon HTTP/1.1
Host: pro-duoxme.fermax.io
Authorization: Bearer <token>
Content-Type: application/json

{
  "directedToBluestream": "cSyPGh6-2kZQlIFS-EteGb:APA91bEfiE...",
  "deviceID": "00009208516a2dac001d00c3"
}
```

#### cURL
```bash
curl -X POST 'https://pro-duoxme.fermax.io/deviceaction/api/v2/device/<DEVICE_ID>/autoon' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -H 'Content-Type: application/json' \
  -d '{"directedToBluestream":"<FCM_TOKEN>","deviceID":"<DEVICE_ID>"}'
```

#### Success Response (Actual)
- **Status Code**: `200 OK`

```json
{
  "reason": "call_starting",
  "divertService": "blueStream",
  "code": 1.0,
  "additional_info": {
    "local": {
      "address": "00 00 22",
      "block": 0.0,
      "number": 22.0,
      "subblock": 0.0,
      "subtype": "monitor",
      "type": "terminal"
    },
    "remote": {
      "address": "00 F0 A0",
      "block": 0.0,
      "number": 0.0,
      "subblock": -1.0,
      "type": "panel"
    },
    "technology": "duox"
  },
  "description": "Auto on is starting",
  "directedTo": "<FCM_TOKEN>"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `reason` | string | Event type: `call_starting` |
| `divertService` | string | Streaming service: `blueStream` |
| `code` | number | Status code (1.0 = success) |
| `description` | string | Human-readable status |
| `additional_info.local` | object | Monitor/terminal device info |
| `additional_info.remote` | object | Panel/camera device info |
| `additional_info.technology` | string | Protocol: `duox` |
| `directedTo` | string | FCM token that will receive the stream |

> [!NOTE]
> The actual video stream is delivered via **push notification** to the FCM token, not in this HTTP response. The mobile app receives the stream data through Firebase Cloud Messaging and then initiates a WebRTC connection.

#### Error Responses

| Status Code | Description |
|-------------|-------------|
| `409 Conflict` | Another session is already active. Wait for it to complete or terminate it first. |

> [!WARNING]
> The `409 Conflict` error occurs when attempting to start a new auto-on session while another is in progress. The app typically waits a few seconds before retrying.

---

## 4. Services

### 4.1 Get Device Services

Retrieves the enabled services/features for a specific device.

```http
GET /services2/api/v1/services/{deviceId}?deviceType={deviceType}
```

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceId` | string | Yes | The unique device identifier |

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceType` | string | Yes | Device type (observed: `wifi`) |

#### Response
| Field | Type | Description |
|-------|------|-------------|
| `Content-Type` | Header | `application/json` |
| Response Size | - | ~244 bytes |

#### Example Request
```http
GET /services2/api/v1/services/00009208516a2dac001d00c3?deviceType=wifi HTTP/1.1
Host: pro-duoxme.fermax.io
Authorization: Bearer <token>
```

#### cURL
```bash
curl 'https://pro-duoxme.fermax.io/services2/api/v1/services/<DEVICE_ID>?deviceType=wifi' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -H 'Content-Type: application/json'
```

#### Success Response
- **Status Code**: `200 OK`

#### Response Schema (Actual)
Returns a **simple array of feature name strings**:

```json
[
  "AccessName",
  "AutoOn",
  "CallDivert",
  "CallRegistry",
  "ChangeVideoSource",
  "CheckInformation",
  "DND",
  "Doormatic",
  "EventRegistry",
  "F1",
  "F1Options",
  "Geo",
  "Guard",
  "Guest5",
  "ManageCallDivert",
  "OpenDoor",
  "Photocaller",
  "Ringtone",
  "SessionsUnlimited",
  "TZ"
]
```

#### Feature Descriptions
| Feature | Description |
|---------|-------------|
| `OpenDoor` | Remote door unlock capability |
| `AutoOn` | Camera preview without doorbell ring |
| `CallDivert` | Forward calls to mobile app |
| `CallRegistry` | Access to call history |
| `Photocaller` | Doorbell photo capture |
| `DND` | Do Not Disturb mode |
| `Doormatic` | Automatic door release |
| `Guest5` | Guest access (5 guests max) |
| `Guard` | Guard/concierge features |
| `Geo` | Geolocation features |
| `SessionsUnlimited` | Premium: unlimited video sessions |
```

---

## 5. Notification Service

### 5.1 Register App Token

Registers the device's push notification token (Firebase Cloud Messaging) with the backend.

```http
POST /notification/api/v1/apptoken
```

#### Request Body
| Field | Type | Description |
|-------|------|-------------|
| Request Size | - | ~402 bytes |

#### Request Body Schema (Actual)
```json
{
  "token": "cSyPGh6-2kZQlIFS-EteGb:APA91bEfiEk...",
  "apns": {
    "sandbox": false,
    "token": "545b242f54b5f567128d991f465fc91e..."
  },
  "os": "iOS",
  "osVersion": "26.2",
  "appVersion": "4.2.5",
  "appBuild": "2",
  "phoneMobile": "iPad Pro (12.9-inch) (3rd generation)",
  "locale": "es",
  "active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | Yes | Firebase Cloud Messaging token |
| `apns` | object | iOS only | Apple Push Notification Service config |
| `apns.sandbox` | boolean | - | Whether using APNS sandbox environment |
| `apns.token` | string | - | APNS device token (hex string) |
| `os` | string | Yes | Operating system: `iOS` or `ANDROID` |
| `osVersion` | string | Yes | OS version string |
| `appVersion` | string | Yes | App version (e.g., `4.2.5`) |
| `appBuild` | string | Yes | App build number |
| `phoneMobile` | string | Yes | Device model name |
| `locale` | string | Yes | User locale (e.g., `es`, `en`) |
| `active` | boolean | Yes | Whether to activate notifications |

#### Response
| Field | Type | Description |
|-------|------|-------------|
| `Content-Type` | Header | `text/plain;charset=UTF-8` |
| Response Size | - | 13 bytes |

#### Example Request
```http
POST /notification/api/v1/apptoken HTTP/1.1
Host: pro-duoxme.fermax.io
Authorization: Bearer <token>
Content-Type: application/json

{
  "token": "cSyPGh6-2kZQlIFS-EteGb:APA91bEfiEk...",
  "apns": {"sandbox": false, "token": "545b242f..."},
  "os": "iOS",
  "osVersion": "26.2",
  "appVersion": "4.2.5",
  "appBuild": "2",
  "phoneMobile": "iPad Pro",
  "locale": "es",
  "active": true
}
```

#### cURL
```bash
curl -X POST 'https://pro-duoxme.fermax.io/notification/api/v1/apptoken' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -H 'Content-Type: application/json' \
  -d '{"token":"<FCM_TOKEN>","os":"iOS","osVersion":"26.2","appVersion":"4.2.5","appBuild":"2","phoneMobile":"HomeAssistant","locale":"en","active":true}'
```

#### Success Response (Actual)
- **Status Code**: `200 OK`
- **Body**: `Token Updated`

> [!NOTE]
> For a Home Assistant integration, you would need to use `push_receiver` (like `bluecon` does) to receive FCM notifications, or implement your own FCM receiving mechanism.

---

### 5.2 Get Mute Device Status

Checks if push notifications are muted for a specific device.

```http
GET /notification/api/v1/mutedevice/me?deviceId={deviceId}&token={token}
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceId` | string | Yes | The intercom device ID |
| `token` | string | Yes | FCM push notification token (URL encoded) |

#### Response
| Field | Type | Description |
|-------|------|-------------|
| `Content-Type` | Header | `application/json` |
| Response Size | - | ~5 bytes |

#### Example Request
```http
GET /notification/api/v1/mutedevice/me?deviceId=00009208516a2dac001d00c3&token=cSyPGh6... HTTP/1.1
Host: pro-duoxme.fermax.io
Authorization: Bearer <token>
```

#### cURL
```bash
curl 'https://pro-duoxme.fermax.io/notification/api/v1/mutedevice/me?deviceId=<DEVICE_ID>&token=<FCM_TOKEN_URL_ENCODED>' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -H 'Content-Type: application/json'
```

#### Success Response (Actual)
- **Status Code**: `200 OK`
- **Body**: `false` (raw boolean, not a JSON object)

| Value | Description |
|-------|-------------|
| `false` | Notifications are NOT muted (enabled) |
| `true` | Notifications ARE muted (disabled) |

> [!NOTE]
> The response is a raw boolean value, not wrapped in a JSON object. This can be used to create a switch entity in Home Assistant for muting/unmuting notifications.

---

## 6. Call Manager Service

### 6.1 Get Call Registry

Retrieves the call history for the user's paired devices.

```http
GET /callManager/api/v1/callregistry/participant
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `appToken` | string | Yes | FCM push notification token (URL encoded) |
| `callRegistryType` | string | Yes | Type filter: `all`, `missed_call`, or `autoon` |

#### Response
| Field | Type | Description |
|-------|------|-------------|
| `Content-Type` | Header | `application/json` |
| Response Size | - | ~2 bytes (empty) / ~446-1115 bytes (with data) |

#### Example Request
```http
GET /callManager/api/v1/callregistry/participant?appToken=cSyPGh6...&callRegistryType=all HTTP/1.1
Host: pro-duoxme.fermax.io
Authorization: Bearer <token>
```

#### cURL
```bash
curl 'https://pro-duoxme.fermax.io/callManager/api/v1/callregistry/participant?appToken=<FCM_TOKEN_URL_ENCODED>&callRegistryType=all' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -H 'Content-Type: application/json'
```

#### Success Response
- **Status Code**: `200 OK`

#### Response Schema (Actual)
Returns an **array** of call registry entries:

```json
[
  {
    "registryId": "69629d550c15ed3bf54ab666",
    "deviceId": "00009208516a2dac001d00c3",
    "callDate": "2026-01-10T19:41:25.183+01:00",
    "registerCall": "M",
    "isAutoon": true,
    "photoId": null,
    "roomId": "00009208516a2dac001d00c3_1768070485110"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `registryId` | string | Unique identifier for the call record (MongoDB ObjectId) |
| `deviceId` | string | The monitor device that received/initiated the call |
| `callDate` | string | ISO 8601 datetime with timezone |
| `registerCall` | string | Call status: `M` (missed), `P` (picked up), etc. |
| `isAutoon` | boolean | `true` if this was an auto-on preview, `false` for doorbell ring |
| `photoId` | string \| null | PhotoCaller image ID if available |
| `roomId` | string | WebRTC room identifier for the call session |

#### Call Registry Types
| Type | Description |
|------|-------------|
| `all` | All call records |
| `missed_call` | Only missed/unanswered calls |
| `autoon` | Only auto-on (manual camera preview) sessions |

> [!TIP]
> The `roomId` field contains the device ID and a timestamp. This could be useful for correlating calls with video recordings if PhotoCaller is enabled.

---

### 6.2 Get Photo Call (PhotoCaller Image)

Retrieves the photo captured during a doorbell ring using the `photoId` from the call registry.

```http
GET /callManager/api/v1/photocall?photoId={photoId}
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `photoId` | string | Yes | Photo ID from call registry entry |

#### Response
| Field | Type | Description |
|-------|------|-------------|
| `Content-Type` | Header | `application/json` |

#### Example Request
```http
GET /callManager/api/v1/photocall?photoId=abc123def456 HTTP/1.1
Host: pro-duoxme.fermax.io
Authorization: Bearer <token>
```

#### cURL
```bash
curl 'https://pro-duoxme.fermax.io/callManager/api/v1/photocall?photoId=<PHOTO_ID>' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -H 'Content-Type: application/json'
```

#### Success Response (from bluecon library)
- **Status Code**: `200 OK`

```json
{
  "image": {
    "data": "<base64_encoded_image_data>"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `image.data` | string | Base64 encoded JPEG image |

#### Decoding the Image
```python
import base64

response_json = await response.json()
image_bytes = base64.b64decode(response_json["image"]["data"])
# Save or process image_bytes as JPEG
```

#### Error Responses
| Status Code | Description |
|-------------|-------------|
| `404 Not Found` | Photo with specified ID does not exist |

```json
{"title": "Not Found", "status": 404, "detail": "Photo Call not found: <photoId>"}
```

> [!NOTE]
> Photos are only captured for actual doorbell rings when PhotoCaller is enabled. Auto-on sessions (manual camera preview) do not capture photos (`photoId` will be `null` in call registry).

---

### 6.3 Delete Call Registry Entries

Deletes (hides) one or more call registry entries from the user's call history.

```http
DELETE /callManager/api/v1/callregistry/participants
```

#### Request Body Schema (Actual)
```json
{
  "participantIds": ["69629b1d1f211357ac292d2b"],
  "fcmToken": "cSyPGh6-2kZQlIFS-EteGb:APA91bEfiEk..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participantIds` | array | Yes | Array of `registryId` values from call registry to delete |
| `fcmToken` | string | Yes | FCM push notification token |

#### Example Request
```http
DELETE /callManager/api/v1/callregistry/participants HTTP/1.1
Host: pro-duoxme.fermax.io
Authorization: Bearer <token>
Content-Type: application/json

{
  "participantIds": ["69629b1d1f211357ac292d2b"],
  "fcmToken": "<FCM_TOKEN>"
}
```

#### cURL
```bash
curl -X DELETE 'https://pro-duoxme.fermax.io/callManager/api/v1/callregistry/participants' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -H 'Content-Type: application/json' \
  -d '{"participantIds":["<REGISTRY_ID>"],"fcmToken":"<FCM_TOKEN>"}'
```

#### Success Response (Actual)
- **Status Code**: `200 OK`

```json
{
  "hidden": true,
  "errorMessage": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `hidden` | boolean | `true` if entries were successfully hidden |
| `errorMessage` | string \| null | Error message if operation failed, `null` on success |

> [!NOTE]
> This endpoint "hides" entries rather than permanently deleting them. The `participantIds` are the `registryId` values from the call registry response.

---

## 7. Subscription Service

### 7.1 Get Subscription Plans

Retrieves available subscription plans.

```http
GET /subscriptionnowifi/api/v1/plans
```

#### Request
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| - | - | - | No parameters required |

#### Response
| Field | Type | Description |
|-------|------|-------------|
| `Content-Type` | Header | `application/json; charset=utf-8` |
| Response Size | - | ~1062 bytes |

#### Example Request
```http
GET /subscriptionnowifi/api/v1/plans HTTP/1.1
Host: pro-duoxme.fermax.io
Authorization: Bearer <token>
```

#### cURL
```bash
curl 'https://pro-duoxme.fermax.io/subscriptionnowifi/api/v1/plans' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'app-version: 4.2.5' \
  -H 'app-build: 2' \
  -H 'Content-Type: application/json'
```

#### Success Response
- **Status Code**: `200 OK`

#### Response Schema (Actual)
Returns an array of subscription plan objects:

```json
[
  {
    "id": "d2d5d64a-0d25-4f11-babc-8e79d3103c49",
    "code": "FREE",
    "features": [
      { "feature": "OpenDoor", "value": 4 },
      { "feature": "CallDivert", "value": 4 },
      { "feature": "Photocaller", "value": 0 },
      { "feature": "AutoOn", "value": 0 },
      { "feature": "Guests", "value": 0 }
    ]
  },
  {
    "id": "d2d5d64a-0d25-4f11-babc-8e79d3103c50",
    "code": "UNLIMITED_1",
    "features": [
      { "feature": "OpenDoor", "value": 10000000 },
      { "feature": "CallDivert", "value": 10000000 },
      { "feature": "Photocaller", "value": 10000000 },
      { "feature": "AutoOn", "value": 10000000 },
      { "feature": "Guests", "value": 5 }
    ]
  }
]
```

#### Plan Codes
| Code | Description |
|------|-------------|
| `FREE` | Limited free tier (4 door opens/call diverts per day) |
| `UNLIMITED_1` | Premium tier with unlimited actions |
| `UNLIMITED_2` | Premium tier variant |
| `UNLIMITED_3` | Premium tier variant |

> [!IMPORTANT]
> The `value` field represents usage limits. `10000000` effectively means unlimited. `0` means the feature is not available.
```

> [!NOTE]
> This endpoint appears to be for marketing/upselling purposes. It may not be essential for a Home Assistant integration.

---

## 8. Monitoring (Telemetry)

### 8.1 Submit Traces

Endpoint for application telemetry/monitoring. Currently returns an error.

```http
POST /monitoring/v1/traces
```

#### Response
- **Status Code**: `405 Method Not Allowed`

> [!WARNING]
> This endpoint consistently returns `405 Method Not Allowed`. It may be deprecated or require special headers. Not recommended for integration use.

---

## App Startup Sequence

Based on the captured network traffic, the mobile app follows this sequence on startup:

```mermaid
sequenceDiagram
    participant App
    participant Auth
    participant User
    participant Pairing
    participant Device
    participant Notification

    App->>Auth: (OAuth2 Login - not captured)
    Auth-->>App: Access Token
    
    App->>User: GET /user/api/v1/users/me
    User-->>App: User Profile
    
    App->>Pairing: GET /pairing/api/v4/pairings/me
    Pairing-->>App: Paired Devices List
    
    loop For each device
        App->>Device: GET /deviceaction/api/v1/device/{deviceId}
        Device-->>App: Device Details
        
        App->>Device: GET /deviceaction/api/v1/device/{deviceId}/panels
        Device-->>App: Panels List
        
        App->>Device: GET /services2/api/v1/services/{deviceId}?deviceType=wifi
        Device-->>App: Enabled Services
    end
    
    App->>Notification: POST /notification/api/v1/apptoken
    Notification-->>App: OK
```

---

## Home Assistant Integration Recommendations

### Entities to Create

| Entity Type | Description | API Source |
|-------------|-------------|------------|
| **Lock** | Door lock control | `directed-opendoor` endpoint |
| **Camera** | Video feed from panel | `autoon` endpoint (check for RTSP/WebRTC) |
| **Binary Sensor** | Device online/offline | `device/{deviceId}` endpoint |
| **Sensor** | Last call timestamp | `callregistry` endpoint |
| **Sensor** | Missed calls count | `callregistry?type=missed_call` |
| **Switch** | Mute notifications | `mutedevice` endpoint |

### Polling Intervals

| Data Type | Recommended Interval | Reason |
|-----------|---------------------|--------|
| Device Status | 60 seconds | Low frequency, status rarely changes |
| Panels | 300 seconds | Panel configuration rarely changes |
| Call Registry | 60 seconds | Useful for doorbell notifications |
| Services | 3600 seconds | Service configuration rarely changes |

### Authentication Strategy

1. **Option A**: Implement OAuth2 flow to get access tokens (recommended)
2. **Option B**: Capture and use refresh tokens from the mobile app
3. **Option C**: Investigate if there's an API key option

### Error Handling

| Status Code | Meaning | Action |
|-------------|---------|--------|
| `200` | Success | Process response |
| `401` | Unauthorized | Refresh access token |
| `403` | Forbidden | Check permissions |
| `409` | Conflict | Wait and retry (auto-on busy) |
| `429` | Rate Limited | Implement exponential backoff |
| `5xx` | Server Error | Retry with backoff |

---

## Unknown/Missing Information

The following items require further investigation during implementation:

1. **Video Streaming Protocol**: Confirmed to use **FCM push notifications** + likely **WebRTC**. The `autoon` response indicates `blueStream` service with `duox` technology.
2. **FCM Push Payload**: Exact format of the push notification containing stream connection data
3. **WebRTC SDP/ICE Details**: STUN/TURN server configuration for video connection

> [!NOTE]
> OAuth2 authentication, all response schemas (including PhotoCaller), and door control are now fully documented.

---

## Related Projects & References

### Existing Home Assistant Integrations

| Project | URL | Features | Notes |
|---------|-----|----------|-------|
| **hass-bluecon** | [AfonsoFGarcia/hass-bluecon](https://github.com/AfonsoFGarcia/hass-bluecon) | Door open, call history, still camera | Active, 47 releases, HACS compatible |
| **HASS-BlueCon** | [cvc90/HASS-BlueCon](https://github.com/cvc90/HASS-BlueCon) | Fork with Spanish translations | Community fork |
| **fermax-blue-intercom** | [marcosav/fermax-blue-intercom](https://github.com/marcosav/fermax-blue-intercom) | Door open only | Simple Python script |

### Key Library: bluecon

The `bluecon` Python library ([AfonsoFGarcia/bluecon](https://github.com/AfonsoFGarcia/bluecon)) provides:

- **OAuth2 authentication** handling
- **FCM push notification receiving** via `push_receiver` library
- **Door opening** API calls
- **PhotoCaller** still image retrieval

```bash
pip install bluecon
```

> [!IMPORTANT]
> The `bluecon` library uses `push_receiver` to receive Firebase Cloud Messaging notifications **without** being a mobile app. This is the key to handling doorbell rings and video stream initiation.

### Video Streaming Status

| Feature | Status | Implementation |
|---------|--------|----------------|
| Door Open | ✅ Working | Direct API call |
| Still Camera (PhotoCaller) | ✅ Working | `getLastPicture()` API |
| Live Video Streaming | ⚠️ Experimental | FCM → WebRTC (has errors in hass-bluecon) |
| Doorbell Notifications | ✅ Working | FCM push via `push_receiver` |

---

## Appendix: Raw Endpoint Summary

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | `/oauth/token` | 200 | OAuth2 authentication |
| GET | `/user/api/v1/users/me` | 200 | User profile |
| GET | `/pairing/api/v4/pairings/me` | 200 | Paired devices |
| GET | `/deviceaction/api/v1/device/{id}` | 200 | Device details |
| GET | `/deviceaction/api/v1/device/{id}/panels` | 200 | Panel list |
| POST | `/deviceaction/api/v1/device/{id}/directed-opendoor` | 200 | Open door |
| POST | `/deviceaction/api/v2/device/{id}/autoon` | 200/409 | Camera preview |
| GET | `/services2/api/v1/services/{id}` | 200 | Device services |
| POST | `/notification/api/v1/apptoken` | 200 | Register FCM token |
| GET | `/notification/api/v1/mutedevice/me` | 200 | Mute status |
| GET | `/callManager/api/v1/callregistry/participant` | 200 | Call history |
| GET | `/subscriptionnowifi/api/v1/plans` | 200 | Subscription plans |

---

## Development Plan

### Approach
**Build from scratch** using `bluecon` library as reference for:
- FCM push notification handling (via `push_receiver`)
- Authentication patterns
- API structure understanding

### Next Steps

- [x] Document OAuth2 authentication flow
- [x] Capture actual JSON response bodies
- [x] Document door open (`directed-opendoor`) request/response
- [x] Document auto-on (`autoon`) request/response
- [ ] Study `bluecon` source code for FCM implementation
- [ ] Implement Home Assistant config flow for authentication
- [ ] Create coordinator for data polling
- [ ] Build lock entity (door control)
- [ ] Build binary sensor (device online/offline)
- [ ] Build sensor entities (call history, wireless signal)
- [ ] Investigate WebRTC for live video streaming
- [ ] Build camera entity (still images first, then video)

### Architecture Decision

```
┌─────────────────────────────────────────────────────────────────┐
│  Home Assistant Integration Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │  Config Flow     │────▶│  OAuth2 Client   │                 │
│  │  (username/pass) │     │  (token mgmt)    │                 │
│  └──────────────────┘     └────────┬─────────┘                 │
│                                    │                            │
│                                    ▼                            │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │  Data Coordinator│◀───▶│  Fermax API      │                 │
│  │  (polling)       │     │  Client          │                 │
│  └────────┬─────────┘     └──────────────────┘                 │
│           │                                                     │
│           ▼                                                     │
│  ┌────────────────────────────────────────────┐                │
│  │  Entities                                   │                │
│  │  • Lock (door control)                      │                │
│  │  • Binary Sensor (online/offline)           │                │
│  │  • Sensor (wireless signal, call count)     │                │
│  │  • Camera (still images via PhotoCaller)    │                │
│  │  • Event (doorbell ring via FCM - future)   │                │
│  └────────────────────────────────────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

*Document generated from network captures of the Fermax DuoxMe mobile app (macOS).  
Captured on: January 10, 2026  
Last updated: January 10, 2026*

