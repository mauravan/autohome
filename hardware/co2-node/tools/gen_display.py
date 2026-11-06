#!/usr/bin/env python3
"""Display sheet: FPC-24 + WeAct boost transcribed 1:1 (3V3-fed, no ME6216).

Source: ../reference/weact-transcription.md (verified vs 300dpi renders).
Boost: L1 10uH, Q1 AO3402, D1-D3 B5819W, R1 100K, R2 3R, C12 100pF NC,
C8/C6 input/SW, C1+C2 VGL doubler, C7 VGH, C9 0.1u bulk, C10/C11 rails,
C13 VGH, C14 VGL. Series R3-R8 100R. E_BS hard-strapped 4-line SPI.
"""
import sys; sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.__str__())
from gen_common import *


def build_display():
    L = [sheet_head(f"CO2 node rev {REV} - {SHEETS['display'][1]}")]
    dx = 15.0
    # --- FPC connector
    fpins = [(str(i), n) for i, n in [
        (1, "GND"), (2, "E_VGL"), (3, "GND"), (4, "E_VGH"), (5, "GND"),
        (6, "GND"), (7, "EPD_P7"), (8, "EPD_P8"), (9, "EPD_P9"),
        (10, "EPD_P10"), (11, "EPD_SDA"), (12, "EPD_SCL"), (13, "EPD_CS"),
        (14, "EPD_DC"), (15, "EPD_RES"), (16, "EPD_BUSY"), (17, "E_BS"),
        (18, "GND"), (19, "GND"), (20, "EPD_P20"), (21, "GND"),
        (22, "E_RESR"), (23, "E_GDR"), (24, "GND")]]
    fpins += [("25", "GND"), ("26", "GND")]  # shell
    L += [sym("co2-node:FPC-24-0.5", "J2", "FPC-24-0.5mm",
              "co2-node:FPC-24-0.5", dx + 120, 45, fpins,
              "24-pin 0.5mm; contact side per WeAct J1 + panel drawing")]
    # series resistors MCU-side -> E_ nets
    series = [("R60", "EPD_SDA", "E_SDA_P", "11"), ("R61", "EPD_SCL", "E_SCL_P", "12"),
              ("R62", "EPD_CS", "E_CS_P", "13"), ("R63", "EPD_DC", "E_DC_P", "14"),
              ("R64", "EPD_RES", "E_RES_P", "15"), ("R65", "EPD_BUSY", "E_BUSY_P", "16")]
    for i, (ref, mcu_net, e_net, fpc) in enumerate(series):
        y = 30 + i * 6
        L += [sym("Device:R", ref, "100R", "co2-node:R_0402", dx + 95, y,
                  [("1", mcu_net), ("2", e_net)])]
        L += [lbl(mcu_net, dx + 88, y), lbl(e_net, dx + 102, y)]
    # E_BS hard strap: 4-line SPI -> E_BS to 3V3 via R9-equivalent 5.1k
    L += [sym("Device:R", "R66", "5.1k", "co2-node:R_0402", dx + 95, 68,
              [("1", "3V3"), ("2", "E_BS")])]
    L += [lbl("3V3", dx + 88, 68), lbl("E_BS", dx + 102, 68)]
    # E_GDR / E_RESR route to boost (labels bridge the sheet)
    L += [lbl("E_GDR", dx + 102, 74), lbl("E_RESR", dx + 102, 78)]
    # panel decoupling at FPC (0402, values from print)
    for i, (ref, val, net) in enumerate(
            [("C60", "1u", "EPD_P20"), ("C61", "0.1u", "VDD33F"),
             ("C62", "1u", "EPD_P8"), ("C63", "1u", "EPD_P7"),
             ("C64", "1u", "E_VGH"), ("C65", "1u", "E_VGL")]):
        L += [sym("Device:C", ref, val, "co2-node:C_0402", dx + 120,
                  70 + i * 5, [("1", net), ("2", "GND")])]
    L += [lbl("3V3", dx + 60, 30)]
    # bulk at boost input: >=10u + 0.1u (replaces omitted U1/C3-C5)
    L += [sym("Device:C", "C66", "10u", "co2-node:C_0603", dx + 40, 30,
              [("1", "3V3"), ("2", "GND")]),
          sym("Device:C", "C67", "0.1u", "co2-node:C_0402", dx + 48, 30,
              [("1", "3V3"), ("2", "GND")])]
    # --- boost core (left side). SW node shared.
    bx = dx + 40
    L += [sym("Device:L", "L1", "10uH", "co2-node:L_0603", bx, 45,
              [("1", "3V3"), ("2", "SW")]),
          sym("Device:C", "C68", "1u", "co2-node:C_0402", bx - 10, 45,
              [("1", "3V3"), ("2", "GND")])]  # C8
    L += [sym("co2-node:AO3402", "Q1", "AO3402", "co2-node:SOT-23-3",
              bx + 12, 55, [("1", "E_GDR"), ("2", "SW"), ("3", "Q1_S")],
              "NMOS: G=E_GDR D=SW S=sense node")]
    L += [sym("Device:R", "R1", "3R", "co2-node:R_0603", bx + 12, 68,
              [("1", "Q1_S"), ("2", "GND")]),
          sym("Device:R", "R2", "100K", "co2-node:R_0402", bx + 4, 68,
              [("1", "E_GDR"), ("2", "GND")]),
          sym("Device:C", "C69", "100p-NC", "co2-node:C_0402", bx + 20, 68,
              [("1", "Q1_S"), ("2", "")])]  # C12 DNP
    L += [nc(bx + 24, 68)]
    L += [lbl("E_RESR", bx + 12, 62), lbl("E_GDR", bx - 8, 55), lbl("SW", bx + 6, 49)]
    # charge pump: SW -D3-> E_VGH // C7; SW -C6-> M; SW -D2-> M; M -D1-> E_VGL
    L += [sym("Device:D", "D23", "B5819W", "co2-node:SOD-323", bx + 30, 45,
              [("1", "SW"), ("2", "E_VGH")]),
          sym("Device:C", "C70", "1u", "co2-node:C_0402", bx + 38, 45,
              [("1", "E_VGH"), ("2", "GND")])]  # C7
    L += [sym("Device:C", "C71", "1u", "co2-node:C_0402", bx + 30, 58,
              [("1", "SW"), ("2", "E_MID")])]  # C6
    L += [sym("Device:D", "D22", "B5819W", "co2-node:SOD-323", bx + 40, 58,
              [("1", "SW"), ("2", "E_MID")])]
    L += [sym("Device:D", "D21", "B5819W", "co2-node:SOD-323", bx + 40, 32,
              [("1", "E_MID"), ("2", "E_VGL")])]
    L += [sym("Device:C", "C72", "1u", "co2-node:C_0402", bx + 48, 32,
              [("1", "E_VGL"), ("2", "E_MID")])]  # C1 across VGL-M
    L += [lbl("E_VGH", bx + 48, 45), lbl("E_VGL", bx + 56, 32),
          lbl("E_MID", bx + 40, 63), gnd(bx + 38, 52), gnd(bx + 12, 74)]
    # VGH/VGL feed FPC via C13/C14 equivalents C64/C65 + direct labels
    L += [wire(bx + 48, 45, bx + 60, 45)]  # visual: E_VGH toward FPC side
    return L


def main():
    out = build_display()
    (HERE / "display.kicad_sch").write_text("\n".join(out) + "\n)\n")
    print(f"display: {len(chr(10).join(out))} bytes")


if __name__ == "__main__":
    main()
