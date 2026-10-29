# Battery CO₂ Sensor Node (ESP32 + SCD41 + WeAct e-paper)

Battery-powered per-floor CO₂ / temperature / humidity node. Wakes every 5 minutes,
takes one SCD41 single-shot measurement, fully refreshes a WeAct 1.54" B/W e-paper
(SSD1681), publishes to the Mosquitto broker via ESPHome MQTT discovery, then deep-sleeps.

Three variants share one package: `top.yaml`, `mid.yaml`, `bottom.yaml` differ only in
`device_name` / `friendly_name` / `floor_label`. Sensor `name`s live in
`co2-node-common.yaml` and carry the floor prefix directly
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
| `co2-node-common.yaml` | Shared package: ESP32, WiFi, MQTT, SCD41, e-paper, deep sleep |
| `top.yaml` / `mid.yaml` / `bottom.yaml` | Per-floor identity + `!include` of the package |
| `secrets.yaml.example` | Template for git-ignored `secrets.yaml` |
| `README.md` | This file |

## Wiring (dev board: ESP32-C3 SuperMini / `esp32-c3-devkitm-1`)

| Signal | ESP32-C3 GPIO | Note |
|---|---|---|
| SCD41 SDA | GPIO1 | I²C; breakout usually has 10 kΩ pull-ups |
| SCD41 SCL | GPIO3 | |
| SCD41 VDD | 3V3 | |
| SCD41 GND | GND | |
| EPD DIN (MOSI) | GPIO6 | |
| EPD CLK (SCK) | GPIO4 | |
| EPD CS | GPIO7 | |
| EPD DC | GPIO5 | |
| EPD RST | GPIO0 | |
| EPD BUSY | GPIO10 | |
| EPD VCC | 3V3 | |
| EPD GND | GND | |

GPIO2 / GPIO8 / GPIO9 (boot strapping, onboard LED, BOOT button) and GPIO20 / GPIO21
(UART0 console) are left untouched. The board is USB-powered, so there is no VCC gating
on this build.

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

`secrets.yaml` is git-ignored and never committed. Flash over USB serial (the node is
MQTT-only — no `api:`/`ota:` — so no native-API handshake cost during its short wake).

Serial monitor should show, in order: boot → `WiFi connected` → SCD41 single-shot
measurement (~5 s) → CO₂/temp/humidity logged → `MQTT connected` → display render →
`Entering deep sleep`. Then silence for ~5 min before the wake sequence repeats.

Confirm telemetry from the workstation:

```bash
mosquitto_sub -h homeassistant.local -u mqtt_user -P 'YOUR_MQTT_PASSWORD' -t '#' -v
```

Expect discovery configs under `homeassistant/sensor/…/config` and state topics carrying
the ppm value, then silence during sleep.

## Production port: ESP32-C6 mini + battery (documented; not built yet)

Same `co2-node-common.yaml` logic. When the C6 board is in hand, three changes:

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

### Power budget (for battery sizing)

- SCD41 single-shot ≈ 0.45 mA average at 5-min cadence.
- ESP active ≈ 30–50 mA for ~30 s per 5 min dominates.
- Expect ~1–3 months on a 2500 mAh cell; tune via `sleep_duration` / `run_duration`.

## Contingencies

- Broker host `homeassistant.local` resolves via mDNS from the ESP. On `MQTT
  disconnected` / DNS failure, substitute the hub IP in `mqtt.broker`.
- E-paper is B/W SSD1681 (confirmed). If the panel never initializes, set
  `reset_duration: 2ms` on the `waveshare_epaper` block (WeAct/Rev-2.1 timing).
- `gfonts://Roboto` needs network at first compile. Offline: drop a local `.ttf` into
  `firmware/co2-node/fonts/` and point `font.file` at it.
- Entity naming hinges on the `${friendly_name}` prefix in each sensor `name`. If HA
  surfaces `sensor.co2` (or floors collide), the substitution is not reaching the package
  — check the `!include` and that `friendly_name` is set per floor.
- Existing Pi publisher topics/`unique_id`s are not in this repo. Capture them at
  cutover (see plan Step 4); if the old publisher cannot be located, stopping the Pis
  and deleting the stale HA entities achieves the same clean names.
