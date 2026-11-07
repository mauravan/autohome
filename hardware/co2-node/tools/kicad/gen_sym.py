#!/usr/bin/env python3
"""Emit sym/co2-node.kicad_sym from tools/kicad/symbols.py.

Plain symbol names ("BQ24074", not "co2-node:BQ24074"), version 20250114,
embedded_fonts no. Validate: kicad-cli sym upgrade -o build/symcheck sym/...
(exit 0 = parse proof). Run from hardware/co2-node/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexpr import Sym, uid, write  # noqa: E402
from symbols import SYMBOLS  # noqa: E402

HERE = Path(__file__).resolve().parent.parent.parent
LIB = "co2-node"


def pin_sym(name, number, pinname, etype, x, y, angle):
    return Sym("pin", f"{etype} line",
               Sym("at", x, y, angle),
               Sym("length", 2.54),
               Sym("name", f'"{pinname}"',
                   Sym("effects", Sym("font", Sym("size", 1.27, 1.27)))),
               Sym("number", f'"{number}"',
                   Sym("effects", Sym("font", Sym("size", 1.27, 1.27)))))


def lib_symbol(spec):
    name = spec["name"]
    kids = [
        Sym("exclude_from_sim", "no"),
        Sym("in_bom", "yes"),
        Sym("on_board", "yes"),
        Sym("property", '"Reference"', f'"{spec["ref_prefix"]}"',
            Sym("at", 0, 5, 0),
            Sym("effects", Sym("font", Sym("size", 1.27, 1.27)))),
        Sym("property", '"Value"', f'"{name}"',
            Sym("at", 0, -5, 0),
            Sym("effects", Sym("font", Sym("size", 1.27, 1.27)))),
        Sym("property", '"Footprint"', '""',
            Sym("at", 0, 0, 0),
            Sym("effects", Sym("font", Sym("size", 1.27, 1.27)),
                Sym("hide", "yes"))),
        Sym("property", '"Datasheet"', '""',
            Sym("at", 0, 0, 0),
            Sym("effects", Sym("font", Sym("size", 1.27, 1.27)),
                Sym("hide", "yes"))),
    ]
    if spec.get("power"):
        kids.insert(0, Sym("power"))
    gfx = [Sym("symbol", f'"{name}_0_1"',
               Sym("rectangle", Sym("start", -12.7, 12.7),
                   Sym("end", 12.7, -12.7),
                   Sym("stroke", Sym("width", 0.254),
                       Sym("type", "default")),
                   Sym("fill", Sym("type", "background"))))]
    pins = [pin_sym(name, n, pn, et, x, y, a)
            for n, pn, et, x, y, a in lay_pins(spec)]
    gfx.append(Sym("symbol", f'"{name}_1_1"', *pins))
    if spec["name"] in ("GND", "PWR_FLAG"):
        gfx = [Sym("symbol", f'"{name}_0_1"',
                   Sym("polyline", Sym("pts",
                                       Sym("xy", 0, 0), Sym("xy", 0, -1.27),
                                       Sym("xy", 1.27, -1.27),
                                       Sym("xy", 0, -2.54),
                                       Sym("xy", -1.27, -1.27),
                                       Sym("xy", 0, -1.27)),
                       Sym("stroke", Sym("width", 0),
                           Sym("type", "default")),
                       Sym("fill", Sym("type", "none")))),
               Sym("symbol", f'"{name}_1_1"', *pins)]
    kids.extend(gfx)
    kids.append(Sym("embedded_fonts", "no"))
    return Sym("symbol", f'"{LIB}:{name}"', *kids)


def lay_pins(spec):
    """Assign library coordinates: pins may carry explicit (num,name,etype)
    triples (auto two-column layout) or full (num,name,etype,x,y,angle)."""
    pins = spec["pins"]
    if pins and len(pins[0]) == 6:
        return pins
    n = len(pins)
    n_left = (n + 1) // 2
    out = []
    for i, (num, nm, et) in enumerate(pins[:n_left]):
        out.append((num, nm, et, -12.7, 10.16 - i * 5.08, 180))
    for i, (num, nm, et) in enumerate(pins[n_left:]):
        out.append((num, nm, et, 12.7, 10.16 - i * 5.08, 0))
    return out


def build_lib():
    return Sym("kicad_symbol_lib",
               Sym("version", 20250114),
               Sym("generator", '"co2-node-sym"'),
               Sym("generator_version", '"1.0"'),
               *[lib_symbol(s) for s in SYMBOLS])


def main():
    write(build_lib(), HERE / "sym" / "co2-node.kicad_sym")
    print(f"symbols: {len(SYMBOLS)} -> sym/co2-node.kicad_sym")


if __name__ == "__main__":
    main()
