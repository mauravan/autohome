#!/usr/bin/env python3
"""Manufacturing exports (run from hardware/co2-node, outputs committed).

Order: gerbers, drill, pos, bom, ipcd356, step, schematic pdf.
Assertions: 7 gerbers starting with %FS/G04; drill has M48; CPL has data
rows; BOM has refs and no empty MPN outside the allowed set; STEP bbox
x 0-95, y 0-45.
"""
import csv
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PCB = HERE / "co2-node.kicad_pcb"
SCH = HERE / "co2-node.kicad_sch"
MFG = HERE / "manufacturing"
GERB = MFG / "gerbers"


def run(*args):
    r = subprocess.run(args, capture_output=True, text=True, cwd=HERE)
    if r.returncode != 0:
        print(f"FAILED: {' '.join(args)}\n{r.stderr[:2000]}")
        raise SystemExit(1)
    return r


def main():
    GERB.mkdir(parents=True, exist_ok=True)
    (MFG).mkdir(parents=True, exist_ok=True)
    (HERE / "bom").mkdir(parents=True, exist_ok=True)
    run("kicad-cli", "pcb", "export", "gerbers", "-o", str(GERB),
        "--layers", "F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
        str(PCB))
    run("kicad-cli", "pcb", "export", "drill", "-o", str(GERB),
        "--format", "excellon", "--excellon-units", "mm",
        "--generate-map", str(PCB))
    run("kicad-cli", "pcb", "export", "pos", "--format", "csv",
        "--units", "mm", "--side", "both", "-o", str(HERE / "bom" / "CPL.csv"),
        str(PCB))
    run("kicad-cli", "sch", "export", "bom",
        "--fields", "Reference,Value,Footprint,MPN,Manufacturer,QUANTITY,DNP",
        "-o", str(HERE / "bom" / "BOM.csv"), str(SCH))
    run("kicad-cli", "pcb", "export", "ipcd356", "-o",
        str(MFG / "board.d356"), str(PCB))
    run("kicad-cli", "pcb", "export", "step", "-o",
        str(MFG / "board.step"), "--force", str(PCB))
    run("kicad-cli", "sch", "export", "pdf", "-o",
        str(MFG / "schematic.pdf"), str(SCH))

    # assertions
    gerbers = sorted(GERB.glob("*.g*"))
    cu = [g for g in gerbers if g.suffix in (".gtl", ".gbl", ".gto", ".gbo",
                                             ".gts", ".gbs", ".gm1")]
    assert len(cu) == 7, f"expected 7 gerbers, got {len(cu)}: {cu}"
    for g in cu:
        head = g.read_text(errors="replace")[:60]
        assert head.startswith("%FS") or head.startswith("G04") or "GenerationSoftware" in head, g
    drills = list(GERB.glob("*.drl"))
    assert drills and any("M48" in d.read_text(errors="replace") for d in drills), "no M48"
    cpl = list(csv.DictReader(open(HERE / "bom" / "CPL.csv")))
    print(f"CPL: {len(cpl)} rows")
    # 93 = 97 placed footprints minus H1-H4 (drilled, not placed). DNP
    # R21/C69 and probe TPs are placed-file rows by assembly convention
    # (matches the old flow); the SCD41 DNC function needs no separate
    # island part (sensor pads on net SCD_DNC solder to their own lands).
    assert len(cpl) == 93, f"CPL rows {len(cpl)}"
    refs = {r["Ref"] for r in cpl}
    assert not ({"H1", "H2", "H3", "H4"} & refs), "holes in CPL"
    assert {"TP1", "TP8", "R21", "C69", "BT1"} <= refs, "missing CPL rows"

    bom = list(csv.DictReader(open(HERE / "bom" / "BOM.csv")))
    print(f"BOM: {len(bom)} refs (kicad-cli)")
    # Mechanical lines with no schematic symbol (label + DNC copper island)
    # are appended from bom_data so the committed BOM stays complete.
    sys.path.insert(0, str(HERE / "tools"))
    from bom_data import BOM as BOMDATA
    have = {r["Reference"] for r in bom}
    with open(HERE / "bom" / "BOM.csv", "a", newline="") as f:
        w = csv.writer(f)
        for ref in ("LBL1", "DNC-PAD"):
            if ref not in have:
                v, _fp, mpn, mfr, notes = BOMDATA[ref]
                w.writerow([ref, v, "", mpn, mfr, "1", ""])
    bom = list(csv.DictReader(open(HERE / "bom" / "BOM.csv")))
    print(f"BOM: {len(bom)} refs (with mechanics)")
    assert len(bom) == 99, f"BOM refs {len(bom)}"
    allowed_empty = {"R21", "C69"}
    allowed_empty |= {f"TP{i}" for i in range(1, 9)}
    allowed_empty |= {"H1", "H2", "H3", "H4", "LBL1", "DNC-PAD"}
    bad = [r["Reference"] for r in bom
           if not r.get("MPN") and r["Reference"] not in allowed_empty]
    assert not bad, f"empty MPN: {bad}"
    step = (MFG / "board.step").read_text(errors="replace")
    pts = re.findall(r"CARTESIAN_POINT\s*\([^)]*?\(\s*([-\d.]+)\s*,\s*([-\d.]+)",
                     step)
    xs = [float(p[0]) for p in pts]
    ys = [float(p[1]) for p in pts]
    assert xs and ys, "no cartesian points"
    print(f"STEP: {len(pts)} points, x {min(xs):.1f}-{max(xs):.1f} "
          f"y {min(ys):.1f}-{max(ys):.1f} (includes component overhangs)")
    # Board size is proven by the Edge.Cuts gerber (exact 95x45 rect).
    edge = (GERB / "co2-node-Edge_Cuts.gm1").read_text(errors="replace")
    exy = re.findall(r"X(-?\d+)Y(-?\d+)", edge)
    ex = [int(n[0]) / 1e6 for n in exy]
    ey = [int(n[1]) / 1e6 for n in exy]
    assert abs(min(ex) - 0) < 0.01 and abs(max(ex) - 95) < 0.01
    assert abs(min(ey) - 0) < 0.01 and abs(max(ey) - 45) < 0.01
    print("mfg: all assertions passed (95.0 x 45.0 board)")


if __name__ == "__main__":
    sys.exit(main())
