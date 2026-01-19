# Fermax DuoxMe for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/puboe/fermax-douxme-homeassistant.svg)](https://github.com/puboe/fermax-douxme-homeassistant/releases)

Home Assistant integration for Fermax DuoxMe video door intercoms.

## Features

- 🔐 **Door Control** - Unlock doors from Home Assistant (F1, F2, General doors)
- 📶 **Device Status** - Monitor connection status and signal strength
- 📷 **PhotoCaller Ready** - Camera entity for still images (requires Phase 2)
- 🌍 **Multi-language** - EN, ES, IT, PT, DE translations

### Coming in Phase 2
- 📞 Call history sensors and logbook events
- 🔕 Mute notifications toggle
- 📷 PhotoCaller photos from doorbell rings
- ⚡ Real-time FCM notifications

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the **⋮** menu (top right) → **Custom repositories**
3. Add `https://github.com/puboe/fermax-douxme-homeassistant` with category **Integration**
4. Click **+ Explore & Download Repositories**
5. Search for "Fermax DuoxMe"
6. Click **Download**
7. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy `custom_components/fermax_duoxme` to your `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Fermax DuoxMe"
4. Enter your Fermax account credentials (same as the DuoxMe app)
5. Select which devices to add (if you have multiple)

### Options

| Option | Default | Description |
|--------|---------|-------------|
| Polling interval | 30 seconds | How often to refresh device data |

## Entities

For each paired device, the integration creates:

| Entity Type | Entity | Description |
|-------------|--------|-------------|
| Lock | `lock.fermax_{tag}_{door}` | Door control - one per visible door |
| Binary Sensor | `binary_sensor.fermax_{tag}_status` | Device connectivity |
| Sensor | `sensor.fermax_{tag}_signal_strength` | WiFi signal (0-100%) |
| Camera | `camera.fermax_{tag}` | PhotoCaller (if enabled) |

> **Note:** The `{tag}` is the name you gave your device in the Fermax DuoxMe app (e.g., "Front Door").

## Example Automations

### Unlock door when person arrives
```yaml
automation:
  - alias: "Unlock front door on arrival"
    trigger:
      - platform: zone
        entity_id: person.john
        zone: zone.home
        event: enter
    action:
      - service: lock.unlock
        target:
          entity_id: lock.fermax_front_door_zero
```

### Notify when device goes offline
```yaml
automation:
  - alias: "Alert intercom offline"
    trigger:
      - platform: state
        entity_id: binary_sensor.fermax_front_door_status
        to: "off"
    action:
      - service: notify.mobile_app
        data:
          message: "Intercom went offline!"
```

## Troubleshooting

### Invalid credentials
Make sure you're using the same email and password as the Fermax DuoxMe mobile app.

### No devices found
Ensure your intercom is paired in the DuoxMe app and showing online.

### Door won't open
Check that your subscription allows door control. FREE accounts have a 4 opens/day limit.

## Known Limitations

- **No live video streaming** - Only PhotoCaller entity (photos coming in Phase 2)
- **No real-time notifications** - Uses polling (30 second delay)
- **Call history requires FCM** - Coming in Phase 2

## Development

### Setting Up the Environment

```bash
# Clone the repository
git clone https://github.com/puboe/fermax-douxme-homeassistant.git
cd fermax-douxme-homeassistant

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install pytest pytest-asyncio pytest-homeassistant-custom-component aiohttp PyTurboJPEG
```

### Running Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=custom_components/fermax_duoxme --cov-report=term-missing

# Run specific test file
pytest tests/test_models.py -v
```

## Credits

- API reverse-engineering based on [bluecon](https://github.com/AfonsoFGarcia/bluecon) by Afonso Garcia
- Inspired by [hass-bluecon](https://github.com/AfonsoFGarcia/hass-bluecon)

## License

MIT License - see [LICENSE](LICENSE) for details.

