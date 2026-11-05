# CO2 sensor node — custom production board (rev A)

2-layer, 95 × 45 mm, 1.6 mm, ENIG. No development components.
KiCad 9 project: open `co2-node.kicad_pro`. Regenerate with
`python3 tools/gen_kicad.py` — never hand-edit generated files.

## Electrical-equivalence rule (binding)

This board MUST reproduce the dev wiring in
`firmware/co2-node/README.md` with identical pin functions and polarities.
Any change to the table below is a **rev B**: firmware and layout both
depend on it.

## Frozen pin map (rev A)

| Signal | ESP32-C3-MINI-1 pin | Net | Firmware reference |
|---|---|---|---|
| SCD41 SDA | GPIO1 | `I2C_SDA` | `i2c.sda` |
| SCD41 SCL | GPIO21 | `I2C_SCL` | `i2c.scl` |
| EPD MOSI | GPIO6 | `EPD_SDA` | `spi.mosi_pin` |
| EPD SCK | GPIO4 | `EPD_SCL` | `spi.clk_pin` |
| EPD CS | GPIO7 | `EPD_CS` | `cs_pin` |
| EPD DC | GPIO5 | `EPD_DC` | `dc_pin` |
| EPD RST | GPIO0 | `EPD_RES` | `reset_pin` |
| EPD BUSY | GPIO10 | `EPD_BUSY` | `busy_pin` |
| Battery sense | GPIO3 (ADC1_CH3) | `VBAT_SENSE` | `adc.pin`, `multiply: 2.0` |
| Peripheral power | GPIO20 | `PWR_EN` | `switch.gpio`, HIGH = P3V3 on |
| USB D− / D+ | GPIO18 / GPIO19 | `USB_DM` / `USB_DP` | native USB CDC |
| BOOT | GPIO9 | `BOOT_N` | button to GND, 10k pull-up |
| Reset | EN | `RESET_N` | button to GND, 10k pull-up + 100 nF |

- GPIO2/GPIO8: strapping, 10k pull-ups, no functions.
- GPIO20/21 are UART0 pins; ROM boot chatter is harmless. Logger stays on
  native USB (GPIO18/19). No UART header.
- Power gate is **active-high** with a 100k pull-down on GPIO20 so P3V3 is
  off during deep sleep. Firmware re-asserts HIGH + 1 s settle every wake.
- Battery divider is **VBAT/2** (1 M/1 M) so `multiply: 2.0` and the SoC
  table in `co2-node-common.yaml` stay valid.

## Sheets

| Sheet | Content |
|---|---|
| `power` | USB-C → 0.75 A polyfuse → USBLC6 → BQ24074 (500 mA) → VSYS; holder → 2 A polyfuse → Q2 reverse P-FET → DW01A/FS8205A → BAT+; VSYS → TPS7A26 → 3V3; 3V3 → Q3/Q4 gate → P3V3; BAT+ → 1 M/1 M → 100 nF → 1 k → GPIO3 |
| `mcu` | ESP32-C3-MINI-1-N4, 10 µF + 1 µF + 0.1 µF, EN pull-up/cap, BOOT/RESET buttons, USB 22 Ω + ESD, test pads, fiducials |
| `sensor` | SCD41-D-R2, VDD/VDDH tied, DNC floating pad, 10k pull-ups to P3V3, ferrite + 10 µF, 1 µF at sensor, no pour under body |
| `display` | FPC-24 0.5 mm + WeAct boost transcribed from `reference/` (3V3-fed, no ME6216A33), 100 Ω series, E_BS = 4-line SPI |
| `connectors` | 18650 holder, NTC, test pads, mounting holes, label ref |

## Copy-critical references (`reference/`)

- `WeAct-EpaperModule-SchDoc.pdf` — the boost + connector block is copied,
  not redrawn from memory. `WeAct-SchDoc-text.txt` is a machine dump;
  `weact-transcription.md` is the audited netlist used for `display`.
- `SCD4x-Datasheet.pdf` — §2.3/§4.2 land pattern: pads VDD, VDDH, GND, SDA,
  SCL, DNC. VDD+VDDH tied at sensor + 1 µF; DNC soldered to a **floating**
  pad (never GND); no SEL pin; 10k pull-ups to P3V3; low-noise rail
  (ferrite + 10 µF).
- `ESP32-C3-MINI-1-Datasheet.pdf` — module pin numbers (§3.1), strapping
  (GPIO2/8/9), 15 mm antenna keepout (§11).
- `WeAct-SSD1681-Datasheet.pdf` — controller init reference.

## Layout constraints

- AISLER 2-layer rules: 0.2 mm min trace/space, 0.3 mm min drill,
  0.6 mm min via pad.
- Antenna overhangs the top edge; no copper/battery/metal within 15 mm,
  both layers; plastic case only.
- SCD41 at bottom-front edge by the vent grille; no copper pour under body;
  charger/LDO/boost away from sensor; cell holder top edge at y = 15 mm.
- Test pads on front side / bottom edge, clear of the holder for the pogo
  fixture. `3V3 GND BAT P3V3 EN GPIO9 SCL PWR_EN`, 1.0 mm, + 3 fiducials.
