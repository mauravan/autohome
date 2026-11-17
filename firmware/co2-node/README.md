# Battery CO₂ Sensor Node (ESP32 + SCD41 + WeAct e-paper)

Battery-powered per-floor CO₂ / temperature / humidity node. Wakes every 15 minutes
(product default; home floors currently run 5 min), takes 1× SCD41 single-shot
measurement (retried up to 3× on failure), fully refreshes a WeAct 1.54" (200×200)
or WeAct 4.2" (400×300) B/W e-paper, selected at runtime, publishes to the Mosquitto
broker via ESPHome MQTT discovery, then deep-sleeps. Battery is sampled 3× per wake at the
quietest load point (radio idle, SCD41 powered down, before the e-paper render) and averaged
via `sliding_window_moving_average` (window 3), matching the SCD41 channels.

Three variants share one package: `top.yaml`, `mid.yaml`, `bottom.yaml` differ only in
`device_name` / `friendly_name` / `floor_label`. Sensor `name`s live in
`co2-node-core.yaml` and carry the floor prefix directly
(`name: "${friendly_name} CO2"` → `"Top Floor CO2"`), which HA slugifies to the entity
ids the dashboard already references (`sensor.top_floor_co2`, `_temperature`,
`_humidity`, and the `mid_floor_*` / `bottom_floor_*` triplets).

> **Why the floor token is in the sensor `name`**: ESPHome ≥2024 MQTT discovery sets the
> discovery `name` to the sensor's own `name` (not `friendly_name + name`), so a bare
> `name: "CO2"` with `friendly_name: "Top Floor"` would surface as `sensor.co2` — and all
> three floors would collide on the same `unique_id`. The `${friendly_name}` prefix keeps
> each floor distinct.

## Files

| File | Purpose |
|---|---|
| `co2-node-core.yaml` | Shared aggregator: base + WiFi/MQTT/SNTP transport + setup flow |
| `co2-node-base.yaml` | Shared hardware package: ESP32, SCD41, e-paper, deep sleep, OTA, safe_mode |
| `co2-node-wifi.yaml` | WiFi/MQTT/SNTP transport (the WiFi component itself lives in `co2-node-setup.yaml`) |
| `co2-node-ble.yaml` | BLE/BTHome transport; WiFi stays off except during setup/cold-boot config window |
| `co2-node-setup.yaml` | Shared QR/AP/captive-portal setup flow, finish/reset buttons, `provisioned` flag |
| `co2-node-webui.yaml` | Web server + sorting groups |
| `co2-node-secure.yaml` | Product-only: NVS encryption, signed OTA, downgrade protection |
| `co2-node-home.yaml` | Home package: default MQTT broker + SNTP servers (station WiFi is provisioned, not compiled in) |
| `gift.yaml` | Gift build: generic MAC-suffixed identity, unprovisioned defaults, no station creds |
| `top.yaml` / `mid.yaml` / `bottom.yaml` | Per-floor identity + `!include` of core + home packages |
| `secrets.yaml.example` | Template for git-ignored `secrets.yaml` (only MQTT/OTA secrets are used now) |
| `README.md` | This file |

## Pinout schema (ESP32-C3 SuperMini / `esp32-c3-devkitm-1`)

Connect all grounds to the ESP32-C3 ground. This maps the configured sensor, display,
and documented battery-board connections (VBAT/2 output and GND); cell/power-input terminals
are board-specific and not identified here.

| Module | Pin / signal | Connect to | Notes |
|---|---|---|---|
| SCD41 sensor | SDA | GPIO1 | I²C. Breakouts commonly have 10 kΩ pull-ups to VDD; ESPHome internal pulls are disabled so the unpowered sensor is not back-fed. |
| SCD41 sensor | SCL | GPIO21 | I²C. GPIO21 is UART0 TX; ROM boot text may toggle it during reset. Logger uses native USB (GPIO18/19), not UART0. |
| SCD41 sensor | VDD | Switched 3V3 rail | High-side P-MOSFET rail; allow 1 s to settle before I²C access. |
| SCD41 sensor | GND | ESP32-C3 GND | Common ground. |
| E-paper display | DIN (MOSI) | GPIO6 | SPI data to display; no MISO connection. |
| E-paper display | CLK (SCK) | GPIO4 | SPI clock. |
| E-paper display | CS | GPIO7 | Do not drive while display power is off. |
| E-paper display | DC | GPIO5 | Do not drive while display power is off. |
| E-paper display | RST | GPIO0 | Do not drive while display power is off. |
| E-paper display | BUSY | GPIO10 | BUSY is high during update; display update blocks until it falls. |
| E-paper display | VCC | Switched 3V3 rail | Same high-side rail as SCD41. Bring the rail up before display initialization; driving SPI/control pins while unpowered can back-power the panel. |
| E-paper display | GND | ESP32-C3 GND | Common ground. |
| Battery-management board | ADC output (VBAT/2) | GPIO3 (ADC1_CH3) | Firmware multiplies the reading by 2 to report cell voltage. Keep this divider off GPIO2: GPIO2 is a boot-strapping pin. |
| Battery-management board | GND | ESP32-C3 GND | Common ADC reference. |
| Peripheral-power P-MOSFET | Gate | GPIO20 | Active high: high turns on the switched 3V3 rail for SCD41 + display. GPIO20 floats during deep sleep; add an external gate pull-down. |

GPIO2 / GPIO8 / GPIO9 remain unused (boot strapping, onboard LED, BOOT button).

If the display cannot reliably share the switched rail, gate only the SCD41; e-paper idle draw is already ~0.

### If it works 1–2 wakes then sticks on BOOTING

That pattern is a brownout / rail-sag signature, not WiFi. The cell sags under transmit +
EPD refresh + SCD41 load; the next reset fires with a half-charged SCD41 / unseated EPD,
`scd41_sensor` warns (`Data not ready` / NACK), the panel never renders page_normal, and
`deep_sleep.enter` is only reached via the failsafe. Check in this order:

1. Scope/meter the switched 3V3 at reset: must be stable 3.3 V **before** any I2C or EPD render.
2. Bypass the MOSFET (EPD VCC + SCD41 VDD straight to 3V3). If cycling recovers, the FET or its gate drive is the fault — not SCL21.
3. In the DEBUG logs (`hardware_uart: USB_SERIAL_JTAG`, USB-C serial): `wakeup_cause`, `scd4x` `Failed to stop measurements` / `Data not ready` (sensor not up), `Timeout while displaying image!` (EPD BUSY stuck).
4. Revert to `logger: level: NONE` + `sleep_duration: 5min` once stable — DEBUG logging over USB costs wake time.

## Flash & verify (dev, ESP32-C3 SuperMini)

Prereqs on the workstation: `pip install esphome`, `sudo apt install mosquitto-clients`.

The C3 SuperMini enumerates as a native-USB CDC port (`/dev/ttyACM0`), not a `ttyUSB`
CH340 port.

```bash
cd firmware/co2-node
cp secrets.yaml.example secrets.yaml   # fill in WiFi + MQTT credentials
ls /dev/ttyACM* /dev/ttyUSB*           # find the board's port
esphome config top.yaml                # expect "Configuration is valid"
esphome run top.yaml --device /dev/ttyACM0
```

`secrets.yaml` is git-ignored and never committed. Flash over USB serial. No native
API (`api:`) is configured — HA integration is MQTT; the node also serves a local web
UI on port 80 (plus the captive portal for WiFi setup (custom minimal page; HTTP OTA is not exposed there — use the web UI or serial flashing)).

Serial monitor should show, in order: boot → setup QR/AP → (after joining the home
WiFi through the captive portal) `WiFi connected` → 1× SCD41 single-shot (retried up
to 3× on failure) → CO₂/temp/humidity logged → `MQTT connected`. On cold boots the
screen holds the centered cog + IP for 60 s after everything is ready, then renders
the readings page and `Entering deep sleep`. Timer wakes skip the config window and
sleep as soon as the reading is advertised. Then silence for ~5 min before the wake
sequence repeats.

Confirm telemetry from the workstation:

```bash
mosquitto_sub -h homeassistant.local -u mqtt_user -P 'YOUR_MQTT_PASSWORD' -t '#' -v
```

Expect discovery configs under `homeassistant/sensor/…/config` and state topics carrying
the ppm value, then silence during sleep.

Top/mid devices that predate the battery sensor must be reflashed before battery entities appear (bottom already publishes).

## Production port: ESP32-C6 mini + battery (documented; not built yet)

Same `co2-node-core.yaml` logic. When the C6 board is in hand, three changes:

1. **Board**: `esp32.board:` → the C6 board id (`esp32-c6-devkitc-1` or the specific
   "mini" board's `board:`; add `variant: esp32c6` if the board requires it).
2. **Pin remap**: `i2c.sda/scl`, `spi.clk_pin/mosi_pin`, and
   `cs_pin/dc_pin/reset_pin/busy_pin` → the C6 board's exposed GPIOs. Logical wiring is
   unchanged; physical numbers differ per board.
3. **Battery power path**: single Li-ion/LiPo cell (3.7 V) → low-quiescent-current
   3.3 V LDO → ESP32-C6. A P-channel MOSFET (GPIO-gated) cuts VCC to **both** SCD41 and
   e-paper during deep sleep so peripheral current is ~0 (also removes the e-paper
   DC-bias-while-floating risk). ESP32-C6 deep-sleep is ~7 µA (chip); the board LDO
   quiescent current dominates — pick an LDO with µA-scale IQ.

### Power optimizations already in `co2-node-base.yaml` / `co2-node-setup.yaml`

- `logger.level: NONE` — no log formatting/TX per wake (flip to `DEBUG` only while developing).
- `wifi.power_save_mode: LIGHT` — modem dozes between beacons during the awake phase; an earlier AP failed the 4-way handshake with LIGHT, revert to `none` in `co2-node-setup.yaml` if association becomes flaky.
- `wifi.output_power: 8.5dB` — cuts TX peak current; raise toward 20 dB if range is marginal.
- `i2c.scan: false` — no boot-time bus probe.
- Single gated e-paper refresh per wake (was two renders + a 1 s delay; `component.update`/`update()` blocks on BUSY, so one render is safe).
- The 4.2" normal page shows the Zurich-local render time (`UPDATED DD.MM. HH:MM`) from SNTP. Its minute is included in the render signature, so the panel refreshes once per wake even when sensor values are unchanged; the 1.54" layout and skip-unchanged behavior are unchanged.
- No-flash e-paper waveform: normal refreshes use the controller's display Mode 2 (`0x22=0xFC`, direct pixel update, no inversion), with a full Mode 1 cleanup (`0x22=0xF7`) on cold boot, on panel switch, and every Nth partial refresh (`# · Full refresh every` in the web UI, default 24 = `DEFAULT_PARTIAL_REFRESHES_BEFORE_FULL`).
- `cpu_frequency: 80MHZ` — minimum for the C3.
- `deep_sleep` after publish; SCD41 `power_down` (0x36e0) → ~0.8 µA between wakes.

### Power budget (for battery sizing)

Estimates, not measured. Per 5-min wake after the optimizations above:

| Phase | Time | Notes |
|---|---|---|
| Boot + WiFi associate + DHCP | ~2–3 s | overlaps the first measurement attempt |
| 1× SCD41 single-shot | ~6 s | radio idles in modem sleep |
| MQTT connect + publish | ~1 s | short TX burst |
| 1× e-paper refresh | ~1 s | single render, Mode 2 (measured 0.77 s vs 2.9 s for a Mode 1 cleanup) |
| Deep sleep | ~4.5 min | board LDO quiescent current dominates |

- WiFi association + the awake window now dominate active energy; cadence (`sleep_duration`) remains the biggest lever.
- Expect roughly 1–3 months on a 2500 mAh cell at 5-min cadence. `sleep_duration` 5→15 min ≈ 3× life, 5→30 min ≈ 6×.

### Battery build recommendations

1. **Cadence first.** CO₂/T/RH in a house changes slowly; 15–30 min is fine for a dashboard and multiplies battery life. Tune `deep_sleep.sleep_duration`.
2. **Board selection.** A bare ESP32-C3/C6 module + µA-quiescent LDO (TPS7A02, MCP1700) beats a dev board, whose onboard LED and LDO dominate sleep current. Avoid USB-serial + always-on LED dev boards for the battery build.
3. **Gate peripheral VCC.** P-MOSFET on SCD41 + e-paper 3V3 (see step 3 above) kills both during sleep; also removes the e-paper DC-bias-while-floating risk.
4. **Battery monitoring.** Add an ADC + high-impedance divider (GPIO-gated so it doesn't leak during sleep) and publish voltage so HA can alert before the cell dies.
5. **ASC note.** `automatic_self_calibration: true` *does* run in single-shot mode, but it assumes a ~5 min measurement interval (SCD41 datasheet §3.10.5) and weekly ~400 ppm fresh-air exposure. Extending `sleep_duration` slows ASC proportionally; for long cadences consider periodic FRC against a reference instead.

## Gifting a sensor

Build/flash `gift.yaml` over USB; for a clean identity run
`python -m esptool --chip esp32c3 -p /dev/ttyACM0 erase_flash` first. To gift an
existing node instead: press `Reset to setup` in its web UI before unplugging (clears
MQTT creds/offsets and sets `provisioned=false`).

Recipient flow: the first boot shows a QR code; scan it to join the setup AP
(`co2-setup`, or `co2-setup-top` / `co2-setup-mid` / `co2-setup-bottom` for the
home floors), open `192.168.4.1`, pick the home WiFi (2.4 GHz/WPA2). The screen
flips to a centered cog with the station IP below; reconnect the phone to the home
WiFi, open that IP, set offsets/room label. MQTT is optional (press 'Save MQTT
settings' to apply it without restarting), then press `Finish setup`.

MQTT: leave broker empty for local-only; `homeassistant.local` works when Mosquitto runs
on the HA host, otherwise enter the broker IP; create broker credentials in HA. Entities
arrive via discovery; topics use `co2-sensor-<mac>/…`.

Settings semantics: CO2/humidity offsets are additive; temperature offset is the SCD41
internal offset (also affects RH); altitude is pressure compensation;
offset changes apply immediately (the SCD41 is re-read, ~20 s) and MQTT settings apply
on 'Save MQTT settings' or restart; setup mode stays awake up to 30 min.

Battery note: press `Finish setup` to stop the 30-minute setup window.

Security: setup AP is WPA2 with the published password; the web UI on port 80 has no
authentication; treat it as LAN-local. The UI also lists the internal
`Peripheral Power` switch (because `include_internal` is on); leave it on. Device → '4.2 inch panel' selects the panel (off = 1.54", on = 4.2"); the choice is
stored in NVS. Auto-detection is not possible: the panel interface is write-only SPI and
SSD1681/SSD1683 expose no ID register.


- Broker host `homeassistant.local` resolves via mDNS from the ESP. On `MQTT
  disconnected` / DNS failure, substitute the hub IP in `mqtt.broker`.
- E-paper is WeAct 1.54" (200×200) or WeAct 4.2" (400×300) B/W, selected in the web UI (Device → '4.2 inch panel'). If the panel never initializes, check the rail, wiring, and BUSY line.
- `gfonts://Roboto` needs network at first compile. Offline: drop a local `.ttf` into
  `firmware/co2-node/fonts/` and point `font.file` at it.
- Entity naming hinges on the `${friendly_name}` prefix in each sensor `name`. If HA
  surfaces `sensor.co2` (or floors collide), the substitution is not reaching the package
  — check the `!include` and that `friendly_name` is set per floor.
- Existing Pi publisher topics/`unique_id`s are not in this repo. Capture them at
  cutover (see plan Step 4); if the old publisher cannot be located, stopping the Pis
  and deleting the stale HA entities achieves the same clean names.

## Production flags (no cadence change)

- `production/build_unit.py --render-only --out-dir <dir>` renders
  `product-<last4>.yaml` without flashing and exits 0 without touching
  `units.csv` (`--port` optional in this mode).
- `production/test_unit.py --dry-run --log <file>` exercises the assertion
  logic (thresholds unchanged) without hardware.
