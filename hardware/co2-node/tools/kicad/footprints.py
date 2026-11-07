#!/usr/bin/env python3
"""Footprint mapping + custom footprint builder (run with /usr/bin/python3).

Maps each BOM footprint string to ("lib", dir, name) for installed parts or
("custom", builder) for SCD41 LGA, BQ24074 VQFN-16, TPS7A26 WSON-6, Keystone
1043. Custom footprints are built through pcbnew (FOOTPRINT/PAD/PCB_SHAPE)
so the API emits a correct file. Validate: kicad-cli fp upgrade -o build/fpcheck fp/co2-node.pretty.

Custom pad coordinates are transcribed from the datasheet figures; see
../schematic-notes.md (reviewer: diff against the figures).
"""
import sys
from pathlib import Path

SYS_FP = "/usr/share/kicad/footprints"

# ref -> (kind, arg). kind "sys": (subdir, name); "custom": builder name.
FOOTPRINTS = {
    # NOTE: no C3-MINI-1 in libs; C6-MINI-1 is the same MINI-1 family/land pattern.
    "ESP32-C3-MINI-1": ("sys", "RF_Module", "ESP32-C6-MINI-1"),
    "BQ24074": ("custom", "BQ24074-VQFN-16"),
    "TPS7A2633": ("custom", "TPS7A26-WSON-6"),
    "DW01A": ("sys", "Package_TO_SOT_SMD", "SOT-23-6"),
    "FS8205A": ("sys", "Package_SO", "TSSOP-8_4.4x3mm_P0.65mm"),
    "AO3401A": ("sys", "Package_TO_SOT_SMD", "SOT-23"),
    "AO3402": ("sys", "Package_TO_SOT_SMD", "SOT-23"),
    "BSS138": ("sys", "Package_TO_SOT_SMD", "SOT-23"),
    "USBLC6-2SC6": ("sys", "Package_TO_SOT_SMD", "SOT-23-6"),
    "SCD41": ("custom", "SCD41-LGA"),
    "USB_C_16P": ("sys", "Connector_USB",
                  "USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A"),
    "FPC-24": ("sys", "Connector_FFC-FPC",
               "Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal"),
    "BAT_HOLDER": ("custom", "Keystone-1043"),
    "R": ("sys", "Resistor_SMD", "R_0603_1608Metric"),
    "R0402": ("sys", "Resistor_SMD", "R_0402_1005Metric"),
    "C": ("sys", "Capacitor_SMD", "C_0603_1608Metric"),
    "C0402": ("sys", "Capacitor_SMD", "C_0402_1005Metric"),
    "L": ("sys", "Inductor_SMD", "L_0603_1608Metric"),
    "D": ("sys", "Diode_SMD", "D_SOD-323"),
    "LED": ("sys", "LED_SMD", "LED_0603_1608Metric"),
    "FUSE0603": ("sys", "Fuse", "Fuse_0603_1608Metric"),
    "FUSE1206": ("sys", "Fuse", "Fuse_1206_3216Metric"),
    "NTC": ("sys", "Resistor_SMD", "R_0603_1608Metric"),
    "SW": ("sys", "Button_Switch_SMD", "SW_Push_1P1T_NO_CK_KMR2"),
    "TP": ("sys", "TestPoint", "TestPoint_Pad_1.0x1.0mm"),
    "MOUNT": ("sys", "MountingHole", "MountingHole_2.7mm_M2.5_Pad"),
}

HERE = Path(__file__).resolve().parent.parent.parent
OUT = HERE / "fp" / "co2-node.pretty"


def _padnum(pad):
    try:
        return int(pad.GetNumber())
    except (ValueError, TypeError):
        return pad.GetNumber()


def build_custom(name):
    import pcbnew
    mm = 1000000
    fp = pcbnew.FOOTPRINT(None)

    def smd(num, x, y, w, h, layers=("F.Cu", "F.Paste", "F.Mask")):
        p = pcbnew.PAD(fp)
        p.SetNumber(str(num))
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetShape(pcbnew.PAD_SHAPE_RECT)
        p.SetPosition(pcbnew.VECTOR2I(int(x * mm), int(y * mm)))
        p.SetSize(pcbnew.VECTOR2I(int(w * mm), int(h * mm)))
        layerset = pcbnew.LSET()
        for ln in layers:
            layerset.addLayer({
                "F.Cu": pcbnew.F_Cu, "F.Paste": pcbnew.F_Paste,
                "F.Mask": pcbnew.F_Mask, "B.Cu": pcbnew.B_Cu,
            }[ln])
        p.SetLayerSet(layerset)
        fp.Add(p)
        return p

    def tht(num, x, y, drill, od):
        p = pcbnew.PAD(fp)
        p.SetNumber(str(num))
        p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        p.SetPosition(pcbnew.VECTOR2I(int(x * mm), int(y * mm)))
        p.SetSize(pcbnew.VECTOR2I(int(od * mm), int(od * mm)))
        p.SetDrillSize(pcbnew.VECTOR2I(int(drill * mm), int(drill * mm)))
        layerset = pcbnew.LSET()
        layerset.addLayer(pcbnew.F_Cu)
        layerset.addLayer(pcbnew.B_Cu)
        layerset.addLayer(pcbnew.F_Mask)
        layerset.addLayer(pcbnew.B_Mask)
        p.SetLayerSet(layerset)
        fp.Add(p)
        return p

    def line(x1, y1, x2, y2, layer, width):
        s = pcbnew.PCB_SHAPE(fp)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(int(x1 * mm), int(y1 * mm)))
        s.SetEnd(pcbnew.VECTOR2I(int(x2 * mm), int(y2 * mm)))
        layerid = {"F.CrtYd": pcbnew.F_CrtYd, "F.SilkS": pcbnew.F_SilkS,
                   "F.Fab": pcbnew.F_Fab}[layer]
        s.SetLayer(layerid)
        s.SetWidth(int(width * mm))
        fp.Add(s)

    if name == "SCD41-LGA":
        # Sensirion SCD4x Fig 4a (p.19), top view mm: edge pads 1.9x0.85 @1.25
        # pitch; outer columns x=+-4.15 rows +-2.5; rows y=+-4.15 at 1.25 pitch;
        # center 4.8x4.8. Matches installed Sensirion_SCD4x footprint geometry.
        for i, n in enumerate(range(1, 6)):
            smd(n, -4.15, -2.5 + i * 1.25, 1.9, 0.85)
        for i, n in enumerate(range(11, 16)):
            smd(n, 4.15, 2.5 - i * 1.25, 1.9, 0.85)
        for i, n in enumerate((6, 7, 8, 9, 10)):
            smd(n, -2.5 + i * 1.25, 4.15, 0.85, 1.9)
        for i, n in enumerate((20, 19, 18, 17, 16)):
            smd(n, -2.5 + i * 1.25, -4.15, 0.85, 1.9)
        smd(21, 0, 0, 4.8, 4.8, layers=("F.Cu",))
        w, h = 10.1, 10.1
    elif name == "BQ24074-VQFN-16":
        # TI RGT0016C (p.52): 3.0x3.0, e=0.5, lead 0.30x0.85, EP 1.68 sq.
        # Pin 1 top-left, CCW: 1-4 left, 5-8 bottom, 9-12 right, 13-16 top.
        xs = -1.4625
        for i, n in enumerate((1, 2, 3, 4)):
            smd(n, xs, -0.75 + i * 0.5, 0.85, 0.24)
        for i, n in enumerate((5, 6, 7, 8)):
            smd(n, -0.75 + i * 0.5, 1.4625, 0.24, 0.85)
        for i, n in enumerate((9, 10, 11, 12)):
            smd(n, 1.4625, 0.75 - i * 0.5, 0.85, 0.24)
        for i, n in enumerate((13, 14, 15, 16)):
            smd(n, 0.75 - i * 0.5, -1.4625, 0.24, 0.85)
        smd(17, 0, 0, 1.2, 1.2, layers=("F.Cu", "F.Paste", "F.Mask"))
        w, h = 3.0, 3.0
    elif name == "TPS7A26-WSON-6":
        # TI DRV0006A (p.29-31): 2x2, e=0.65, lead ~0.375x0.40, EP 1.0x1.6.
        for i, n in enumerate((1, 2, 3)):
            smd(n, -0.8875, -0.65 + i * 0.65, 0.375, 0.40)
        for i, n in enumerate((6, 5, 4)):
            smd(n, 0.8875, -0.65 + i * 0.65, 0.375, 0.40)
        smd(7, 0, 0, 1.0, 1.6, layers=("F.Cu", "F.Paste", "F.Mask"))
        w, h = 2.0, 2.0
    elif name == "Keystone-1043":
        # Keystone M65 p.27 THM single cell: one + and one - pin on the
        # 55.2 center span, .145 [3.7] DIA; body 77.1x20.7; courtyard 86x24.
        tht(1, -27.6, 0, 3.7, 5.5)
        tht(2, 27.6, 0, 3.7, 5.5)
        w, h = 86.0, 24.0
    else:
        raise KeyError(name)
    if name in ("SCD41-LGA", "BQ24074-VQFN-16", "TPS7A26-WSON-6"):
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_SMD)
    # courtyard outline (single-segment outlines; KiCad takes one segment
    # per record)
    line(-w / 2 - 0.5, h / 2 + 0.5, w / 2 + 0.5, h / 2 + 0.5, "F.CrtYd", 0.05)
    line(w / 2 + 0.5, h / 2 + 0.5, w / 2 + 0.5, -h / 2 - 0.5, "F.CrtYd", 0.05)
    line(w / 2 + 0.5, -h / 2 - 0.5, -w / 2 - 0.5, -h / 2 - 0.5, "F.CrtYd", 0.05)
    line(-w / 2 - 0.5, -h / 2 - 0.5, -w / 2 - 0.5, h / 2 + 0.5, "F.CrtYd", 0.05)
    import uuid as _uuid
    _u = lambda *parts: str(_uuid.uuid5(
        _uuid.NAMESPACE_URL, "co2-node:" + "/".join(parts)))
    fp.SetUuid(pcbnew.KIID(_u("fp", name)))
    for i, pad in enumerate(fp.Pads()):
        pad.SetUuid(pcbnew.KIID(_u("fp", name, "pad", str(i))))
    for i, d in enumerate(fp.GraphicalItems()):
        d.SetUuid(pcbnew.KIID(_u("fp", name, "shape", str(i))))
    for f in fp.GetFields():
        f.SetUuid(pcbnew.KIID(_u("fp", name, "field", f.GetName())))
    return fp


def main():
    import pcbnew
    OUT.mkdir(parents=True, exist_ok=True)
    for _sym, spec in sorted(FOOTPRINTS.items()):
        if spec[0] != "custom":
            continue
        fp = build_custom(spec[1])
        fp.SetFPID(pcbnew.LIB_ID("co2-node", spec[1]))
        b = pcbnew.CreateEmptyBoard()
        b.Add(fp)
        tmp = OUT / f".{spec[1]}.kicad_pcb"
        pcbnew.SaveBoard(str(tmp), b)
        text = tmp.read_text()
        start = text.find('(footprint "')
        depth, end = 0, None
        for i in range(start, len(text)):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        body = text[start:end]
        import re
        body = re.sub(r"\n\t\t\(at [^)]*\)", "", body, count=1)
        body = re.sub(r'\n\t\t\(layer "[^"]*"\)', "", body, count=1)
        body = re.sub(r"\n\t\t\(uuid \"[^\"]*\"\)", "", body, count=1)
        body = re.sub(r"\n\t\t\(tstamp [^)]*\)", "", body, count=1)
        if spec[1] in ("SCD41-LGA", "BQ24074-VQFN-16", "TPS7A26-WSON-6"):
            body = body.replace(f'(footprint "{spec[1]}"',
                                f'(footprint "{spec[1]}"\n\t(attr smd)', 1)
        (OUT / f"{spec[1]}.kicad_mod").write_text(body + "\n")
        tmp.unlink()
        print(f"fp: {spec[1]} ({len(fp.Pads())} pads)")
    import glob
    print("custom files:", sorted(glob.glob(str(OUT / "*.kicad_mod"))))


if __name__ == "__main__":
    main()
