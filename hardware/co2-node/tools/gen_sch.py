#!/usr/bin/env python3
"""Build all six .kicad_sch files (5 sheets + root) from netmap + bom_data.

Order: power, mcu, sensor, display, connectors, then root co2-node.kicad_sch
with five (sheet ...) records, pages 2-6. Root (sheet ...) shape was proven
in /tmp/hier-test: netlist resolves the shared global label across sheets.

Run from hardware/co2-node/: python3 tools/gen_sch.py
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kicad"))
from schematic import GRID, Sheet, sheet_tree  # noqa: E402
from sexpr import Sym, uid, write  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kicad.symbols import SYMBOLS  # noqa: E402
from kicad.netmap import DNP, MECH_NETS, NETS, SHEETS  # noqa: E402
from bom_data import BOM  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
LIB = "co2-node"

TITLES = {
    "power": "Power: USB-C, BQ24074, TPS7A26, protection, gate, divider",
    "mcu": "MCU: ESP32-C3-MINI-1-N4, USB, BOOT/RESET, decoupling, test pads",
    "sensor": "Sensor: SCD41-D-R2, ferrite, pull-ups, DNC float",
    "display": "Display: FPC-24 + WeAct boost (SSD1681), 3V3-fed, no ME6216",
    "connectors": "Connectors: 18650 holder, NTC, buttons, test pads, mounting",
}

FOOTPRINTS = {
    "ESP32-C3-MINI-1": "RF_Module:ESP32-C6-MINI-1",  # same MINI-1 family/land pattern (see schematic-notes.md)
    "BQ24074": "co2-node:BQ24074-VQFN-16",
    "TPS7A2633": "co2-node:TPS7A26-WSON-6",
    "DW01A": "Package_TO_SOT_SMD:SOT-23-6",
    "FS8205A": "Package_SO:TSSOP-8_4.4x3mm_P0.65mm",
    "AO3401A": "Package_TO_SOT_SMD:SOT-23",
    "AO3402": "Package_TO_SOT_SMD:SOT-23",
    "BSS138": "Package_TO_SOT_SMD:SOT-23",
    "USBLC6-2SC6": "Package_TO_SOT_SMD:SOT-23-6",
    "SCD41": "Sensor:Sensirion_SCD4x-1EP_10.1x10.1mm_P1.25mm_EP4.8x4.8mm",
    "USB_C_16P": "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A",
    "FPC-24": "Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal",
    "BAT_HOLDER": "co2-node:Keystone-1043",
    "R": "Resistor_SMD:R_0603_1608Metric",
    "R0402": "Resistor_SMD:R_0402_1005Metric",
    "C": "Capacitor_SMD:C_0603_1608Metric",
    "C0402": "Capacitor_SMD:C_0402_1005Metric",
    "L": "Inductor_SMD:L_0603_1608Metric",
    "D": "Diode_SMD:D_SOD-323",
    "LED": "LED_SMD:LED_0603_1608Metric",
    "FUSE0603": "Fuse:Fuse_0603_1608Metric",
    "FUSE1206": "Fuse:Fuse_1206_3216Metric",
    "NTC": "Resistor_SMD:R_0603_1608Metric",
    "SW": "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2",
    "TP": "TestPoint:TestPoint_Pad_1.0x1.0mm",
    "MOUNT": "MountingHole:MountingHole_2.7mm_M2.5_Pad",
    "GND": "", "PWR_FLAG": "",
}

R0402 = {"R1", "R60", "R61", "R62", "R63", "R64", "R65", "R66"}
C0402 = {"C60", "C61", "C62", "C63", "C64", "C65", "C67", "C68", "C69",
         "C70", "C71", "C72"}
F1206 = {"F2"}


def footprint_for(ref, sym):
    if sym in ("GND", "PWR_FLAG"):
        return ""
    if sym == "R":
        return FOOTPRINTS["R0402" if ref in R0402 else "R"]
    if sym == "C":
        return FOOTPRINTS["C0402" if ref in C0402 else "C"]
    if sym == "FUSE":
        return FOOTPRINTS["FUSE1206" if ref in F1206 else "FUSE0603"]
    return FOOTPRINTS[sym]


def sym_for(ref):
    v, fp, mpn, mfr, notes = BOM[ref]
    if ref.startswith("R") and not ref.startswith("RT"):
        return "R"
    if ref.startswith("C"):
        return "C"
    if ref in ("Q2", "Q3"):
        return "AO3401A"
    if ref == "Q1":
        return "AO3402"
    if ref == "Q4":
        return "BSS138"
    if ref == "D1":
        return "USBLC6-2SC6"
    if ref in ("D21", "D22", "D23"):
        return "D"
    if ref == "D20":
        return "LED"
    if ref == "IC-SCD":
        return "SCD41"
    if ref == "J1":
        return "USB_C_16P"
    if ref == "J2":
        return "FPC-24"
    if ref == "BT1":
        return "BAT_HOLDER"
    if ref == "RT1":
        return "NTC"
    if ref in ("SW1", "SW2"):
        return "SW"
    if ref.startswith("TP"):
        return "TP"
    if ref.startswith("H"):
        return "MOUNT"
    if ref == "U1":
        return "BQ24074"
    if ref == "U2":
        return "TPS7A2633"
    if ref == "U3":
        return "DW01A"
    if ref == "U4":
        return "FS8205A"
    if ref == "U10":
        return "ESP32-C3-MINI-1"
    if ref in ("FB50", "L1"):
        return "L"
    if ref.startswith("F"):
        return "FUSE"
    raise KeyError(ref)


NAME2SYM = {s["name"]: s for s in SYMBOLS}


def auto_pins(sym):
    """Two-column auto layout mirroring gen_sym.lay_pins (for pin lookup)."""
    pins = NAME2SYM[sym]["pins"]
    if pins and len(pins[0]) == 6:
        return {n: (None, et, x, y, a) for n, _nm, et, x, y, a in pins}
    n = len(pins)
    out = {}
    for i, (num, _nm, et) in enumerate(pins[: (n + 1) // 2]):
        out[num] = (None, et, -12.7, 10.16 - i * 5.08, 180)
    for i, (num, _nm, et) in enumerate(pins[(n + 1) // 2:]):
        out[num] = (None, et, 12.7, 10.16 - i * 5.08, 0)
    return out


def build_sheets():
    order = ["power", "mcu", "sensor", "display", "connectors"]
    sheets = {name: Sheet(name, TITLES[name]) for name in order}
    # deterministic placement: sorted refs per sheet, grid wrap at 4
    by_sheet: dict[str, list[str]] = {n: [] for n in order}
    for ref in sorted(NETS, key=lambda r: (SHEETS[r], r)):
        by_sheet[SHEETS[ref]].append(ref)
    for name in order:
        for i, ref in enumerate(by_sheet[name]):
            sym = sym_for(ref)
            col, row = i % 4, i // 4
            x = GRID * (2 + col * 6)
            y = GRID * (2 + row * 5)
            pinpos = auto_pins(sym)
            pins = {}
            for num, net in NETS[ref].items():
                _nn, et, px, py, ang = pinpos[num]
                pins[num] = (net, et, px, py, ang)
            v, _fp, mpn, mfr, notes = BOM[ref]
            sheets[name].add(ref, sym, v, footprint_for(ref, sym),
                             pins, x, y, datasheet="", mpn=mpn, mfr=mfr,
                             notes=notes, dnp=ref in DNP)
    # PWR_FLAGs: one per net that has a power_in pin and no power_out pin
    # anywhere (computed globally so no net gets two power_out drivers).
    # Placed on the first sheet (in sheet order) containing the net.
    have_out: dict[str, bool] = {}
    have_in: dict[str, bool] = {}
    for name in order:
        for p in sheets[name].parts:
            for _num, (net, et, _x, _y, _a) in p.pins.items():
                if net == "":
                    continue
                if et == "power_out":
                    have_out[net] = True
                if et == "power_in":
                    have_in[net] = True
    need = sorted(n for n in have_in if n not in have_out)
    seen: dict[str, bool] = {}
    for name in order:
        sh = sheets[name]
        for net in need:
            if net in seen:
                continue
            nets_here = {nn for p in sh.parts for _n, (nn, _e, _x, _y, _a)
                         in p.pins.items()}
            if net in nets_here:
                i = len(sh.parts)
                col, row = i % 4, i // 4
                sh.add(f"#PWR{len(seen):02d}", "PWR_FLAG", net, "",
                       {"1": (net, "power_out", 0, 0, 270)},
                       GRID * (2 + col * 6), GRID * (2 + row * 5))
                seen[net] = True
    return sheets


def sym_lib_defs(used):
    from kicad.gen_sym import lay_pins, lib_symbol  # noqa: E402
    return {lib: lib_symbol(NAME2SYM[lib]) for lib in used}


def main():
    HERE  # noqa: B018
    sheets = build_sheets()
    from kicad import gen_sym  # noqa: E402
    _ = gen_sym
    from kicad.gen_sym import lay_pins as _lp, lib_symbol as _ls  # noqa: E402
    root_uuid = uid("sch", "root")
    order = ["power", "mcu", "sensor", "display", "connectors"]
    sheet_uuids = {n: uid("sch", "sheet", n) for n in order}
    for page, name in enumerate(order, start=2):
        used = []
        for p in sheets[name].parts:
            if p.lib not in used:
                used.append(p.lib)
        defs = {lib: _ls(NAME2SYM[lib]) for lib in used}
        tree = sheet_tree(sheets[name], defs, uid("sch", "file", name),
                          root_uuid, sheet_uuids[name], page, is_root=False)
        write(tree, HERE / f"{name}.kicad_sch")
        print(f"{name}: {len(sheets[name].parts)} parts")
    # root
    kids = [
        Sym("version", 20250114),
        Sym("generator", '"eeschema"'),
        Sym("generator_version", '"9.0"'),
        Sym("uuid", f'"{root_uuid}"'),
        Sym("paper", '"A3"'),
        Sym("title_block",
            Sym("title", '"CO2 sensor node rev A - root"'),
            Sym("date", '"2026-11-05"'),
            Sym("rev", '"A"'),
            Sym("company", '"autohome"')),
    ]
    x = 10.0
    for page, name in enumerate(order, start=2):
        su = sheet_uuids[name]
        kids.append(Sym("sheet",
                        Sym("at", x, 10.0),
                        Sym("size", 110, 70),
                        Sym("fields_autoplaced", "yes"),
                        Sym("stroke", Sym("width", 0.1524),
                            Sym("type", "solid")),
                        Sym("fill", Sym("color", 0, 0, 0, 0.0)),
                        Sym("uuid", f'"{su}"'),
                        Sym("property", '"Sheetname"', f'"{name}"',
                            Sym("at", x, 8.0, 0),
                            Sym("effects",
                                Sym("font", Sym("size", 1.27, 1.27)))),
                        Sym("property", '"Sheetfile"',
                            f'"{name}.kicad_sch"',
                            Sym("at", x, 9.5, 0),
                            Sym("effects",
                                Sym("font", Sym("size", 1.27, 1.27)))),
                        Sym("instances",
                            Sym("project", '"co2-node"',
                                Sym("path", f'"/{root_uuid}"',
                                    Sym("page", f'"{page}"'))))))
        x += 120.0
    kids.append(Sym("sheet_instances",
                    Sym("path", '"/"',
                        Sym("page", '"1"'))))
    kids.append(Sym("embedded_fonts", "no"))
    write(Sym("kicad_sch", *kids), HERE / "co2-node.kicad_sch")
    print("root: 5 sheets")


if __name__ == "__main__":
    main()
