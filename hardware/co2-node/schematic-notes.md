# Schematic notes — authoritative pad/pin transcriptions

All numbers below were read off the datasheet figures at 200–300 dpi.
The symbol pin tables in `tools/kicad/symbols.py` and the footprint pad
tables in `tools/gen_pcb.py` MUST match this file. Reviewer: diff the pad
coordinates against these figures before sign-off.

## SCD41-D-R2 (Sensirion SCD4x-Datasheet.pdf, 23 pp, Jan 2021)

Source: §2.3 Table 6 "Pin assignment (top view)" p.5 + Fig 4a land pattern
p.19 (pads 1–21 legible at 200 dpi in Table 6 figure; geometry from Fig 4a/b/c).

Table 6 (top view, notched membrane corner = pin 1 side):

| Pad(s) | Name | Notes |
|---|---|---|
| 6 | GND | ground |
| 7 | VDD | supply; tie to VDDH at sensor + 1 uF |
| 8 | DNC | floating pad, soldered, no copper pour |
| 9 | SCL | I2C clock, 10k pull-up to P3V3 |
| 10 | SDA | I2C data bidir, 10k pull-up to P3V3 |
| 19 | VDD | second VDD pad (same net) |
| 20 | GND | second GND pad (same net) |
| 21 (×4) | GND | large center thermal pad, 4.8×4.8 (solder paste c: 4× islands) |
| 1–5, 11–18 | DNC | floating pads, soldered, no net |

Fig 4a geometry (top view, mm): 21 landing pads in 3 columns;
edge pads 1.9×0.85 at 1.25 pitch; outer columns at x=±4.15, rows span
±2.5; top row (6–10) at y=+4.15, bottom row (16–20) at y=−4.15;
center pad 21 = 4.8×4.8. Package outline §4.1: 10.1×10.1, cap Ø8.5/7.8,
height 5.5, weight ~0.6 g. VDD+VDDH combined peak 205 mA @3.3 V.

Cross-check: installed `Sensor:Sensirion_SCD4x-1EP_10.1x10.1mm_P1.25mm_EP4.8x4.8mm`
has identical geometry (pads 1–21 + 4 paste islands); our custom footprint
copies its pad coordinates verbatim (verified by diff in Step 6).

## FS8205A (Fortune FS8205A-Datasheet.pdf Rev 1.2, p.3 §4 Pin Assignment)

TSSOP-8 top view, dual N-channel common-drain:

| Pin | Name |
|---|---|
| 1 | D12 (common drain) |
| 2 | S1 |
| 3 | S1 |
| 4 | G1 |
| 5 | G2 |
| 6 | S2 |
| 7 | S2 |
| 8 | D12 (common drain) |

Body per JEDEC MO-153 AA: D=2.93 (2.83–3.03), E1=4.40 (4.30–4.50) →
**4.4 mm body** → `Package_SO:TSSOP-8_4.4x3mm_P0.65mm`, e=0.65 BSC.
DW01A OD→G1, OC→G2. Sources S1 tie to GND, S2 tie to PACK−.

## ESP32-C3-MINI-1 (Espressif datasheet v2.2, §3.1 Table 3-1 p.11)

53 pins confirmed: GND = 1, 2, 11, 14, 36–53 (36–53 = center GND array);
3V3 = 3; NC = 4, 7, 9, 10, 15, 17, 24, 25, 28, 29, 32–35;
IO2 = 5, IO3 = 6, EN = 8, IO0 = 12, IO1 = 13, IO10 = 16, IO4 = 18,
IO5 = 19, IO6 = 20, IO7 = 21, IO8 = 22, IO9 = 23, IO18 = 26 (USB D−),
IO19 = 27 (USB D+), RXD0/GPIO20 = 30, TXD0/GPIO21 = 31.
Straps: GPIO2/8/9 (§4). Land pattern Fig 11-1: module 13.2×16.6 (±0.15),
48 edge pads 0.8×0.4 at 0.8 pitch + center 3×3 heatsink array 1.45² @1.975
+ corner GND 50–53. Cross-check `RF_Module:ESP32-C6-MINI-1` (same MINI-1
family): 62 pad records = 48 edge + 9× pad 49 + 50, 51, 52, 53 → 53 unique
numbers, identical coordinates; datasheet wins on conflict (none found).

## Keystone 1043 (Keystone catalog M65 p.27; source PDF saved during research)

1043 = THM leaf-spring single-18650: body 77.1×18.0; mounting 2× Ø3.45 +
2× Ø1.19; pad-layout span 86.0 MIN, refs 55.2 / 16.0 / 6.4 MIN / 7.3 MIN.
Because the drawing text layer is jumbled, pad coordinates below are the
values used in `tools/gen_pcb.py` — verify against the catalog figure:

THT pads (+): 2× Ø3.45 holes at (±27.6, 0) relative to holder center.
THT pads (−): 2× Ø1.19 holes at (±8.0, 0).
Courtyard: 86.0×24.0 centered. Mounting holes are plated and carry BAT+
and GND respectively (check continuity to springs on first article).

Fallback (not used): `Battery:Keystone_1042_1x18650` + 105×45 board.

## BQ24074 (TI SLUS810N §7 Figs 7-1/7-2 + RGT0016C dwg)

| Pin | Name | Pin | Name |
|---|---|---|---|
| 1 | TS | 9 | CHG |
| 2 | BAT | 10 | OUT |
| 3 | BAT | 11 | OUT |
| 4 | CE | 12 | ILIM |
| 5 | EN2 | 13 | IN |
| 6 | EN1 | 14 | TMR |
| 7 | PGOOD | 15 | ITERM |
| 8 | VSS | 16 | ISET |
| 17 | EP | (=VSS, tied to GND) | |

VQFN-16 3.0×3.0 (2.9–3.1): e=0.5, lead pad 0.24×0.6, EP ≈1.5–1.68 sq + vias.

## TPS7A2633 fixed (TI SBVS290B p.3, DRV0006A dwg p.29–31)

| Pin | Name |
|---|---|
| 1 | OUT |
| 2 | NC |
| 3 | PG |
| 4 | EN |
| 5 | GND |
| 6 | IN |
| 7 | EP (float/GND) |

WSON-6 2×2: e=0.65, lead pad ≈0.30×0.45, EP ≈1.0×1.6.

## DW01A (H&M Semi p.1 pin config)

1 OD, 2 VM (=CS net), 3 OC, 4 TD, 5 VCC, 6 GND. SOT-23-6 standard
2.9×1.6 body, e=0.95.

## USBLC6-2SC6 (ST p.1–2, 4)

1 I/O1, 2 GND, 3 I/O2, 4 I/O2, 5 Vcc, 6 I/O1. SOT-23-6L: D 2.82–3.02,
E1 2.65–2.95, E 1.5–1.7, e=0.95 BSC, e1 1.8–2.0, b 0.3–0.5, L 0.3–0.6.
