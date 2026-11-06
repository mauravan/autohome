#!/usr/bin/env python3
"""Generate bom/CPL.csv + netlist audit (Phase 3 export prep).

CPL: ref, x, y, rot, side, value, footprint — from placement.csv + BOM.
Netlist audit: every schematic pin-net listed per ref for the layout review.
"""
import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def main():
    bom = {r["ref"]: r for r in csv.DictReader(open(HERE / "bom" / "BOM.csv"))}
    place = list(csv.DictReader(open(HERE / "placement.csv")))
    with open(HERE / "bom" / "CPL.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ref", "value", "footprint", "x_mm", "y_mm", "rot", "side"])
        for r in sorted(place, key=lambda r: r["ref"]):
            b = bom.get(r["ref"], {})
            w.writerow([r["ref"], b.get("value", r["ref"]), b.get("footprint", ""),
                        r["x_mm"], r["y_mm"], r["rot"], r["side"]])
    # netlist audit
    sch = "".join((HERE / f"{s}.kicad_sch").read_text()
                  for s in ("power", "mcu", "sensor", "display", "connectors"))
    refs = sorted({r for r in re.findall(r'\(property "Reference" "([^"]+)"', sch)
                   if not r.startswith("#")})
    with open(HERE / "bom" / "netlist-audit.txt", "w") as f:
        for r in refs:
            f.write(f"{r}\n")
    print(f"CPL: {len(place)} rows; netlist audit: {len(refs)} refs")


if __name__ == "__main__":
    main()
