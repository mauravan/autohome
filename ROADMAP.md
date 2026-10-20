# Roadmap

## Phased Rollout

### Phase 0 — Docs (this plan)
Create the 6 tracking files: `README.md`, `INVENTORY.md`, `SENSORS.md`, `STANDARDS.md`, `ARCHITECTURE.md`, `ROADMAP.md`.
**Verification**: All 6 files exist in repo root; `SENSORS.md` has ≥37 data rows; every sensor name is grep-findable; `ARCHITECTURE.md` mermaid renders.

---

### Phase 1 — Hub
**Goal**: Home Assistant running on RPi 5 with 7" touchscreen dashboard, MQTT broker, Samba add-on.
- Flash Home Assistant OS onto 64 GB micro-SD (RPi 5).
- Boot RPi 5 with DSI screen + HifiBerry HAT.
- Configure Wi-Fi (static IP or DHCP reservation).
- Install add-ons: **Mosquitto broker**, **Samba**, **File Editor**, **Terminal & SSH**.
- Verify: `http://homeassistant.local:8123` loads dashboard; touchscreen shows Lovelace; `mosquitto_sub -t '#'` on hub sees `#` traffic.

---

### Phase 2 — Lighting
**Goal**: Philips Hue lamps controllable from HA.
- Purchase: Hue Bridge v2 + per-room Hue lamps (White & Color Ambiance or White Ambiance).
- Pair lamps to Bridge via Hue app.
- Add HA `hue` integration (auto-discovery or manual IP).
- Verify: Toggle a lamp from HA dashboard; automation turns on at sunset.

---

### Phase 3 — Blinds + Roof Windows
**Goal**: Somfy RTS blinds + Velux io roof windows controllable from HA.

- **Somfy RTS blinds**: Purchase **RFLink gateway** (Arduino Mega + 433 MHz transceiver) or pre-built. Pair each blind's rolling code via RFLink CLI. Add HA `rflink` integration (serial/TCP).
- **Velux io roof windows**: If confirmed io, purchase **Velux KLF200** (one unit bridges Velux io + Somfy io — but we have RTS, so KLF200 only used for Velux). Alternative: Somfy Tahoma (cloud) or wait for Velux USB stick + local API.
- Pair devices per their respective manuals.
- Add HA integrations: `rflink` for RTS, `velux` for KLF200 (if Velux are io).
- Verify: Open/close a blind from HA; position slider works (RTS supports %). Open/close a Velux window from HA.
- **Fallback**: If Velux are RTS too (check remote), RFLink handles both — no KLF200 needed.
### Phase 4 — Environmental (CO₂ from Day 1)
**Goal**: Per-floor CO₂ + temperature + humidity in HA; automation opens roof window when CO₂ > 1000 ppm.
- Purchase: **3× Sensirion SCD41 breakout boards** (I2C, 0x62).
- Wire one per floor node:
  - Top: Pi Zero W #1, I2C GPIO 2/3 (3.3 V, pull-ups on breakout).
  - Mid: Pi 3B #2, I2C GPIO 2/3.
  - Bottom: Pi Zero W #2, I2C GPIO 2/3.
- Software per node: ESPHome or lightweight Python MQTT publisher (systemd service).
  - Read SCD41 every 30 s (single-shot or periodic mode).
  - Publish JSON to `homeassistant/sensor/<floor>/scd41/config` (auto-discovery) + state to `home/<floor>/scd41`.
- HA: auto-discovered sensors appear as `sensor.top_floor_co2`, `sensor.top_floor_temperature`, `sensor.top_floor_humidity` (same for mid/bottom).
- Automation (HA YAML or UI):
  ```yaml
  trigger:
    - platform: numeric_state
      entity_id: sensor.top_floor_co2
      above: 1000
  action:
    - service: cover.open_cover
      target:
        entity_id: cover.top_floor_velux_window
  ```
- Verify: Each floor shows CO₂ (ppm), °C, %RH in HA; trigger >1000 ppm (exhale near sensor) → roof window opens.

---

### Phase 5 — Extras
**Goal**: Battery BLE sensors, outdoor LoRa, MEMS vibration, IR remote, dry-contact relays.
- **nRF52 BLE mesh nodes**: program nRF52 DK (Arduino / Zephyr / nRF Connect SDK) to read reed (door), tilt (window), ADXL335 (blind motor vibration) → publish via BLE to nearest Pi Zero W → MQTT.
- **LoRa outdoor node**: Pi Zero W #2 + LoRa pHAT → TTN → webhook → MQTT → HA. Sensors: YL-69 soil moisture, 11035 reed (garage), HC-SR04 (water level?).
- **STM32MP157F-DK2 + STEVAL-MKI197V1**: MEMS vibration/tilt on blind/window motors → local ST edge compute → MQTT.
- **IR remote**: Joy-Pi IR TX/RX (KY-005/KY-022) → LIRC or ESPHome → HA remote control.
- **Relay module (5V)**: dry-contact triggers for KLF200 (if needed for hardwired fallback).
- **HC-SR04**: distance sensing (bin level, water tank) on any node with GPIO.

---

## Purchase List (Rough USD)

| Item | Qty | Unit ~$ | Total ~$ | Notes |
|---|---|---:|---:|---|
| RFLink gateway (Arduino Mega + 433 MHz) | 1 | 35 | 35 | Somfy RTS + Velux RTS if applicable |
| Philips Hue Bridge v2 | 1 | 50 | 50 | Zigbee coordinator for lamps |
| Hue lamps (per room) | ~8–12 | 15–50 | 200–400 | Mix White Ambiance + Color |
| Sensirion SCD41 breakout | 3 | 35–45 | 120 | CO₂ + T + RH, I2C 0x62 |
| 8 GB micro-SD (A2) | 5+ | 5 | 25 | HA OS + 3 nodes + spares |
| micro-USB PSU (Pi Zero W) | 2 | 8 | 16 | 5 V 2.5 A recommended |
| ADS1115 or MCP3008 HAT | 1 | 5 | 5 | For ADXL335 / analog sensors |
| Misc: I2C pull-ups, JST-SH cables, Dupont, heatshrink | — | — | 20 | Wiring consumables |

**Estimated minimum**: ~$471 (bridge + hub + 3 SCD41 + SD + PSU) — RFLink saves ~$165 vs KLF200  
**With full lighting**: ~$685–$885 depending on lamp count.

---

## Acceptance Criteria (End of Phase 4 = MVP)

1. HA reachable at `http://homeassistant.local` with touchscreen dashboard.
2. Every Hue lamp toggleable from HA.
3. Every Somfy io blind + Velux roof window open/close/position from HA.
4. Three `sensor.<floor>_co2` entities in HA, updating ≤30 s.
5. Automation: CO₂ > 1000 ppm on any floor → corresponding Velux roof window opens.
6. MQTT broker receives telemetry from all 3 floor nodes + LoRa (if deployed).

---

## Out of Scope (Future Plans)

- Full ESPHome firmware for Pi Zero W nodes (replace Python publishers).
- Thread/Matter border router (RPi 5 + OpenThread dongle).
- Local voice (Wyoming / Assist) on hub Pi.
- Energy monitoring (Shelly EM / P1 meter).
- Water leak sensors (Aqara / ESPHome) under sinks.
- Camera integration (Frigate on separate box).