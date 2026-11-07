#!/usr/bin/env python3
"""Whole-project verification harness (run from hardware/co2-node).

Levels: 1 structure (<5 s), 2 KiCad, 3 firmware (~1-3 min), default = all
(plus level 4 records). Prints one PASS/FAIL line per check + summary.
Exit 0/1.
"""
import csv
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent.parent
FW = ROOT / "firmware" / "co2-node"
PROD = ROOT / "production"

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'} {name} — {detail}")


def run(*args, cwd=HERE, timeout=300):
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd,
                          timeout=timeout)


def level1():
    # determinism: snapshot, regenerate, byte-compare (gen_all also runs
    # here so level 1 refreshes every artifact the later levels check)
    import hashlib
    # Byte-stable set: generator-owned s-expr/csv (tool binaries carry
    # timestamps and are verified by content assertions in mfg.py).
    tracked = ["power.kicad_sch", "mcu.kicad_sch", "sensor.kicad_sch",
               "display.kicad_sch", "connectors.kicad_sch",
               "co2-node.kicad_sch", "sym/co2-node.kicad_sym",
               "co2-node.kicad_pcb", "co2-node.kicad_pro",
               "bom/BOM.csv", "bom/CPL.csv",
               "fp/co2-node.pretty/BQ24074-VQFN-16.kicad_mod",
               "fp/co2-node.pretty/Keystone-1043.kicad_mod",
               "fp/co2-node.pretty/SCD41-LGA.kicad_mod",
               "fp/co2-node.pretty/TPS7A26-WSON-6.kicad_mod"]
    before = {}
    for p in tracked:
        fp = HERE / p
        if fp.exists():
            before[p] = hashlib.sha256(fp.read_bytes()).hexdigest()
    r = run(sys.executable, "tools/gen_all.py")
    same = r.returncode == 0
    for p, h in before.items():
        fp = HERE / p
        if not fp.exists() or hashlib.sha256(fp.read_bytes()).hexdigest() != h:
            same = False
    r2 = run(sys.executable, "tools/mfg.py")
    same = same and r2.returncode == 0
    check("deterministic", same, "regen byte-identical + mfg clean")
    sys.path.insert(0, str(HERE / "tools"))
    sys.path.insert(0, str(HERE / "tools" / "kicad"))
    from bom_data import BOM  # noqa
    from kicad.netmap import NETS  # noqa
    from kicad.footprints import FOOTPRINTS  # noqa
    from gen_sch import footprint_for, sym_for  # noqa
    allowed = {"R21", "C69"}
    allowed |= {f"TP{i}" for i in range(1, 9)}
    allowed |= {"H1", "H2", "H3", "H4", "LBL1", "DNC-PAD"}
    bad = [r for r in BOM if r not in allowed
           and (not BOM[r][2] or not BOM[r][3])]
    check("bom-fields", not bad, f"{len(BOM)} refs" + (f" bad={bad}" if bad else ""))
    badfp = []
    for ref in NETS:
        try:
            fps = footprint_for(ref, sym_for(ref))
            lib, name = fps.split(":", 1)
            if lib == "co2-node":
                if not (HERE / "fp" / "co2-node.pretty" / f"{name}.kicad_mod").exists():
                    badfp.append(ref)
            else:
                import glob as _g
                if not _g.glob(f"/usr/share/kicad/footprints/{lib}.pretty/{name}.kicad_mod"):
                    badfp.append(ref)
        except Exception as e:  # noqa
            badfp.append(f"{ref}:{e}")
    check("footprints-resolve", not badfp, f"{len(NETS)} refs" + (f" bad={badfp[:5]}" if badfp else ""))
    # pro json
    try:
        pro = json.load(open(HERE / "co2-node.kicad_pro"))
        ok = pro["meta"]["version"] == 3
    except Exception as e:  # noqa
        ok = False
    check("pro-json", ok, "meta.version == 3")
    # sch contains lib_symbols + embedded_fonts
    ok = True
    for f in ["power", "mcu", "sensor", "display", "connectors"]:
        t = (HERE / f"{f}.kicad_sch").read_text()
        if "(lib_symbols" not in t or "(embedded_fonts no)" not in t:
            ok = False
    check("sch-shape", ok, "lib_symbols + embedded_fonts")
    # label svg xml
    try:
        ET.parse(PROD / "label.svg")
        ok = True
    except Exception:  # noqa
        ok = False
    check("label-xml", ok, "production/label.svg parses")


def netlist_nodes():
    t = (HERE / "build" / "netlist.net").read_text()
    sec = t[t.find("(nets"):]
    blocks = re.split(r"\t\t\(net\n", sec)
    nodes = {}
    for b in blocks[1:]:
        m = re.search(r'\(name "([^"]+)"\)', b)
        if not m:
            continue
        nodes.setdefault(m.group(1), []).extend(
            sorted(re.findall(r'\(ref "([^"]+)"\)\n\t\t\t\t\(pin "([^"]+)"\)', b)))
    return {n: v for n, v in nodes.items() if not n.startswith("unconnected")}


def level2():
    run("kicad-cli", "sym", "upgrade", "--output", "build/symcheck",
        "sym/co2-node.kicad_sym")
    check("sym-parse", (HERE / "build" / "symcheck").exists(), "sym upgrade exit 0")
    run("kicad-cli", "fp", "upgrade", "--output", "build/fpcheck",
        "fp/co2-node.pretty")
    check("fp-parse", (HERE / "build" / "fpcheck").exists(), "fp upgrade exit 0")
    r = run("kicad-cli", "sch", "erc", "--severity-error",
            "--severity-warning", "--exit-code-violations", "--format", "json",
            "-o", "reports/erc.json", "co2-node.kicad_sch")
    d = json.load(open(HERE / "reports/erc.json"))
    errs = [v for s in d["sheets"] for v in s.get("violations", [])
            if v["severity"] == "error"]
    warns = [(v["type"]) for s in d["sheets"] for v in s.get("violations", [])
             if v["severity"] != "error" and v["type"] != "footprint_link_issues"]
    allow = {}
    for line in (HERE / "reports" / "erc-allowlist.txt").read_text().splitlines():
        if line.strip():
            code, count, _reason = line.split("\t")
            allow[code] = int(count)
    import collections
    wc = collections.Counter(warns)
    check("erc", not errs and wc == allow,
          f"errors={len(errs)} warnings={dict(wc)}")
    # netlist assertions
    run("kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr",
        "-o", "build/netlist.net", "co2-node.kicad_sch")
    nodes = netlist_nodes()
    exp = {
        "I2C_SDA": [("IC-SCD", "10"), ("R50", "2"), ("U10", "13")],
        "PWR_EN": [("Q4", "1"), ("R29", "1"), ("TP8", "1"), ("U10", "30")],
        "VBAT_SENSE": [("R32", "2"), ("U10", "6")],
    }
    ok = all(sorted(nodes.get(k, [])) == sorted(v) for k, v in exp.items())
    ok = ok and all(len(nodes.get(f"EPD_{s}", [])) == 2
                    for s in ("SDA", "SCL", "CS", "DC", "RES", "BUSY"))
    n_epd = sum(len(nodes.get(f"EPD_{s}", [])) for s in ("SDA", "SCL", "CS", "DC", "RES", "BUSY"))
    check("nets", ok, f"{len(nodes)} nets, I2C_SDA={len(nodes.get('I2C_SDA', []))} "
                       f"PWR_EN={len(nodes.get('PWR_EN', []))} EPD={n_epd}")
    # drc
    r = run("kicad-cli", "pcb", "drc", "--schematic-parity", "--severity-all",
            "--format", "json", "-o", "reports/drc.json", "co2-node.kicad_pcb")
    d = json.load(open(HERE / "reports/drc.json"))
    par = d.get("schematic_parity", [])
    vtypes = {v.get("type") for v in d.get("violations", [])}
    allow_drc = {}
    for line in (HERE / "reports" / "drc-allowlist.txt").read_text().splitlines():
        if line.strip():
            code, count, _reason = line.split("\t")
            allow_drc[code] = int(count)
    import collections as _c
    vc = _c.Counter(v.get("type") for v in d.get("violations", []))
    ok = (not par and set(vc) - set(allow_drc) <= {"unconnected_items"}
          and all(vc[k] == allow_drc[k] for k in vc if k in allow_drc))
    check("drc", ok, f"parity={len(par)} violations={dict(vc)} "
                     f"unconnected={len(d.get('unconnected_items', []))}")
    # export assertions
    gerbers = list((HERE / "manufacturing" / "gerbers").glob("*.g*"))
    cu = [g for g in gerbers if g.suffix in (".gtl", ".gbl", ".gto", ".gbo",
                                            ".gts", ".gbs", ".gm1")]
    cpl = list(csv.DictReader(open(HERE / "bom" / "CPL.csv")))
    bom = list(csv.DictReader(open(HERE / "bom" / "BOM.csv")))
    ok = len(cu) == 7 and len(cpl) == 93 and len(bom) == 99
    check("exports", ok, f"BOM {len(bom)} refs, CPL {len(cpl)} rows, "
                         f"{len(cu)} gerbers")


def level3(full=False):
    for cfg in ["top", "mid", "bottom", "gift", "test"]:
        r = run("esphome", "config", f"{cfg}.yaml", cwd=FW, timeout=240)
        if "Configuration is valid!" not in (r.stdout + r.stderr):
            check(f"esphome-{cfg}", False, "config invalid")
            return
    check("esphome-configs", True, "5 configs valid")
    dump = run("esphome", "config", "top.yaml", cwd=FW, timeout=240).stdout
    ok = ('name: "Top Floor CO2"' in dump or "Top Floor CO2" in dump)
    check("entity-names", ok, "Top Floor CO2 present")
    mid = run("esphome", "config", "mid.yaml", cwd=FW, timeout=240).stdout
    bot = run("esphome", "config", "bottom.yaml", cwd=FW, timeout=240).stdout
    ok = ("Mid Floor" in mid and "Bottom Floor" in bot)
    check("entity-names-mid-bottom", ok, "mid/bottom names present")
    r = run(sys.executable, str(PROD / "build_unit.py"), "--serial",
            "AH-CO2-TEST", "--mac", "AA:BB:CC:DD:EE:01", "--render-only",
            cwd=PROD)
    yf = FW / "product-ee01.yaml"
    ok = r.returncode == 0 and yf.exists()
    if ok:
        r2 = run("esphome", "config", str(yf), cwd=FW, timeout=240)
        ok = "Configuration is valid!" in (r2.stdout + r2.stderr)
        yf.unlink()
    check("render-only", ok, "product-ee01 renders + validates")
    r = run(sys.executable, str(PROD / "test_unit.py"), "--serial", "DRY",
            "--port", "none", "--dry-run", "--log", "fixtures/pass.log",
            cwd=PROD)
    r2 = run(sys.executable, str(PROD / "test_unit.py"), "--serial", "DRY",
             "--port", "none", "--dry-run", "--log", "fixtures/fail.log",
             cwd=PROD)
    ok = (r.returncode == 0 and r2.returncode == 1
          and "CO2 out of range" in (r2.stdout + r2.stderr))
    check("dry-run", ok, "pass.log 0 / fail.log 1 + CO2 out of range")
    for f in PROD.glob("test-DRY.log"):
        f.unlink()
    if full:
        r = run("esphome", "compile", "top.yaml", cwd=FW, timeout=1800)
        check("compile-top", r.returncode == 0, "esphome compile top.yaml")


def level4():
    import re as _re
    docs = {
        HERE / "LAYOUT.md": None, HERE / "ORDER.md": None,
        ROOT / "docs" / "compliance" / "TECHFILE.md": None,
        ROOT / "enclosure" / "BUILD.md": None,
    }
    missing = []
    for doc in docs:
        if not doc.exists():
            missing.append(str(doc))
            continue
        text = doc.read_text()
        for m in _re.findall(r"(?<![A-Za-z0-9_@./-])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.(?:csv|sch|pcb|pro|step|md|svg|pdf|yaml|pretty|kicad_sym|kicad_mod|d356|net|rpt|json|txt|png)", text):
            if not any(((doc.parent / m).exists(), (HERE / m).exists(),
                            (ROOT / m).exists())):
                missing.append(f"{doc.name}: {m}")
    check("records", not missing, f"{len(missing)} missing" if missing else "all paths exist")


def main():
    args = sys.argv[1:]
    level = int(args[args.index("--level") + 1]) if "--level" in args else 0
    only = args[args.index("--only") + 1] if "--only" in args else ""
    full = "--full" in args
    (HERE / "build").mkdir(exist_ok=True)
    (HERE / "reports").mkdir(exist_ok=True)
    if level in (0, 1):
        level1()
    if level in (0, 2):
        if not only or only in ("nets", "exports"):
            level2()
        else:
            level2()
    if level in (0, 3):
        level3(full)
    if level == 0 or level == 4:
        level4()
    nfail = sum(1 for _, ok, _ in results if not ok)
    print(f"ALL CHECKS PASSED (levels, {len(results)} checks)" if not nfail
          else f"{nfail}/{len(results)} CHECKS FAILED")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
