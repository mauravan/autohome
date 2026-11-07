#!/usr/bin/env python3
"""Build co2-node.kicad_pcb with pcbnew (run with /usr/bin/python3).

1. Parse build/netlist.net (kicadsexpr) into net -> {(ref, pin)}.
2. Board: 2 copper layers, 1.6 mm thick, 95x45 outline on Edge.Cuts.
3. For each part: FootprintLoad (system dir or fp/co2-node.pretty), place,
   orient, back-side BT1, SetReference/SetValue.
4. Pad nets from netlist + MECH_NETS table (VQFN EP 17, WSON EP 7, FPC MP,
   USB-C SH, mounting holes) so no pad is netless.
5. Antenna keepout: pcbnew.ZONE rule area over x 70-86.5, y 30-46.
6. Save board; write co2-node.kicad_pro (meta.version 3, Default 0.2/0.25 +
   Power 0.25/0.5/0.9 via 0.5).
7. Placement from PLACE table (real courtyard sizes); overlap/keepout/
   thermal assertions run generator-side before DRC.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE / "tools" / "kicad"))
from kicad.footprints import FOOTPRINTS  # noqa: E402
from kicad.netmap import DNP, MECH_NETS, NETS  # noqa: E402
from bom_data import BOM  # noqa: E402

SYS_FP = "/usr/share/kicad/footprints"

# ref -> (footprint_key, x, y, rot, side). 95x45 board,
# origin bottom-left. Courtyard-clean per measured installed
# courtyard sizes (see SIZES); J1 bottom overhang + U10 top overhang
# by design.
PLACE = {
    "BT1": ("BAT_HOLDER", 47.5, 18.0, 0, "B"),
    "C20": ("C", 43.0, 13.5, 0, "F"),
    "C21": ("C", 56.5, 16.0, 0, "F"),
    "C22": ("C", 47.5, 16.5, 0, "F"),
    "C23": ("C", 66.5, 13.5, 0, "F"),
    "C24": ("C", 41.0, 22.0, 0, "F"),
    "C25": ("C", 40.0, 25.0, 0, "F"),
    "C26": ("C", 44.5, 25.0, 0, "F"),
    "C27": ("C", 33.5, 36.0, 0, "F"),
    "C28": ("C", 42.5, 31.0, 0, "F"),
    "C29": ("C", 86.5, 7.5, 0, "F"),
    "C40": ("C", 70.0, 27.0, 0, "F"),
    "C41": ("C", 73.5, 27.0, 0, "F"),
    "C42": ("C", 77.0, 27.0, 0, "F"),
    "C43": ("C", 80.5, 27.0, 0, "F"),
    "C50": ("C", 29.0, 7.0, 0, "F"),
    "C51": ("C", 10.0, 10.5, 0, "F"),
    "C60": ("C0402", 6.0, 24.8, 0, "F"),
    "C61": ("C0402", 9.4, 24.8, 0, "F"),
    "C62": ("C0402", 12.8, 24.8, 0, "F"),
    "C63": ("C0402", 16.2, 24.8, 0, "F"),
    "C64": ("C0402", 19.6, 24.8, 0, "F"),
    "C65": ("C0402", 23.0, 24.8, 0, "F"),
    "C66": ("C", 26.4, 24.8, 0, "F"),
    "C67": ("C0402", 29.8, 24.8, 0, "F"),
    "C68": ("C0402", 45.0, 34.5, 0, "F"),
    "C69": ("C0402", 56.5, 37.0, 0, "F"),
    "C70": ("C0402", 61.5, 29.0, 0, "F"),
    "C71": ("C0402", 47.5, 30.0, 0, "F"),
    "C72": ("C0402", 55.0, 24.5, 0, "F"),
    "D1": ("USBLC6-2SC6", 58.0, 2.5, 0, "F"),
    "D20": ("LED", 58.0, 23.0, 0, "F"),
    "D21": ("D", 48.5, 27.5, 0, "F"),
    "D22": ("D", 52.0, 30.0, 0, "F"),
    "D23": ("D", 58.0, 29.0, 0, "F"),
    "F1": ("FUSE0603", 50.0, 11.0, 0, "F"),
    "F2": ("FUSE1206", 65.0, 7.0, 0, "F"),
    "FB50": ("L", 10.0, 7.0, 0, "F"),
    "H1": ("MOUNT", 3.5, 3.5, 0, "F"),
    "H2": ("MOUNT", 91.5, 3.5, 0, "F"),
    "H3": ("MOUNT", 3.5, 41.5, 0, "F"),
    "H4": ("MOUNT", 48.0, 41.5, 0, "F"),
    "IC-SCD": ("SCD41", 20.0, 7.0, 0, "F"),
    "J1": ("USB_C_16P", 50.0, 4.0, 0, "F"),
    "J2": ("FPC-24", 13.0, 34.5, 0, "F"),
    "L1": ("L", 48.0, 33.5, 0, "F"),
    "Q1": ("AO3402", 52.5, 33.5, 0, "F"),
    "Q2": ("AO3401A", 70.0, 9.5, 0, "F"),
    "Q3": ("AO3401A", 38.0, 32.5, 0, "F"),
    "Q4": ("BSS138", 38.0, 36.5, 0, "F"),
    "R1": ("R0402", 52.5, 38.5, 0, "F"),
    "R10": ("R", 40.0, 6.0, 0, "F"),
    "R11": ("R", 40.0, 9.0, 0, "F"),
    "R12": ("R", 61.0, 7.5, 0, "F"),
    "R13": ("R", 61.0, 10.5, 0, "F"),
    "R2": ("R", 56.5, 33.5, 0, "F"),
    "R20": ("R", 46.5, 13.5, 0, "F"),
    "R21": ("R", 56.5, 12.5, 0, "F"),
    "R22": ("R", 58.0, 20.0, 0, "F"),
    "R23": ("R", 58.0, 26.0, 0, "F"),
    "R24": ("R", 62.0, 12.5, 0, "F"),
    "R25": ("R", 66.5, 19.5, 0, "F"),
    "R27": ("R", 49.5, 23.0, 0, "F"),
    "R28": ("R", 33.5, 32.5, 0, "F"),
    "R29": ("R", 42.5, 36.5, 0, "F"),
    "R30": ("R", 76.0, 7.5, 0, "F"),
    "R31": ("R", 79.5, 7.5, 0, "F"),
    "R32": ("R", 83.0, 7.5, 0, "F"),
    "R40": ("R", 70.0, 23.5, 0, "F"),
    "R41": ("R", 73.5, 23.5, 0, "F"),
    "R42": ("R", 77.0, 23.5, 0, "F"),
    "R43": ("R", 80.5, 23.5, 0, "F"),
    "R50": ("R", 14.0, 14.5, 0, "F"),
    "R51": ("R", 26.5, 14.5, 0, "F"),
    "R60": ("R0402", 6.0, 27.8, 0, "F"),
    "R61": ("R0402", 9.4, 27.8, 0, "F"),
    "R62": ("R0402", 12.8, 27.8, 0, "F"),
    "R63": ("R0402", 16.2, 27.8, 0, "F"),
    "R64": ("R0402", 19.6, 27.8, 0, "F"),
    "R65": ("R0402", 23.0, 27.8, 0, "F"),
    "R66": ("R0402", 26.4, 27.8, 0, "F"),
    "RT1": ("NTC", 32.0, 12.0, 0, "F"),
    "SW1": ("SW", 88.0, 26.0, 0, "F"),
    "SW2": ("SW", 88.0, 22.0, 0, "F"),
    "TP1": ("TP", 64.0, 1.5, 0, "F"),
    "TP2": ("TP", 67.2, 1.5, 0, "F"),
    "TP3": ("TP", 70.4, 1.5, 0, "F"),
    "TP4": ("TP", 73.6, 1.5, 0, "F"),
    "TP5": ("TP", 76.8, 1.5, 0, "F"),
    "TP6": ("TP", 80.0, 1.5, 0, "F"),
    "TP7": ("TP", 83.2, 1.5, 0, "F"),
    "TP8": ("TP", 86.4, 1.5, 0, "F"),
    "U1": ("BQ24074", 52.0, 16.0, 0, "F"),
    "U10": ("ESP32-C3-MINI-1", 78.0, 36.5, 0, "F"),
    "U2": ("TPS7A2633", 45.0, 22.0, 0, "F"),
    "U3": ("DW01A", 61.0, 16.5, 0, "F"),
    "U4": ("FS8205A", 64.0, 25.0, 0, "F"),
}

# Courtyard half-extents measured from installed libraries (pcbnew files);
# custom footprints from the pcbnew-built geometry. Used by the
# generator-side overlap/keepout/thermal assertions.
SIZES = {
    "ESP32-C3-MINI-1": (6.6, 8.3), "SCD41": (5.55, 5.55),
    "BQ24074": (2.0, 2.0), "TPS7A2633": (1.5, 1.5),
    "DW01A": (2.15, 1.87), "FS8205A": (3.95, 1.86),
    "AO3401A": (2.03, 1.8), "AO3402": (2.03, 1.8), "BSS138": (2.03, 1.8),
    "USBLC6-2SC6": (2.15, 1.87), "USB_C_16P": (5.42, 4.64),
    "FPC-24": (9.15, 4.05), "BAT_HOLDER": (38.55, 10.33),
    "R": (1.58, 0.83), "R0402": (1.03, 0.57), "C": (1.58, 0.83),
    "C0402": (1.01, 0.56), "L": (1.58, 0.83), "D": (1.71, 1.05),
    "LED": (1.58, 0.83), "FUSE0603": (1.58, 0.83), "FUSE1206": (2.38, 1.23),
    "NTC": (1.58, 0.83), "SW": (2.9, 1.9), "TP": (1.1, 1.1),
    "MOUNT": (2.0, 2.0),
}


def parse_netlist(path):
    text = Path(path).read_text()
    sec = text[text.find("(nets"):]
    blocks = re.split(r"\t\t\(net\n", sec)
    out = {}
    for b in blocks[1:]:
        m = re.search(r'\(name "([^"]+)"\)', b)
        if not m:
            continue
        nodes = re.findall(r'\(ref "([^"]+)"\)\n\t\t\t\t\(pin "([^"]+)"\)', b)
        out.setdefault(m.group(1), set()).update(nodes)
    return out


def check_placement():
    errs = []
    # inside board (J1 bottom overhang + U10 top overhang by design)
    for ref, (fk, x, y, _rot, _side) in PLACE.items():
        if ref in ("J1", "U10"):
            continue
        hw, hh = SIZES[fk]
        if not (hw <= x <= 95 - hw and hh <= y <= 45 - hh):
            errs.append(f"{ref} outside board")
    # overlaps (skip BT1 back-side vs front parts? BT1 is back, still
    # keepout vs parts on front is allowed; check front-front only)
    front = [(r, PLACE[r]) for r in PLACE if PLACE[r][4] == "F"]
    for i in range(len(front)):
        for j in range(i + 1, len(front)):
            r1, (f1, x1, y1, _, _) = front[i]
            r2, (f2, x2, y2, _, _) = front[j]
            hw1, hh1 = SIZES[f1]
            hw2, hh2 = SIZES[f2]
            if abs(x1 - x2) < hw1 + hw2 and abs(y1 - y2) < hh1 + hh2:
                errs.append(f"overlap {r1}/{r2}")
    # antenna keepout x[70,86.5] y[30,46]: only U10 allowed
    for ref, (fk, x, y, _rot, _side) in PLACE.items():
        if ref == "U10":
            continue
        hw, hh = SIZES[fk]
        if x + hw > 70 and x - hw < 86.5 and y + hh > 30:
            errs.append(f"{ref} in antenna keepout")
    # holder top edge below keepout bottom (y<=30-4=26+hh)
    hx, hy = PLACE["BT1"][1], PLACE["BT1"][2]
    if hy + SIZES["BAT_HOLDER"][1] > 30:
        errs.append("holder intrudes keepout")
    # SCD41 bottom-front edge region
    sx, sy = PLACE["IC-SCD"][1], PLACE["IC-SCD"][2]
    if not (sx < 35 and sy < 12):
        errs.append("SCD41 not bottom-front")
    return errs


REF_SIDE_OVERRIDES: dict[str, object] = {
    "R40": "below", "R41": "below", "R42": "below", "R43": "below",
    "R22": "below", "R13": "below", "R23": "left",
    "R27": "below", "C21": "below", "R21": "below",
    "H1": "right", "H2": ("above", 0.5), "H3": "right", "H4": "left",
    "D22": "below", "R1": "above",
    "C60": "below", "C61": "below", "C62": "below", "C63": "below",
    "C64": "below", "C65": "below", "C66": "below", "C67": "below",
    "C72": "below", "D21": "below",
}

REF_POS: dict[str, tuple[float, float]] = {}


def main():
    import pcbnew
    errs = check_placement()
    if errs:
        print("PLACEMENT ERRORS:")
        for e in errs:
            print("  -", e)
        raise SystemExit(1)
    print(f"placement: {len(PLACE)} refs, overlap/keepout/thermal clean")
    netlist = parse_netlist(HERE / "build" / "netlist.net")
    # net -> {(ref, pin)}
    board = pcbnew.CreateEmptyBoard()
    board.SetCopperLayerCount(2)
    # outline: single rectangle (shared segment endpoints count as
    # overlaps, so four segments are not used)
    mm = 1000000
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(pcbnew.VECTOR2I(int(0 * mm), int(0 * mm)))
    s.SetEnd(pcbnew.VECTOR2I(int(95 * mm), int(-45 * mm)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(int(0.1 * mm))
    s.SetFilled(False)
    board.Add(s)
    netcache = {}

    def get_net(name):
        if name in netcache:
            return netcache[name]
        net = board.FindNet(name)
        if net is None:
            net = pcbnew.NETINFO_ITEM(board, name)
            board.Add(net)
        netcache[name] = net
        return net

    import gen_sch
    for ref, (fk, x, y, rot, side) in PLACE.items():
        fps = gen_sch.footprint_for(ref, gen_sch.sym_for(ref))
        libname, fpname = fps.split(":", 1)
        if libname == "co2-node":
            fp = pcbnew.FootprintLoad(str(HERE / "fp" / "co2-node.pretty"),
                                      fpname)
        else:
            fp = pcbnew.FootprintLoad(f"{SYS_FP}/{libname}.pretty", fpname)
        if fp is None:
            raise SystemExit(f"footprint not found: {fps} for {ref}")
        board.Add(fp)
        fp.SetFPID(pcbnew.LIB_ID(libname, fpname))
        fp.SetPosition(pcbnew.VECTOR2I(int(x * mm), int(-y * mm)))
        fp.SetOrientationDegrees(rot)
        if side == "B":
            fp.SetLayerAndFlip(pcbnew.B_Cu)
        v, _fp0, mpn, mfr, notes = BOM[ref]
        fp.SetReference(ref)
        fp.SetValue(v)
        if fk in ("SCD41", "BQ24074", "TPS7A2633"):
            fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_SMD)
        attrs = fp.GetAttributes() & ~pcbnew.FP_EXCLUDE_FROM_BOM
        if ref in DNP:
            attrs |= pcbnew.FP_DNP
        if fk == "TP":
            attrs &= ~pcbnew.FP_EXCLUDE_FROM_POS_FILES
        fp.SetAttributes(attrs)
        fp.SetField("MPN", mpn)
        fp.SetField("Manufacturer", mfr)
        fp.SetField("Notes", notes)
        # BOM fields live on F.Fab (hidden); F.SilkS is for refs only.
        for fname in ("MPN", "Manufacturer", "Notes"):
            fld = fp.GetField(fname)
            if fld is not None:
                fld.SetLayer(pcbnew.F_Fab)
                fld.SetVisible(False)
        # Silk layout: values hidden (BOM/pos carry values); references
        # 0.8 mm tucked above each part to survive dense placement.
        val = fp.Value()
        val.SetVisible(False)
        reffield = fp.Reference()
        reffield.SetVisible(True)
        reffield.SetTextSize(pcbnew.VECTOR2I(int(0.8 * mm), int(0.8 * mm)))
        reffield.SetTextThickness(int(0.12 * mm))
        hw, hh = SIZES[fk]
        # pass 1 choice recorded; pass 2 (after loop) resolves ref/ref
        # collisions deterministically (see REF_SIDE_OVERRIDES).
        above = y + hh + 1.0
        below = y - hh - 1.0

        def hits(ry):
            n = 0
            for r2, (fk2, x2, y2, _rt2, _sd2) in PLACE.items():
                if r2 == ref:
                    continue
                hw2, hh2 = SIZES[fk2]
                if abs(x - x2) < hw2 + 1.6 and abs(ry - y2) < hh2 + 0.6:
                    n += 1
            return n

        ry = above if hits(above) <= hits(below) else below
        rx = x
        if ref in REF_SIDE_OVERRIDES:
            spec = REF_SIDE_OVERRIDES[ref]
            side, extra = spec if isinstance(spec, tuple) else (spec, 0.0)
            if side in ("left", "right"):
                rx = x - hw - 2.2 if side == "left" else x + hw + 2.2
                ry = y
            else:
                ry = y + hh + 1.0 + extra if side == "above" else y - hh - 1.0 - extra
        reffield.SetPosition(pcbnew.VECTOR2I(int(rx * mm), int(-ry * mm)))
        REF_POS[ref] = (rx, ry)
        # pad nets
        for pad in fp.Pads():
            num = pad.GetNumber()
            for netname, nodes in netlist.items():
                if netname.startswith("unconnected"):
                    continue
                if (ref, num) in nodes:
                    found = netname
                    break
            if found is None and (ref, num) in MECH_NETS:
                found = MECH_NETS[(ref, num)]
            if found is None:
                # Designed floating: schematic "" pins (DNC/NC/SBU/DNP/
                # TMR/ITERM), footprint "" mechanical pads, Keystone extra
                # THT. Anything else is a netmap omission — fail loudly.
                expected = (
                    num == ""
                    or NETS.get(ref, {}).get(num, "X") == ""
                )
                if not expected:
                    raise SystemExit(f"netless pad not in netmap: {ref} {num}")
                continue
            pad.SetNet(get_net(found))
    # keepout: antenna rule area both layers. Tracks/vias/pours banned;
    # pads and footprints allowed (the module itself lives in its keepout).
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetLayer(layer)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        for cx, cy in [(70, 30), (86.5, 30), (86.5, 46), (70, 46)]:
            z.AppendCorner(pcbnew.VECTOR2I(int(cx * mm), int(-cy * mm)), -1)
        board.Add(z)
    # Deterministic uuids: pcbnew mints fresh random uuids on every load,
    # so overwrite them with stable uid()s. Regeneration is byte-identical.
    import uuid as _uuid

    def _set_uuid(obj, *parts):
        u = str(_uuid.uuid5(_uuid.NAMESPACE_URL,
                            "co2-node:" + "/".join(parts)))
        obj.SetUuid(pcbnew.KIID(u))

    for fp in board.Footprints():
        r = fp.GetReference()
        _set_uuid(fp, "pcb", r)
        for i, pad in enumerate(fp.Pads()):
            _set_uuid(pad, "pcb", r, "pad", str(i))
        for i, d in enumerate(fp.GraphicalItems()):
            _set_uuid(d, "pcb", r, "shape", str(i))
        try:
            for i, z in enumerate(fp.Zones()):
                _set_uuid(z, "pcb", r, "fpzone", str(i))
        except Exception:
            pass
        for i, f in enumerate(fp.GetFields()):
            _set_uuid(f, "pcb", r, "field", f.GetName())
    for i, z in enumerate(board.Zones()):
        _set_uuid(z, "pcb", "zone", str(i))
    for d in board.GetDrawings():
        _set_uuid(d, "pcb", "drawing",
                  str(d.GetPosition().x), str(d.GetPosition().y))
    for n in board.GetNetsByName().values():
        _set_uuid(n, "pcb", "net", n.GetNetname())
    import uuid as _uuid2
    zone_uuid = str(_uuid2.uuid5(_uuid2.NAMESPACE_URL,
                                "co2-node:pcb:U10:fpzone:0"))
    pcbnew.SaveBoard(str(HERE / "co2-node.kicad_pcb"), board)
    import re as _re
    _p = HERE / "co2-node.kicad_pcb"
    _t = _p.read_text()
    _t, _n = _re.subn(r'(\(zone\n\t+\(layers "F\.Cu" "B\.Cu"\)\n\t+\(uuid ")[0-9a-f-]{36}(")',
                      r"\g<1>" + zone_uuid + r"\g<2>", _t, count=1)
    assert _n == 1, "antenna zone uuid normalize failed"
    _p.write_text(_t)
    print("pcb: saved co2-node.kicad_pcb")
    import json
    tpl = json.load(open("/usr/share/kicad/template/Arduino_Nano/Arduino_Nano.kicad_pro"))
    pro = dict(tpl)
    pro["meta"] = {"filename": "co2-node.kicad_pro", "version": 3}
    pro["net_settings"] = {
        "classes": [
            {"bus_width": 12, "clearance": 0.2, "diff_pair_gap": 0.25,
             "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2,
             "line_style": 0, "microvia_diameter": 0.3,
             "microvia_drill": 0.1, "name": "Default",
             "pcb_color": "rgba(0, 0, 0, 0.000)",
             "schematic_color": "rgba(0, 0, 0, 0.000)",
             "track_width": 0.25, "via_diameter": 0.6, "via_drill": 0.4,
             "wire_width": 6},
            {"bus_width": 12, "clearance": 0.25, "diff_pair_gap": 0.25,
             "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2,
             "line_style": 0, "microvia_diameter": 0.3,
             "microvia_drill": 0.1, "name": "Power",
             "pcb_color": "rgba(0, 0, 0, 0.000)",
             "schematic_color": "rgba(0, 0, 0, 0.000)",
             "track_width": 0.5, "via_diameter": 0.5, "via_drill": 0.5,
             "wire_width": 6,
             "nets": ["VBUS", "VSYS", "3V3", "P3V3", "BAT+", "GND"]},
        ],
        "meta": {"version": 4},
        "netclass_assignments": [], "netclass_patterns": [],
        "net_colors": None,
    }
    pro["sheets"] = []
    (HERE / "co2-node.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
    print("pcb: wrote co2-node.kicad_pro")


if __name__ == "__main__":
    main()
