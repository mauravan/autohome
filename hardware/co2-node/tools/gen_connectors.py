#!/usr/bin/env python3
"""Connectors sheet: holder, NTC, buttons, test pads, mounting, label ref.

BT1/NTC live on power sheet as electrical parts; this sheet carries the
mechanical holder symbol + NTC placement note + BOOT/RESET buttons +
8 test pads (3V3 GND BAT P3V3 EN GPIO9 SCL PWR_EN) + mounting holes.
"""
import sys; sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.__str__())
from gen_common import *


def build_connectors():
    L = [sheet_head(f"CO2 node rev {REV} - {SHEETS['connectors'][1]}")]
    cx = 30.0
    # holder mechanical (electrical BT1 on power sheet shown as linked ref)
    L += [lbl("CELL+", cx - 12, 40)]
    L += [txt("BT1 holder electrical part is on the power sheet.", cx - 12, 34),
          txt("Placement: back side, top edge y=15mm.", cx - 12, 48)]
    # NTC adjacent to cell -> TS net (electrical on power sheet TS pin)
    L += [sym("Device:R_NTC", "RT1", "10k-B3950", "co2-node:R_0603",
              cx + 25, 40, [("1", "TS_NTC"), ("2", "GND")],
              "NTC at cell; BQ24074 TS: 75uA bias")]
    L += [lbl("TS_NTC", cx + 25, 34)]
    # BOOT / RESET tactile buttons to GND
    L += [sym("co2-node:SW_TACT", "SW1", "BOOT", "co2-node:SW-3x4",
              cx + 50, 35, [("1", "BOOT_N"), ("2", "GND")],
              "BOOT pinhole in case")]
    L += [sym("co2-node:SW_TACT", "SW2", "RESET", "co2-node:SW-3x4",
              cx + 50, 50, [("1", "RESET_N"), ("2", "GND")],
              "RESET pinhole in case")]
    L += [lbl("BOOT_N", cx + 42, 35), lbl("RESET_N", cx + 42, 50)]
    # charge LED is D20 on power sheet; light-pipe note
    # test pads 1.0mm: 3V3 GND BAT P3V3 EN GPIO9 SCL PWR_EN
    pads = [("TP1", "3V3"), ("TP2", "GND"), ("TP3", "BAT+"),
            ("TP4", "P3V3"), ("TP5", "RESET_N"), ("TP6", "BOOT_N"),
            ("TP7", "I2C_SCL"), ("TP8", "PWR_EN")]
    # NOTE: plan says EN + GPIO9; RESET_N == EN net, BOOT_N == GPIO9 net.
    for i, (ref, net) in enumerate(pads):
        L += [sym("co2-node:TESTPAD", ref, net, "co2-node:TP-1.0mm",
                  cx + 75 + (i % 4) * 12, 32 + (i // 4) * 12,
                  [("1", net)], f"pogo 1.0mm; front/bottom clear of holder")]
        L += [lbl(net, cx + 75 + (i % 4) * 12, 26 + (i // 4) * 12)]
    # mounting holes + label ref
    for i, (ref, mx_, my_) in enumerate(
            [("H1", 3.5, 3.5), ("H2", 91.5, 3.5),
             ("H3", 3.5, 41.5), ("H4", 91.5, 41.5)]):
        L += [sym("co2-node:MOUNT_M2.5", ref, "M2.5",
                  "co2-node:MOUNT-2.5", cx + 110 + (i % 2) * 12,
                  30 + (i // 2) * 12, [("1", "GND")],
                  f"board hole ({mx_},{my_}mm); standoff")]
    L += [sym("co2-node:LABEL", "LBL1", "AH-CO2-1",
              "co2-node:LABEL-70x30", cx + 110, 60, [],
              "70x30 back label; no metal over antenna")]
    L += [gnd(cx + 25, 48), gnd(cx + 50, 42)]
    return L


def main():
    out = build_connectors()
    (HERE / "connectors.kicad_sch").write_text("\n".join(out) + "\n)\n")
    print(f"connectors: {len(chr(10).join(out))} bytes")


if __name__ == "__main__":
    main()
