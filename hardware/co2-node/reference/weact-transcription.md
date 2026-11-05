# WeAct EpaperModule SchDoc — audited transcription for `display`

Source: `WeAct-EpaperModule-SchDoc.pdf` (WeAct Studio, V1.0, 2022-08-06).
Dump: `WeAct-SchDoc-text.txt`. Checked against the PDF text layer;
**re-verify visually against the PDF before layout sign-off.**

## Power in (module J2/P1 side)

- `U1` ME6216A33XG: VIN = VDD5V, VOUT = VDD33, GND.
- VIN side: `C3` 10 µF 0402 to GND.
- VDD33 side: `C4` 0.1 µF + `C5` 10 µF 0402 to GND.
- **Omitted on our board**: U1/C3/C4/C5. Boost + panel run from board 3V3.
  Our 3V3 rail needs the equivalent bulk: ≥10 µF + 0.1 µF at the boost input.

## Boost (charge-pump driver supply, SSD1681 gate/source rails)

- `L1` 10 µH, `Q1` AO3402 (SOT23-3, gate = E_GDR),
  `D1/D2/D3` B5819W (SOD-323), `R1` 100 kΩ 0402, `R2` 3 Ω 0603,
  `C12` 100 pF NC (DNP).
- Bulk/output: `C1` 1 µF, `C2` 1 µF, `C6` 1 µF, `C7` 1 µF (VDD33),
  `C8` 1 µF (E_RESR), `C9` 0.1 µF (GND), `C10/C11` 1 µF,
  `C13` 1 µF (E_VGH), `C14` 1 µF (E_VGL). All 0402.
- Topology: standard SSD1681 boost (GDR-driven inductor, diode-capacitor
  multiplier to VGH/VGL/VSH/VSL rails). Copy nets exactly from the PDF;
  keep the switching loop tight and away from antenna + sensor.

## Panel connector J1 (FPC 0.5 mm, 24-pin, panel side)

E-paper signals from FPC (our net → series R → FPC):

| FPC | Net | Note |
|---|---|---|
| 2 | E_VGL | via C14 |
| 4 | E_VGH | via C13 |
| 11 | E_SDA | via R8 100 Ω |
| 12 | E_SCL | via R7 100 Ω |
| 13 | E_CS | via R6 100 Ω |
| 14 | E_D/C | via R5 100 Ω |
| 15 | E_RES | via R4 100 Ω |
| 16 | E_BUSY | via R3 100 Ω |
| 17 | E_BS | strapped for 4-line SPI (see below) |
| 22 | E_RESR | via C8 |
| 23 | E_GDR | boost drive |

- `R3–R8`: 100 Ω 0402 in series on BUSY/RES/D-C/CS/SCL/SDA.
- `E_BS`: `R9` + `SB1`/`SB2` solder jumpers select 3-line vs 4-line SPI.
  Our firmware uses 4-line SPI (DC pin driven) → strap E_BS for 4-line,
  hard-wired, no jumper.
- FPC `J1` land pattern and **contact side** must be copied exactly;
  confirm against a spare panel before layout (top/bottom contact).

## Module input connectors (reference only — not on our board)

- `J2` Wafer-1.25-8P: BUSY / RES / D-C / CS / SCL / SDA / GND / VDD5V —
  this is the signal set our firmware bit-bangs (minus power, which we gate).
- `P1` 2.54 header: RES / CS / SDA(+VDD5V/GND…) — bench only.
- Mounting: 4× M3 (`X1–X4`).
