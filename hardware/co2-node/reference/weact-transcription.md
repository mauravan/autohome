# WeAct EpaperModule SchDoc — audited transcription for `display`

Source: `WeAct-EpaperModule-SchDoc.pdf` (WeAct Studio, V1.0, 2022-08-06).
Dump: `WeAct-SchDoc-text.txt` is a machine dump; the netlist below was
**verified pixel-by-pixel against 300 dpi renders of the PDF**.

## Power in (module J2/P1 side)

- `U1` ME6216A33XG: VIN = VDD5V, VOUT = VDD33, GND.
- VIN side: `C4` 0.1 µF + `C5` 10 µF 0402 to GND.
- VDD33 side: `C3` 10 µF 0402 to GND.
- **Omitted on our board**: U1/C3/C4/C5. Boost + panel run from board 3V3.
  Our 3V3 rail needs the equivalent bulk: ≥10 µF + 0.1 µF at the boost input.

## Boost (charge-pump driver supply, SSD1681 gate/source rails)

Switch node **SW**: `L1` (10 µH) from VDD33 meets `Q1` drain, `D3` anode,
`C6` top plate at one dot.

- `L1` 10 µH: VDD33 → SW.
- `Q1` AO3402 NMOS (SOT23-3, gate = E_GDR): drain = SW, source = R2 top.
  Body-diode stripe ties source→drain (source dot at bottom wire = R2/C12/E_RESR).
- `R2` 3 Ω 0603: Q1 source → GND (current sense).
- `R1` 100 kΩ 0402: E_GDR node → GND (gate pull-down).
- `C12` 100 pF 0402 **NC/DNP** across Q1 source→GND (fitted "NC" in print).
- `E_RESR` net: joins Q1-source/R2-top node (low-side sense node =
  panel RESR current return). `E_GDR` drives the gate.
- `C8` 1 µF 0402: VDD33 → GND (input bulk at inductor).
- `C6` 1 µF 0402: SW → mid node M (= D2 anode, D1 cathode, C1 bottom).
- `D2` B5819W: SW → M (anode at SW dot, cathode at M).
- `D1` B5819W: M → E_VGL rail node (= C1 top; anode at M, cathode at E_VGL).
- `C1` 1 µF 0402: E_VGL rail → M.
- `D3` B5819W: SW → E_VGH (anode SW, cathode E_VGH).
- `C7` 1 µF 0402: E_VGH → GND.
- The M node has a single GND symbol directly under the D2–C1 junction in
  the print; D2 cathode/C1 bottom join M — the GND mark is the C1-bottom
  plate reference as drawn. Re-verify on the bench: E_VGL rail polarity
  before panel connect.
- Keep the SW loop (L1/Q1/D3/C7 and L1/D2-D1/C1) tight; away from
  antenna + sensor.

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
| 22 | E_RESR | low-side sense node |
| 23 | E_GDR | boost gate drive |

Panel-side decoupling (all 0402, VDD33↔GND unless noted):
`C2` 1 µF (PIN20 rail → GND), `C9` 0.1 µF bulk, `C10` 1 µF (PIN8),
`C11` 1 µF (PIN7), `C13` 1 µF (E_VGH PIN4), `C14` 1 µF (E_VGL PIN2).
FPC pins 1, 19, 21, 24, 18, 6, 5, 3: GND returns/shields per print.
Shell pins 25/26 → GND.

- `R3–R8`: 100 Ω 0402 in series on BUSY/RES/D-C/CS/SCL/SDA.
- `E_BS`: `R9` 5.1 kΩ + `SB1`/`SB2` solder jumpers select 3-line vs 4-line
  SPI. Our firmware uses 4-line SPI (DC pin driven) → strap E_BS for 4-line,
  hard-wired, no jumper.
- FPC `J1` land pattern and **contact side** must be copied exactly;
  confirm against a spare panel before layout (top/bottom contact).

## Module input connectors (reference only — not on our board)

- `J2` Wafer-1.25-8P: BUSY / RES / D-C / CS / SCL / SDA / GND / VDD5V —
  this is the signal set our firmware bit-bangs (minus power, which we gate).
- `P1` 2.54 header: RES / CS / SDA(+VDD5V/GND…) — bench only.
- Mounting: 4× M3 (`X1–X4`).
