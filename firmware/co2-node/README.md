# Battery CO₂ Sensor Node (ESP32 + SCD41 + WeAct e-paper)

Battery-powered per-floor CO₂ / temperature / humidity node. Wakes every 15 minutes
(product default; home floors currently run 5 min), takes 1× SCD41 single-shot
measurement (retried up to 3× on failure), fully refreshes a WeAct 1.54" (200×200)
or WeAct 4.2" (400×300) B/W e-paper, selected at runtime, publishes to the Mosquitto
broker via ESPHome MQTT discovery, then deep-sleeps. Battery is sampled 3× per wake at the
quietest load point (radio idle, SCD41 powered down, before the e-paper render) and averaged
via `sliding_window_moving_average` (window 3), matching the SCD41 channels.

Two generic builds cover every unit: `wifi.yaml` and `ble.yaml` are identical images
flashed to all units. Identity is configured at runtime through the setup AP / config page:

- **Room label** (`room_label`): the e-paper header and (for BLE) the advertisement name.
  Required: **Finish setup** stays disabled until the label is saved.
- **MQTT broker/credentials** (`wifi.yaml` / `test.yaml` only): configured on the config page;
  an empty broker disables MQTT and the unit runs local-only.
- **HA identity**: the node name is `co2-sensor-<mac>` (`name_add_mac_suffix: true`).
  MQTT discovery uses the MAC for `unique_id` and the node name for `object_id`, so
  entity ids look like `co2_sensor_<mac>_co2` and never collide between units. Friendly
  names (`CO2`, `Temperature`, `Humidity`, `Battery`) can be renamed per-entity in HA.

## Files

| File | Purpose |
|---|---|
| `wifi.yaml` | Generic WiFi/MQTT build — flash this to every WiFi unit |
| `ble.yaml` | Generic BLE/BTHome build — flash this to every BLE unit |
| `test.yaml` | Dev build: DEBUG logs + checkerboard e-paper test page (same flow as `wifi.yaml`) |
| `co2-node-core.yaml` | Aggregator for WiFi builds: base + WiFi/MQTT/SNTP transport + setup flow |
| `co2-node-base.yaml` | Shared hardware package: ESP32, SCD41, e-paper, deep sleep, OTA, safe_mode |
| `co2-node-wifi.yaml` | WiFi/MQTT/SNTP transport with MAC-derived discovery identifiers |
| `co2-node-ble.yaml` | BLE/BTHome transport; advertisement name copied from the runtime room label |
| `co2-node-setup.yaml` | Shared QR/AP/captive-portal setup flow + config page, finish/reset buttons, `provisioned` flag |
| `co2-node-mqtt.yaml` | Runtime MQTT broker/port/username/password inputs |
| `co2-node-secure.yaml` | Product-only security package (currently unused) |
| `secrets.yaml.example` | Template for git-ignored `secrets.yaml` (OTA password; MQTT is runtime) |
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
cp secrets.yaml.example secrets.yaml   # fill in OTA password (MQTT is configured on the config page)
ls /dev/ttyACM* /dev/ttyUSB*           # find the board's port
esphome config wifi.yaml               # expect "Configuration is valid"
esphome run wifi.yaml --device /dev/ttyACM0
```

`secrets.yaml` is git-ignored and never committed. Flash over USB serial. No native
API (`api:`) is configured — HA integration is MQTT; the node serves a custom config
page on port 80 (readings, setup inputs, action buttons, calibration/device settings
behind an advanced toggle) plus the captive portal for WiFi setup. HTTP OTA is not
exposed — use serial flashing.

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
- No-flash e-paper waveform: normal refreshes use the controller's display Mode 2 (`0x22=0xFC`, direct pixel update, no inversion), with a full Mode 1 cleanup (`0x22=0xF7`) on cold boot, on panel switch, and every Nth partial refresh (`# · Full refresh every` on the config page, default 24 = `DEFAULT_PARTIAL_REFRESHES_BEFORE_FULL`).
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

Build/flash `wifi.yaml` (or `ble.yaml`) over USB; for a clean identity run
`python -m esptool --chip esp32c3 -p /dev/ttyACM0 erase_flash` first. To gift an
existing node instead: press `Reset to setup` on its config page before unplugging (clears
MQTT creds/offsets and sets `provisioned=false`).

Recipient flow: the first boot shows a QR code; scan it to join the setup AP
(`co2-setup`), open `192.168.4.1`, pick the home WiFi (2.4 GHz/WPA2). The screen
flips to a centered cog with the station IP below; reconnect the phone to the home
WiFi and open that IP. The setup AP page is WiFi-join only on WiFi builds; BLE builds
have no MQTT and are configured over the setup AP, so there it also shows the readings
and configuration. The config page shows **Current readings** (CO2, temperature,
humidity, battery), **Setup** (room label, MQTT broker/credentials for WiFi, status),
and the action buttons (**Save MQTT settings**, **Finish setup**); calibration and
device settings live behind **Show advanced settings**. MQTT is optional (press **Save
MQTT settings** to apply it without restarting), then press **Finish setup**. The room
label is required; **Finish setup** is blocked until it is saved.

MQTT: leave broker empty for local-only; `homeassistant.local` works when Mosquitto runs
on the HA host, otherwise enter the broker IP; create broker credentials in HA. Entities
arrive via discovery; topics use `co2-sensor-<mac>/…`.

Settings semantics:
- CO2/humidity/temperature offsets are all additive corrections applied in software;
  the SCD41's internal 1 °C self-heating offset stays fixed. Altitude is chip-side
  pressure compensation.
- Offset changes apply immediately (the SCD41 is re-read, ~20 s); MQTT settings apply
  on 'Save MQTT settings' or restart.
- **FRC flow**: power-cycle the unit (or press **Reset to setup**) to get the awake
  window, place it in reference conditions (e.g. outside air), open the config page,
  press **Show advanced settings**, set "ppm · FRC reference", press **Calibrate CO2
  (FRC)**. The baseline is persisted to the SCD41's NVM — keep calibrations infrequent
  (months apart), NVM write cycles are consumed.
- **Trend arrow**: CO₂ vs the previous wake, ±25 ppm deadband; no arrow right after a
  calibration or first boot.
- **Smileys**: CO₂ happy below 1000 ppm; humidity happy strictly between 30 % and 60 %;
  temperature is not judged.
- Setup mode stays awake up to 30 min.

Battery note: press `Finish setup` to stop the 30-minute setup window.

Security: setup AP is WPA2 with the published password; the config page on port 80 has no
authentication; treat it as LAN-local. The page also lists the internal
`Peripheral Power` switch behind **Show advanced settings** → **Device** (every entity is
shown); leave it on. **Show advanced settings** → **Device** → '4.2 inch panel' selects
the panel (off = 1.54", on = 4.2"); the choice is stored in NVS. Auto-detection is not possible:
the panel interface is write-only SPI and SSD1681/SSD1683 expose no ID register.


- Broker host `homeassistant.local` resolves via mDNS from the ESP. On `MQTT
  disconnected` / DNS failure, substitute the hub IP in `mqtt.broker`.
- E-paper is WeAct 1.54" (200×200) or WeAct 4.2" (400×300) B/W, selected on the config
  page (**Show advanced settings** → **Device** → '4.2 inch panel'). If the panel never initializes,
  check the rail, wiring, and BUSY line.
- `gfonts://Roboto` needs network at first compile. Offline: drop a local `.ttf` into
  `firmware/co2-node/fonts/` and point `font.file` at it.
- Entity naming is distinct per unit because MQTT discovery uses the MAC address for
  `unique_id` and the node name for `object_id`. If the e-paper header is blank, the
  room label was not set before pressing `Finish setup` — reset to setup and set it.
- Existing Pi publisher topics/`unique_id`s are not in this repo. Capture them at
  cutover (see plan Step 4); if the old publisher cannot be located, stopping the Pis
  and deleting the stale HA entities achieves the same clean names.


