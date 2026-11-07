#!/usr/bin/env python3
"""Regenerate every hardware artifact in dependency order.

sym -> schematic (+ netlist) -> footprints -> pcb -> mfg exports.
Run from hardware/co2-node/. Byte-identical on re-run (deterministic uids).
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PY = "/usr/bin/python3"


def run(*args):
    print("+", " ".join(str(a) for a in args[1:]))
    r = subprocess.run(args, cwd=HERE)
    if r.returncode:
        sys.exit(r.returncode)


def main():
    run(PY, "tools/kicad/gen_sym.py")
    run(PY, "tools/gen_sch.py")
    run("kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr",
        "-o", "build/netlist.net", "co2-node.kicad_sch")
    run(PY, "tools/kicad/footprints.py")
    run(PY, "tools/gen_pcb.py")
    run(PY, "tools/mfg.py")


if __name__ == "__main__":
    main()
