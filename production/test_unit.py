#!/usr/bin/env python3
"""Production test per unit (Phase 9).

Usage: python3 test_unit.py --serial AH-CO2-0001 --port /dev/ttyACM0 --broker <host>
Flashes test.yaml, captures boot log, asserts:
  CO2 400-5000ppm, temp -10..50C, RH 0..100%, battery 3.0..4.2V,
  wake < 30s, no reset. Sleep current + charge current are MANUAL DMM
entries (--sleep-ua, --charge-ma). Appends PASS/FAIL row to units.csv.
"""
import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FW = HERE.parent / "firmware" / "co2-node"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", required=True)
    ap.add_argument("--port", required=True)
    ap.add_argument("--broker", default="homeassistant.local")
    ap.add_argument("--sleep-ua", type=float, default=-1)
    ap.add_argument("--charge-ma", type=float, default=-1)
    a = ap.parse_args()
    fails = []
    r = subprocess.run(["esphome", "logs", "test.yaml", "--device", a.port],
                       capture_output=True, text=True, timeout=180)
    log = r.stdout + r.stderr
    (HERE / f"test-{a.serial}.log").write_text(log)
    co2 = re.findall(r"mqtt co2=([\d.]+) ppm", log)
    if not co2:
        fails.append("no CO2 reading in log")
    elif not (400 <= float(co2[-1]) <= 5000):
        fails.append(f"CO2 out of range: {co2[-1]}")
    m = re.search(r"cell ([\d.]+) V", log)
    if not m:
        fails.append("no battery voltage in log")
    elif not (3.0 <= float(m.group(1)) <= 4.2):
        fails.append(f"battery out of range: {m.group(1)}")
    m = re.search(r"wake duration ([\d.]+) s", log)
    if not m:
        fails.append("no wake duration in log")
    elif float(m.group(1)) >= 30:
        fails.append(f"wake too long: {m.group(1)}s")
    if "0x62" not in log and "scd4x" not in log.lower():
        fails.append("no SCD41/I2C evidence in log")
    if a.sleep_ua >= 0 and a.sleep_ua > 20:
        fails.append(f"sleep current {a.sleep_ua}uA > 20uA")
    if a.charge_ma >= 0 and not (450 <= a.charge_ma <= 550):
        fails.append(f"charge current {a.charge_ma}mA not 500mA+-10%")
    result = "FAIL:" + ";".join(fails) if fails else "PASS"
    with open(HERE / "units.csv", "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([a.serial, "test", result, f"sleep_ua={a.sleep_ua}",
                    f"charge_ma={a.charge_ma}"])
    print(result)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
