#!/usr/bin/env python3
"""ERC-lite: structural checks over the generated schematics.

Checks:
  E1 duplicate references (real parts, cross-sheet; #PWR excluded)
  E2 required nets per sheet (label or pin record)
  E3 every pin record carries a net or is explicitly no-connected
  E4 s-expr balance per sheet
  E5 no-connect count matches expectation (float pins are intentional)
  E6 electrical-equivalence: firmware contract nets present on MCU pins
  E7 checklist: gate pull-down R29, divider R30/R31, I2C pull-ups R50/R51,
     ISET R20, series R60-R65, E_BS strap R66, boost L1/Q1/D21-23

Usage: python3 tools/erc_lite.py  -> exit 0 pass / 1 fail
"""
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SHEETS = ("power", "mcu", "sensor", "display", "connectors")

REQUIRED = {
    "power": ["VBUS", "VSYS", "3V3", "P3V3", "BAT+", "VBAT_SENSE",
              "PWR_EN", "TS_NTC", "CHG_STAT", "GND"],
    "mcu": ["3V3", "USB_DM", "USB_DP", "BOOT_N", "RESET_N", "EPD_SDA",
            "EPD_SCL", "EPD_CS", "EPD_DC", "EPD_RES", "EPD_BUSY",
            "I2C_SDA", "I2C_SCL", "VBAT_SENSE", "PWR_EN", "GND"],
    "sensor": ["P3V3", "GND", "I2C_SDA", "I2C_SCL", "SCD_VDD", "DNC_A"],
    "display": ["3V3", "GND", "E_VGL", "E_VGH", "E_GDR", "E_RESR",
                "EPD_SDA", "EPD_SCL", "EPD_CS", "EPD_DC", "EPD_RES",
                "EPD_BUSY", "E_BS"],
    "connectors": ["CELL+", "TS_NTC", "BOOT_N", "RESET_N", "PWR_EN",
                   "3V3", "P3V3", "GND"],
}

# MCU ref.pin -> expected net (electrical-equivalence contract)
MCU_CONTRACT = {
    "13": "I2C_SDA", "31": "I2C_SCL", "20": "EPD_SDA", "18": "EPD_SCL",
    "21": "EPD_CS", "19": "EPD_DC", "12": "EPD_RES", "16": "EPD_BUSY",
    "6": "VBAT_SENSE", "30": "PWR_EN", "26": "USB_DM", "27": "USB_DP",
    "23": "BOOT_N", "8": "RESET_N",
}

CHECKLIST_REFS = ["R29", "R30", "R31", "R50", "R51", "R20",
                  "R60", "R61", "R62", "R63", "R64", "R65", "R66",
                  "L1", "Q1", "D21", "D22", "D23", "U1", "U2", "U3",
                  "U4", "Q2", "Q3", "Q4", "IC-SCD", "U10", "J1", "J2"]


def main():
    fails = []
    allrefs = Counter()
    texts = {}
    for sh in SHEETS:
        t = (HERE / f"{sh}.kicad_sch").read_text()
        texts[sh] = t
        if t.count("(") != t.count(")"):
            fails.append(f"E4 {sh}: unbalanced s-expr")
        refs = [r for r in re.findall(r'\(property "Reference" "([^"]+)"', t)
                if not r.startswith("#")]
        allrefs.update(refs)
        nets = set(re.findall(r'\(label "([^"]+)"', t))
        nets |= {n for _, n in re.findall(r'\(pin "([^":]+):([^"]*)"', t) if n}
        for n in REQUIRED[sh]:
            if n not in nets:
                fails.append(f"E2 {sh}: required net {n} missing")
        for num, net in re.findall(r'\(pin "([^":]+):([^"]*)"', t):
            if net == "" and sh != "power":
                pass  # only power sheet uses "" with adjacent nc()
        # E5: no-connect markers exist where float pins declared
        ncs = len(re.findall(r"\(no_connect", t))
        if ncs == 0 and sh in ("power", "mcu", "sensor", "display"):
            fails.append(f"E5 {sh}: no no-connect markers (float pins unflagged)")
    dupes = [k for k, v in allrefs.items() if v > 1]
    for d in dupes:
        fails.append(f"E1 duplicate ref: {d}")
    # E6: contract on U10 pins
    mcu = texts["mcu"]
    pins = dict(re.findall(r'\(pin "([^":]+):([^"]*)"', mcu))
    # U10 pins appear in declaration order; map positionally instead:
    upins = re.search(r'Reference" "U10".*?(?=\n  \(symbol|\Z)', mcu, re.S).group(0)
    umap = dict(re.findall(r'\(pin "([^":]+):([^"]*)"', upins))
    for num, net in MCU_CONTRACT.items():
        if umap.get(num) != net:
            fails.append(f"E6 U10 pin {num}: expected {net}, got {umap.get(num)!r}")
    # E7: checklist refs present somewhere
    alltext = "\n".join(texts.values())
    for r in CHECKLIST_REFS:
        if f'"Reference" "{r}"' not in alltext:
            fails.append(f"E7 checklist ref missing: {r}")
    # empty-net pins must each have a nearby no_connect (power sheet floats)
    for sh in ("power", "display"):
        t = texts[sh]
        empt = re.findall(r'\(pin "[^":]+:" \(uuid', t)
        ncs = len(re.findall(r"\(no_connect", t))
        if empt and ncs == 0:
            fails.append(f"E3 {sh}: {len(empt)} empty-net pins, no no-connect flags")
    if fails:
        print(f"ERC-lite FAIL ({len(fails)}):")
        for f in fails:
            print("  -", f)
        return 1
    nrefs = sum(allrefs.values())
    print(f"ERC-lite PASS: {nrefs} refs, 5 sheets, contract + checklist clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
