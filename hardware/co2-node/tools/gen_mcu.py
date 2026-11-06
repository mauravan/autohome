#!/usr/bin/env python3
"""MCU sheet: ESP32-C3-MINI-1-N4 + USB + BOOT/RESET + decoupling + test pads.

Module pins (datasheet §3.1): GND=1,2,11,14,36-53 3V3=3 IO2=5 IO3=6 EN=8
IO0=12 IO1=13 IO10=16 IO4=18 IO5=19 IO6=20 IO7=21 IO8=22 IO9=23 IO18=26
IO19=27 GPIO20=30 GPIO21=31. NC=4,7,9,10,15,17,24,25,28,29,32-35 (no-connect).
Strapping: GPIO2/8/9 — 10k pull-ups, no functions (README contract).
USB: D-/D+ = GPIO18/19 via 22R (power sheet) + USBLC6 (power sheet) + native CDC.
"""
import sys; sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.__str__())
from gen_common import *

X = 15.0


def build_mcu():
    L = [sheet_head(f"CO2 node rev {REV} - {SHEETS['mcu'][1]}")]
    mx = X + 60
    # Module: all 35 edge pins explicitly listed (53 = 35 edge + 18 GND pad)
    pins = [("1", "GND"), ("2", "GND"), ("3", "3V3"), ("4", ""), ("5", "STRAP2"),
            ("6", "VBAT_SENSE"), ("7", ""), ("8", "RESET_N"), ("9", ""),
            ("10", ""), ("11", "GND"), ("12", "EPD_RES"), ("13", "I2C_SDA"),
            ("14", "GND"), ("15", ""), ("16", "EPD_BUSY"), ("17", ""),
            ("18", "EPD_SCL"), ("19", "EPD_DC"), ("20", "EPD_SDA"),
            ("21", "EPD_CS"), ("22", "STRAP8"), ("23", "BOOT_N"),
            ("24", ""), ("25", ""), ("26", "USB_DM"), ("27", "USB_DP"),
            ("28", ""), ("29", ""), ("30", "PWR_EN"), ("31", "I2C_SCL"),
            ("32", ""), ("33", ""), ("34", ""), ("35", "")]
    L += [sym("co2-node:ESP32-C3-MINI-1", "U10", "ESP32-C3-MINI-1-N4",
              "co2-node:ESP32-C3-MINI-1", mx, 45, pins,
              "Espressif C3 MINI 4MB; antenna overhangs top edge")]
    for n in ("4", "7", "9", "10", "15", "17", "24", "25", "28",
              "29", "32", "33", "34", "35"):
        L += [nc(mx + 14, 20 + int(n))]
    # decoupling at 3V3 pin
    L += [sym("Device:C", "C40", "10u", "co2-node:C_0603", mx - 14, 62,
              [("1", "3V3"), ("2", "GND")]),
          sym("Device:C", "C41", "1u", "co2-node:C_0603", mx - 8, 62,
              [("1", "3V3"), ("2", "GND")]),
          sym("Device:C", "C42", "0.1u", "co2-node:C_0603", mx - 2, 62,
              [("1", "3V3"), ("2", "GND")])]
    # EN: 10k pull-up + 100nF (RESET_N button to GND on connectors sheet)
    L += [sym("Device:R", "R40", "10k", "co2-node:R_0603", mx - 20, 30,
              [("1", "3V3"), ("2", "RESET_N")]),
          sym("Device:C", "C43", "100n", "co2-node:C_0603", mx - 14, 30,
              [("1", "RESET_N"), ("2", "GND")])]
    # BOOT: 10k pull-up (button to GND on connectors sheet)
    L += [sym("Device:R", "R41", "10k", "co2-node:R_0603", mx + 20, 30,
              [("1", "3V3"), ("2", "BOOT_N")])]
    # Strapping GPIO2/GPIO8: 10k pull-ups, no functions
    L += [sym("Device:R", "R42", "10k", "co2-node:R_0603", mx + 28, 52,
              [("1", "3V3"), ("2", "STRAP2")]),
          sym("Device:R", "R43", "10k", "co2-node:R_0603", mx + 28, 58,
              [("1", "3V3"), ("2", "STRAP8")])]
    # PWR_EN 100k pull-down is on the power sheet (Q4 gate); label here
    L += [lbl("3V3", mx - 14, 45), lbl("PWR_EN", mx + 14, 45),
          lbl("I2C_SDA", mx - 14, 38), lbl("I2C_SCL", mx + 14, 38),
          lbl("EPD_SDA", mx + 14, 50), lbl("EPD_SCL", mx + 14, 55),
          lbl("EPD_CS", mx + 14, 60), lbl("EPD_DC", mx + 14, 65),
          lbl("EPD_RES", mx - 14, 50), lbl("EPD_BUSY", mx - 14, 55),
          lbl("VBAT_SENSE", mx - 14, 62), lbl("USB_DM", mx + 14, 30),
          lbl("USB_DP", mx + 14, 33), lbl("BOOT_N", mx + 20, 26),
          lbl("RESET_N", mx - 20, 26), lbl("STRAP2", mx + 28, 48),
          lbl("STRAP8", mx + 28, 62)]
    L += [gnd(mx - 8, 70), gnd(mx + 20, 38)]
    return L


def main():
    out = build_mcu()
    (HERE / "mcu.kicad_sch").write_text("\n".join(out) + "\n)\n")
    print(f"mcu: {len(chr(10).join(out))} bytes")


if __name__ == "__main__":
    main()
