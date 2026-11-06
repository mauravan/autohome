#!/usr/bin/env python3
"""DRC-lite: structural layout audit (not a KiCad substitute).

Checks over placement.csv + co2-node.kicad_pcb:
  D1 board outline 95x45 present, all footprints inside.
  D2 antenna keepout: no footprint center inside x[70,86.5] y[30,46]
      except U10 (module itself).
  D3 holder top edge: BT1 y extent (14..26) below keepout bottom (30).
  D4 SCD41 position: bottom-front edge region (x<35, y<12).
  D5 sensor distance: SCD41 >= 25mm from U1/U2/L1/Q1.
  D6 test pads y<=5 (front/bottom, clear of holder y14..26).
  D7 overlap: center-to-center >= 2.5mm for all pairs (except DNC-PAD/IC-SCD).
  D8 USB-C at bottom edge (y<=4).
  D9 FPC top-left quadrant (x<35, y>30).
  D10 netlist continuity: every schematic pin-net appears in NETS table.
  D11 AISLER rules note: 0603/0402 geometries respected (by construction).

Usage: python3 tools/drc_lite.py -> exit 0 pass / 1 fail
"""
import csv
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

KEEP = (70.0, 86.5, 30.0, 46.0)


def main():
    fails = []
    rows = {r["ref"]: (float(r["x_mm"]), float(r["y_mm"]))
            for r in csv.DictReader(open(HERE / "placement.csv"))}
    pcb = (HERE / "co2-node.kicad_pcb").read_text()
    if pcb.count("(") != pcb.count(")"):
        fails.append("D0 pcb s-expr unbalanced")
    if "(gr_rect (start 0 0) (end 95 45)" not in pcb:
        fails.append("D1 board outline 95x45 missing")
    for ref, (x, y) in rows.items():
        if not (0 <= x <= 95 and 0 <= y <= 45):
            fails.append(f"D1 {ref} outside board ({x},{y})")
    # D2 keepout
    for ref, (x, y) in rows.items():
        if ref == "U10":
            continue
        if KEEP[0] <= x <= KEEP[1] and KEEP[2] <= y <= KEEP[3]:
            fails.append(f"D2 {ref} inside antenna keepout ({x},{y})")
    # D3 holder
    bx, by = rows["BT1"]
    if by + 6 > KEEP[2]:
        fails.append(f"D3 holder top edge {by + 6} >= keepout {KEEP[2]}")
    # D4 sensor
    sx, sy = rows["IC-SCD"]
    if not (sx < 35 and sy < 12):
        fails.append(f"D4 SCD41 not bottom-front ({sx},{sy})")
    # D5 distances
    for other in ("U1", "U2", "L1", "Q1"):
        ox, oy = rows[other]
        d = math.hypot(sx - ox, sy - oy)
        if d < 25:
            fails.append(f"D5 SCD41-{other} only {d:.1f}mm (<25)")
    # D6 test pads
    for i in range(1, 9):
        _, py = rows[f"TP{i}"]
        if py > 5:
            fails.append(f"D6 TP{i} y={py} not at bottom edge")
    # D7 overlap
    refs = list(rows)
    for a in range(len(refs)):
        for b in range(a + 1, len(refs)):
            ra, rb = refs[a], refs[b]
            if {ra, rb} == {"IC-SCD", "DNC-PAD"}:
                continue
            xa, ya = rows[ra]
            xb, yb = rows[rb]
            if math.hypot(xa - xb, ya - yb) < 2.5:
                fails.append(f"D7 overlap {ra}-{rb} "
                             f"({math.hypot(xa-xb, ya-yb):.2f}mm)")
    # D8 USB
    if rows["J1"][1] > 4:
        fails.append("D8 USB-C not at bottom edge")
    # D9 FPC
    fx, fy = rows["J2"]
    if not (fx < 35 and fy > 30):
        fails.append(f"D9 FPC not top-left ({fx},{fy})")
    # D10 nets
    import sys as _s
    _s.path.insert(0, str(HERE / "tools"))
    from gen_common import NETS
    sch = "".join((HERE / f"{s}.kicad_sch").read_text()
                  for s in ("power", "mcu", "sensor", "display", "connectors"))
    pinnets = {n for _, n in re.findall(r'\(pin "([^":]+):([^"]*)"', sch)
                    if n}
    labels = set(re.findall(r'\(label "([^"]+)"', sch))
    missing = (pinnets | labels) - set(NETS) - {""}
    if missing:
        fails.append(f"D10 nets missing from PCB table: {sorted(missing)}")
    if fails:
        print(f"DRC-lite FAIL ({len(fails)}):")
        for f in fails[:30]:
            print("  -", f)
        return 1
    print(f"DRC-lite PASS: {len(rows)} footprints, keepout/thermal/nets clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
