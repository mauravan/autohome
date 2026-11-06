#!/usr/bin/env python3
"""Sensor sheet: SCD41-D-R2 bare LGA + ferrite + pull-ups + DNC float.

Datasheet §2.3/§4.2: pads VDD VDDH GND SDA SCL DNC. VDD+VDDH tied at sensor
+ 1uF; DNC soldered to FLOATING pad (never GND); no SEL pin; 10k pull-ups
to P3V3; ferrite bead + 10uF from P3V3 to SCD_VDD; no copper pour under body.
"""
import sys; sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.__str__())
from gen_common import *


def build_sensor():
    L = [sheet_head(f"CO2 node rev {REV} - {SHEETS['sensor'][1]}")]
    sx = 60.0
    L += [sym("co2-node:SCD41-D-R2", "IC-SCD", "SCD41-D-R2",
              "co2-node:SCD41-LGA", sx, 45,
              [("VDD", "SCD_VDD"), ("VDDH", "SCD_VDD"), ("GND", "GND"),
               ("SDA", "I2C_SDA"), ("SCL", "I2C_SCL"),
               ("DNC1", "DNC_A"), ("DNC2", "DNC_A")],
              "Sensirion SCD41-D-R2 MSL3; VDD+VDDH tied; DNC floating pad")]
    L += [lbl("SCD_VDD", sx - 14, 38), lbl("I2C_SDA", sx - 14, 48),
          lbl("I2C_SCL", sx + 14, 48), lbl("DNC_A", sx + 14, 58)]
    # floating DNC pad: copper island, no net (flagged no-connect x2)
    L += [sym("co2-node:PAD_FLOAT", "DNC-PAD", "DNC-float",
              "co2-node:SCD41-DNC", sx + 30, 58,
              [("1", "DNC_A"), ("2", "")])]
    L += [nc(sx + 36, 58)]
    # VDD+VDDH tied + 1uF at sensor
    L += [sym("Device:C", "C50", "1u", "co2-node:C_0603", sx, 60,
              [("1", "SCD_VDD"), ("2", "GND")])]
    # ferrite + 10uF from P3V3
    L += [sym("co2-node:FERRITE", "FB50", "600R@100MHz",
              "co2-node:L_0603", sx - 20, 38,
              [("1", "P3V3"), ("2", "SCD_VDD")]),
          sym("Device:C", "C51", "10u", "co2-node:C_0603", sx - 28, 38,
              [("1", "P3V3"), ("2", "GND")])]
    # 10k pull-ups to P3V3 (NOT 3V3: no back-power when gate off)
    L += [sym("Device:R", "R50", "10k", "co2-node:R_0603", sx - 10, 52,
              [("1", "P3V3"), ("2", "I2C_SDA")]),
          sym("Device:R", "R51", "10k", "co2-node:R_0603", sx + 10, 52,
              [("1", "P3V3"), ("2", "I2C_SCL")])]
    L += [lbl("P3V3", sx - 20, 32), lbl("GND", sx, 68), gnd(sx, 68)]
    return L


def main():
    out = build_sensor()
    (HERE / "sensor.kicad_sch").write_text("\n".join(out) + "\n)\n")
    print(f"sensor: {len(chr(10).join(out))} bytes")


if __name__ == "__main__":
    main()
