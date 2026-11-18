# Repository Guidelines

Guide for AI assistants working in this repo.

## Project Overview

Home Assistant companion firmware for battery-powered ESP32 CO₂ / temperature / humidity sensor nodes. Each node wakes on a timer, takes one SCD41 single-shot measurement, refreshes a WeAct e-paper display, publishes the reading (MQTT or BLE BTHome), then deep-sleeps. The active code lives under `firmware/co2-node/`; repo root contains hardware inventory and sensor catalog docs.

Current target: **ESP32-C3** (`esp32-c3-devkitm-1`, ESP-IDF framework, 80 MHz). ESP32-C6 is documented as a future pin-remap, not yet built.

## Architecture & Data Flow

### High-level cycle

```
Boot/on_boot scripts -> measure SCD41 -> filter offsets -> publish -> render e-paper -> deep sleep
```

1. **Boot**: `on_boot` priorities load stored offsets/intervals, turn on the peripheral rail, and set deep-sleep duration.
2. **Measure**: `scd4x` runs in `measurement_mode: single_shot`, triggered by a wake script; read waits 5500 ms for data-ready.
3. **Battery**: ADC sampled 3× at quiet load, averaged with `sliding_window_moving_average` (window 3).
4. **Publish hook**: the humidity sensor's `on_value` sets `reading_done` and logs readings.
5. **Transport**:
   - **WiFi builds**: MQTT with Home Assistant discovery, gated by `transport_ready` (WiFi + MQTT + SNTP within 60 s).
   - **BLE builds**: `bthome_adv` advertises CO₂, temp, humidity, battery for ~700 ms; WiFi stays off on timer wakes.
6. **Display**: `runtime_epaper` renders the normal page; RTC noinit `RenderState` skips redundant refreshes.
7. **Sleep**: `finish_wake` runs SCD41 power-down (`0x36E0`) and enters deep sleep.

### Two transport families

| Family | Root files | Packages |
|---|---|---|
|WiFi + MQTT|`wifi.yaml`, `test.yaml`|`co2-node-core.yaml` = base + wifi + setup + webui; `co2-node-mqtt.yaml` = runtime broker inputs|
|BLE BTHome|`ble.yaml`|base + ble + setup + webui|

Both share `co2-node-setup.yaml` for the captive-portal provisioning flow.

### Data flow

```
SCD41 (I²C 0x62, single-shot)
  -> co2 / temperature / humidity sensors
     -> offset filters (globals: co2_offset, hum_offset, temp_offset)
     -> on_value hook -> reading_done, last_reading_millis
  -> battery_percent (ADC, avg x3)
Transport (exclusive):
  WiFi: mqtt_client (HA discovery)
  BLE:  bthome_adv v2 advertisement
Display: runtime_epaper <- values; RenderState decides re-render
Web UI: web_server v3 + captive_portal on setup AP
Sleep: finish_wake -> allow_sleep gate -> deep_sleep
```

## Key Directories

| Directory | Purpose |
|---|---|
| `firmware/co2-node/` | Entire ESPHome project (configs, components, tools, assets). |
| `firmware/co2-node/components/` | Custom C++ components and Python bindings. |
| `firmware/co2-node/components/scd4x/` | SCD41 driver (vendored from ESPHome 2026.10.1, single-shot modes). |
| `firmware/co2-node/components/runtime_epaper/` | Dual-panel (1.54" / 4.2") e-paper driver with RTC render-state dedup. |
| `firmware/co2-node/components/web_server/` | Patched ESPHome web UI v3; `server_index_v3.h` is generated. |
| `firmware/co2-node/components/captive_portal/` | Captive portal for setup AP + DNS server (ESP-IDF). |
| `firmware/co2-node/components/bthome_adv/` | BTHome v2 advertisement encoder. |
| `firmware/co2-node/webui/` | Inputs for web UI generation: `stock_v3.html.gz`, `boot.js`. |
| `firmware/co2-node/fonts/` | Local fonts and logo (`Roboto`, `MaterialIcons`, `logo_green.png`). |
| `firmware/co2-node/tools/` | `regen_webui_header.py` regenerates the patched v3 UI header. |
| `firmware/co2-node/.esphome/` | **Generated build/cache dir** — do not edit or commit. |

## Development Commands

Run from `firmware/co2-node/`:

```bash
# Validate a config
esphome config wifi.yaml

# Compile and flash over USB (native-USB CDC, usually /dev/ttyACM0)
esphome run wifi.yaml --device /dev/ttyACM0

# Compile only
esphome compile wifi.yaml

# OTA upload
esphome upload wifi.yaml --device <host-or-ip>

# Clean build artifacts for one target
esphome clean wifi.yaml

# Verbose logs for debugging (costs wake time / battery)
esphome run wifi.yaml -s log_level DEBUG

# BLE build with light sleep disabled for bench debug
esphome run ble.yaml --device /dev/ttyACM0 -s light_sleep_enabled false

# Validate the generic builds
esphome config wifi.yaml
esphome config ble.yaml
esphome config test.yaml

# Regenerate the patched web UI header after editing webui/boot.js or fonts/logo_green.png
python3 tools/regen_webui_header.py

# Optional: preview patched HTML in a browser
python3 tools/regen_webui_header.py --emit-html /tmp/preview.html
```

Onboarding:

```bash
pip install esphome
sudo apt install mosquitto-clients   # for MQTT verification

cd firmware/co2-node
cp secrets.yaml.example secrets.yaml   # fill in ota_password; MQTT is configured in the web UI
```

Flash a unit cleanly:

```bash
python -m esptool --chip esp32c3 -p /dev/ttyACM0 erase_flash
esphome run wifi.yaml --device /dev/ttyACM0
# or, for BLE:
# esphome run ble.yaml --device /dev/ttyACM0
```

## Code Conventions & Common Patterns

### YAML

- **Package composition**: build files (`wifi.yaml`, `ble.yaml`, `test.yaml`) are thin identity files (`esphome:` + `packages:`). Behaviour lives in `co2-node-*.yaml`.
- **Include / extend**: `!include` for packages; `!extend <id>` to append to shared entities.
- **Substitutions**: only debug/transport toggles (e.g., `light_sleep_enabled`, `log_level`) remain; per-unit identity vars moved to runtime inputs in `co2-node-setup.yaml` / `co2-node-mqtt.yaml`.
- **Sensor naming**: bare sensor names (`"CO2"`, `"Temperature"`, `"Humidity"`, `"Battery"`).
  Uniqueness in Home Assistant comes from `name_add_mac_suffix: true`,
  `discovery_unique_id_generator: mac`, and `discovery_object_id_generator: device_name`.
  Per-unit identity is the runtime `room_label` text input (e-paper header / BLE adv name).
- **Secrets**: `!secret ota_password` in every build; `!secret ota_signing_key` for the unused `co2-node-secure.yaml` package. MQTT credentials are runtime web-UI inputs, not compile-time secrets.

### C++ custom components

- **Namespaces**: `namespace esphome::<component> { ... }` (C++17 nested namespace style).
- **Logging**: `static const char *const TAG = "...";` + `ESP_LOGx` / `ESP_LOGCONFIG`. Repeated info uses `ESP_LOGD`.
- **Lifecycle**: inherit from `Component` or `PollingComponent`; implement `setup()`, `loop()`, `update()`, `dump_config()`. Use `get_setup_priority()` when order matters.
- **Async / scheduling**: use ESPHome's `set_timeout(ms, [this](){ ... })` and `interval:` blocks in YAML. Do not spawn raw FreeRTOS tasks.
- **Error handling**: log with `ESP_LOGE`, call `status_set_warning()`, return `bool` or `ErrorCode`. Failures are logged and reported, not aborted.
- **Priorities**: `setup_priority::HARDWARE` (~800), `DATA` (~600), `WIFI` (captive portal uses `WIFI + 1`). YAML `on_boot` priorities follow the same scale.
- **Cross-component access**:
  - YAML lambdas: `id(scd41_sensor)->set_temperature_offset(...)`.
  - C++ globals: `global_captive_portal` is a non-const singleton; preserve the `// NOLINT` comment.
- **RTC noinit state**: `RTC_NOINIT_ATTR RenderState render_state` survives deep sleep. If you change the struct layout, bump `RENDER_MAGIC` or stale state will be trusted.

### Python bindings

- Each component's `__init__.py` defines `CODEOWNERS`, `DEPENDENCIES`, `AUTO_LOAD`, `CONFIG_SCHEMA`, and async `to_code()`.
- Platform modules: `sensor.py` (scd4x), `display.py` (runtime_epaper).
- Common helpers: `cv.Schema`, `cv.GenerateID`, `cv.declare_id`, `cv.use_id`, `cv.enum`, `cv.Optional`, `cv.All`, `cv.only_on`, `cg.new_Pvariable`, `cg.register_component`, `cg.add(var.set_x(...))`, `cg.add_define`.
- Auto-load chains:
  - `scd4x`: `["sensirion_common"]`
  - `runtime_epaper`: `["split_buffer", "epaper_spi"]`, `DEPENDENCIES = ["spi"]`
  - `web_server`: `["json", "web_server_base"]`
  - `captive_portal`: `web_server_base`, `socket` on ESP32

### Generated files

- **`components/web_server/server_index_v3.h`** is generated by `tools/regen_webui_header.py`. Do not hand-edit. Edit `webui/boot.js` or the logo, then rerun the script.
- **`components/captive_portal/portal_logo.h`** is a C array header generated from `fonts/logo_green.png`; no script exists in the repo, so regenerate it manually if the logo changes.

## Important Files

| File | What it does |
|---|---|
|`wifi.yaml`|Generic WiFi/MQTT build — identical image for every unit.|
|`ble.yaml`|Generic BLE/BTHome build — identical image for every unit.|
|`test.yaml`|Dev build: DEBUG logs, checkerboard page, MAC suffix; same flow as `wifi.yaml`.|
|`co2-node-core.yaml`|WiFi+MQTT aggregator: `base + wifi + setup`. Included by `wifi.yaml` and `test.yaml`.|
| `co2-node-base.yaml` | Hardware package: ESP32, I²C, SPI, SCD41, e-paper, battery, deep sleep, OTA, globals, render script. |
| `co2-node-wifi.yaml` | WiFi/MQTT/SNTP transport, `sntp_poll.h` include, `transport_ready` gate. |
| `co2-node-ble.yaml` | BLE/BTHome transport, local `external_components` listing, light-sleep flag. |
| `co2-node-setup.yaml` | Captive portal AP, QR code, provisioning globals, finish/reset buttons. |
| `co2-node-mqtt.yaml` | Runtime MQTT broker/port/username/password inputs and factory-reset hook. |
| `co2-node-secure.yaml` | Product-only security package (currently unused). **Burns eFuse key block 5 on first boot.** |
| `co2-node-webui.yaml` | `web_server` v3 + sorting groups. Keep `compression: gzip` (default) or the patched UI is bypassed. |
| `secrets.yaml.example` | Template for git-ignored `secrets.yaml`. |
| `sntp_poll.h` | Inline SNTP helper; avoids including `<esp_sntp.h>`. |
| `INVENTORY.md` (root) | Hardware inventory table. |
| `SENSORS.md` (root) | Sensor/module catalog. |
| `firmware/co2-node/README.md` | Operational runbook: pinout, flashing, MQTT verification, troubleshooting, power budget. |

## Runtime/Tooling Preferences

- **Runtime**: ESPHome CLI (`pip install esphome`). No version pin in repo; last cached build used ESPHome `2026.10.1` with ESP-IDF `5.5.6`.
- **Framework**: ESP-IDF, not Arduino.
- **USB port**: native-USB CDC (`/dev/ttyACM0`), not `ttyUSB`.
- **Offline builds**: `gfonts://Roboto` needs network on first compile. Local `fonts/Roboto-Regular.ttf` and `fonts/MaterialIcons-Regular.ttf` are used; keep paths relative to `firmware/co2-node/`.
- **Package manager**: Python `pip` for ESPHome; `mosquitto-clients` and `esptool` are optional host helpers.
- **Generated build dir**: `firmware/co2-node/.esphome/` is git-ignored; do not commit it.
- **Tool constraints**:
  - `tools/regen_webui_header.py` uses stdlib only.
  - `webui/stock_v3.html.gz` upgrades can silently break the byte-exact JS patches; verify `--emit-html` after any stock bundle change.
  - The BLE advertisement name is copied from the runtime `room_label` (≤16 chars); the BTHome encoder trims it to fit the 31-byte payload (≈9 chars visible). Longer names can be renamed in HA.

## Testing & QA

- **Automated tests**: none. No `pytest`, `tox`, CI, pre-commit, or lint/format config exists in the repo.
- **Config validation**: `esphome config <target>.yaml` is the primary static check. Expect `"Configuration is valid"`.
- **Manual QA**:
  - Flash and watch serial: boot → setup QR/AP → `WiFi connected` → SCD41 single-shot → `MQTT connected` → render → deep sleep.
  - Verify MQTT: `mosquitto_sub -h homeassistant.local -u mqtt_user -P '...' -t '#' -v`.
  - Brownout triage: scope 3V3 rail at reset; check logs for `wakeup_cause`, `Data not ready`, `Timeout while displaying image!`.
  - Entity naming: entities are unique per unit via MAC-based `discovery_unique_id_generator: mac` and node-name `discovery_object_id_generator: device_name`. If the e-paper header is blank, the room label was not set before `Finish setup`.
- **Coverage**: none; power budget figures in README are estimates, not measured.
- **Production tooling**: `README.md` previously referenced `production/build_unit.py` and `production/test_unit.py`; the corresponding `product.yaml`/`product-ble.yaml` build files have been removed. Do not document them as runnable until restored or docs are updated.
