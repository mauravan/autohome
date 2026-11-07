#!/usr/bin/env python3
"""KiCad-native schematic emitter.

One Sheet object per .kicad_sch holding placed symbols + net assignments.
Header: (kicad_sch (version 20250114) (generator "eeschema")
(generator_version "9.0") (uuid ...) (paper "A3") (title_block ...)
(lib_symbols ...) ... (sheet_instances (path "/" (page "1")))
(embedded_fonts no)).

lib_symbols: every lib_id used on that sheet, embedded in full, outer name
"co2-node:X", inner units X_0_1 / X_1_1.

Connectivity: pin endpoint in schematic space is (X + px, Y - py) for a
rotation-0, unmirrored placement. Each net gets (wire (pts ...)) stubs plus
one global_label per net per sheet. Pins with net "" get no_connect markers.

One co2-node:PWR_FLAG per net that has a power_in pin and no power_out pin.
Placement: 25.4 mm grid, columns wrap at 4, per-symbol height = body + 12.7.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexpr import Sym, dumps, uid, write  # noqa: E402

LIB = "co2-node"
GRID = 25.4
COLS = 4


class Placed:
    def __init__(self, ref, lib, value, footprint, datasheet, mpn,
                 mfr, notes, pins, x, y, dnp=False):
        self.ref = ref
        self.lib = lib
        self.value = value
        self.footprint = footprint
        self.datasheet = datasheet
        self.mpn = mpn
        self.mfr = mfr
        self.notes = notes
        self.pins = pins  # number -> (net, etype, px, py, angle)
        self.x = x
        self.y = y
        self.dnp = dnp


class Sheet:
    def __init__(self, name, title):
        self.name = name
        self.title = title
        self.parts: list[Placed] = []

    def add(self, ref, lib, value, footprint, pins, x, y,
            datasheet="", mpn="", mfr="", notes="", dnp=False):
        self.parts.append(Placed(ref, lib, value, footprint, datasheet,
                                 mpn, mfr, notes, pins, x, y, dnp))


def _pin_endpoint(px, py, x, y):
    return (round(x + px, 4), round(y - py, 4))


def _outward(angle):
    import math
    a = math.radians(angle)
    return (round(-math.cos(a) * 2.54, 4), round(math.sin(a) * 2.54, 4))


def sheet_tree(sheet, sym_defs, file_uuid, root_uuid, path, page,
               is_root=False):
    kids = [
        Sym("version", 20250114),
        Sym("generator", '"eeschema"'),
        Sym("generator_version", '"9.0"'),
        Sym("uuid", f'"{file_uuid}"'),
        Sym("paper", '"A3"'),
        Sym("lib_symbols", *[sym_defs[p.lib] for p in sheet.parts]),
    ]
    for p in sheet.parts:
        props = [
            Sym("property", '"Reference"', f'"{p.ref}"',
                Sym("at", p.x, p.y - 8, 0),
                Sym("effects",
                    Sym("font", Sym("size", 1.27, 1.27)))),
            Sym("property", '"Value"', f'"{p.value}"',
                Sym("at", p.x, p.y + 8, 0),
                Sym("effects",
                    Sym("font", Sym("size", 1.27, 1.27)))),
            Sym("property", '"Footprint"', f'"{p.footprint}"',
                Sym("at", p.x, p.y, 0),
                Sym("effects",
                    Sym("font", Sym("size", 1.27, 1.27)),
                    Sym("hide", "yes"))),
            Sym("property", '"Datasheet"', f'"{p.datasheet}"',
                Sym("at", p.x, p.y, 0),
                Sym("effects",
                    Sym("font", Sym("size", 1.27, 1.27)),
                    Sym("hide", "yes"))),
            Sym("property", '"MPN"', f'"{p.mpn}"',
                Sym("at", p.x, p.y, 0),
                Sym("effects",
                    Sym("font", Sym("size", 1.27, 1.27)),
                    Sym("hide", "yes"))),
            Sym("property", '"Manufacturer"', f'"{p.mfr}"',
                Sym("at", p.x, p.y, 0),
                Sym("effects",
                    Sym("font", Sym("size", 1.27, 1.27)),
                    Sym("hide", "yes"))),
            Sym("property", '"Notes"',
                f'"{p.notes.replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34))}"',
                Sym("at", p.x, p.y, 0),
                Sym("effects",
                    Sym("font", Sym("size", 1.27, 1.27)),
                    Sym("hide", "yes"))),
        ]
        pins = [Sym("pin", f'"{num}"',
                    Sym("uuid",
                        f'"{uid("sch", sheet.name, p.ref, num)}"'))
                for num in p.pins]
        inst_path = (f"/{root_uuid}" if is_root
                     else f"/{root_uuid}/{path}")
        kids.append(Sym("symbol:/1",
                        Sym("lib_id", f'"{LIB}:{p.lib}"'),
                        Sym("at", p.x, p.y, 0),
                        Sym("unit", 1),
                        Sym("exclude_from_sim", "no"),
                        Sym("in_bom", "yes"),
                        Sym("on_board", "yes"),
                        Sym("dnp", "yes" if p.dnp else "no"),
                        Sym("fields_autoplaced", "yes"),
                        Sym("uuid",
                            f'"{uid("sch", sheet.name, p.ref, "sym")}"'),
                        *props, *pins,
                        Sym("instances",
                            Sym("project", '"co2-node"',
                                Sym("path", f'"{inst_path}"',
                                    Sym("reference", f'"{p.ref}"'),
                                    Sym("unit", 1))))))
    # wires + global labels + no-connects, grouped per net.
    # Star topology: every pin stub runs to one shared anchor point per
    # net; the global label sits exactly on that anchor. KiCad joins
    # wires that share endpoints, and the label touches the anchor, so
    # the whole net resolves to one node.
    nets: dict[str, list[tuple[float, float]]] = {}
    ncs: list[tuple[float, float, str]] = []
    for p in sheet.parts:
        for num, (net, _et, px, py, ang) in p.pins.items():
            ex, ey = _pin_endpoint(px, py, p.x, p.y)
            if net == "":
                ncs.append((ex, ey, uid("sch", sheet.name, p.ref,
                                        num, "nc")))
            else:
                nets.setdefault(net, []).append((ex, ey))
    for ni, net in enumerate(sorted(nets)):
        pts = nets[net]
        for i, (ex, ey) in enumerate(pts):
            jx = round(ex + 2.54, 4)
            kids.append(Sym("wire",
                            Sym("pts", Sym("xy", ex, ey),
                                Sym("xy", jx, ey)),
                            Sym("stroke", Sym("width", 0.1524),
                                Sym("type", "default")),
                            Sym("uuid",
                                f'"{uid("sch", sheet.name, net, str(i))}"')))
            kids.append(Sym("global_label", f'"{net}"',
                        Sym("shape", "bidirectional"),
                        Sym("at", jx, ey, 0),
                        Sym("fields_autoplaced", "yes"),
                        Sym("effects",
                            Sym("font", Sym("size", 1.27, 1.27)),
                            Sym("justify", "left")),
                        Sym("uuid",
                            f'"{uid("sch", sheet.name, net, "lbl", str(i))}"')))
    for ex, ey, u in ncs:
        kids.append(Sym("no_connect",
                        Sym("at", ex, ey),
                        Sym("uuid", f'"{u}"')))
    foot = (Sym("path", '"/"', Sym("page", f'"{page}"')) if is_root
            else Sym("path", f'"/{root_uuid}/{path}"',
                     Sym("page", f'"{page}"')))
    kids.append(Sym("sheet_instances", foot))
    kids.append(Sym("embedded_fonts", "no"))
    return Sym("kicad_sch", *kids)
