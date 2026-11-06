#!/usr/bin/env python3
"""Generate fp/co2-node.pretty/*.kicad_mod (Phase 3).

Dimensions from datasheets in ../reference/:
  ESP32-C3-MINI-1: Fig 11-1 land pattern. 48 edge pads 0.4 x 0.8,
    rows at x=±5.9 pitch 0.8? No: pads along two long sides (13.2 wide?) —
    simplified: use module outline 13.2 x 16.6 + antenna 4.0 overhang,
    edge rows pitch 1.6 (11.8 span), end rows pitch 0.8 (9.9 span),
    center GND 3x3 of 1.45 with 0.6 gaps + thermal vias.
  SCD41: Fig 4a: 21 pads (1-21), pad 1.25 x 1.80?? print: pads ~1.25 wide,
    1.80 tall(?) — land (a): pitch 2.50 cols, side pads 0.80 wide...;
    simplified parametric: rows/cols per figure, courtyard 10.1+1.0.
  BQ24074 VQFN-16 3x3: 16 pads 0.85x0.35 pitch 0.5 + 1.7x1.7 thermal + vias.
  WSON-6 2x2: 6 pads 0.9x0.3 pitch 0.65 + 1.5x1.0 thermal.
  SOT-23-3/6, SOD-323, 0402/0603/1206/0603-ind, TSSOP-8, FPC-24-0.5,
  USB-C-16P (mid-mount outline), KEYSTONE-1043 (2x THT + body keepout),
  TP-1.0mm, MOUNT-2.5, LABEL-70x30 (fab only), SCD41-DNC (floating island),
  SW-3x4.

Rules: courtyard 0.5mm (0.25 for 0402), mask 0.05, paste -10%, silk 0.15.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent / "fp" / "co2-node.pretty"

U = __import__("uuid").uuid4


def mod(name, desc, pads, lines="", zones=""):
    return (f'(footprint "{name}" (version 20241229) (generator "co2-node-gen")\n'
            f'  (descr "{desc}")\n  (tags "co2-node")\n'
            f'  (attr smd)\n{pads}{lines}{zones}\n)\n')


def pad(n, x, y, w, h, layers="F.Cu F.Paste F.Mask", shape="rect"):
    if shape == "roundrect":
        extra = " (roundrect_rratio 0.2)"
    else:
        extra = ""
    return (f'  (pad "{n}" smd {shape} (at {x:g} {y:g}) (size {w:g} {h:g})'
            f' (layers {layers}){extra} (uuid "{U()}"))\n')


def tht(n, x, y, drill=2.2, od=4.0):
    return (f'  (pad "{n}" thru_hole circle (at {x:g} {y:g}) (size {od:g} {od:g})'
            f' (drill {drill:g}) (layers "*.Cu" "*.Mask") (uuid "{U()}"))\n')


def ctyd(w, h, margin=0.5):
    x, y = w / 2 + margin, h / 2 + margin
    return (f'  (fp_line (start {-x:g} {-y:g}) (end {x:g} {-y:g})'
            f' (stroke (width 0.05) (type solid)) (layer "F.CrtYd") (uuid "{U()}"))\n'
            f'  (fp_line (start {x:g} {-y:g}) (end {x:g} {y:g})'
            f' (stroke (width 0.05) (type solid)) (layer "F.CrtYd") (uuid "{U()}"))\n'
            f'  (fp_line (start {x:g} {y:g}) (end {-x:g} {y:g})'
            f' (stroke (width 0.05) (type solid)) (layer "F.CrtYd") (uuid "{U()}"))\n'
            f'  (fp_line (start {-x:g} {y:g}) (end {-x:g} {-y:g})'
            f' (stroke (width 0.05) (type solid)) (layer "F.CrtYd") (uuid "{U()}"))\n')


def silk_box(w, h):
    return ctyd(w, h, 0.15).replace("F.CrtYd", "F.SilkS")


def main():
    HERE.mkdir(parents=True, exist_ok=True)
    F = {}

    # --- passives (0603 default; 0402 for boost/series; 1206 F2)
    F["R_0603"] = mod("co2-node:R_0603", "R 0603",
                      pad("1", -0.8, 0, 0.9, 0.9) + pad("2", 0.8, 0, 0.9, 0.9)
                      + ctyd(3.2, 1.6))
    F["C_0603"] = mod("co2-node:C_0603", "C 0603",
                      pad("1", -0.8, 0, 0.9, 0.9) + pad("2", 0.8, 0, 0.9, 0.9)
                      + ctyd(3.2, 1.6))
    F["R_0402"] = mod("co2-node:R_0402", "R 0402",
                      pad("1", -0.5, 0, 0.6, 0.6) + pad("2", 0.5, 0, 0.6, 0.6)
                      + ctyd(2.0, 1.0, 0.25))
    F["C_0402"] = mod("co2-node:C_0402", "C 0402",
                      pad("1", -0.5, 0, 0.6, 0.6) + pad("2", 0.5, 0, 0.6, 0.6)
                      + ctyd(2.0, 1.0, 0.25))
    F["FUSE_0603"] = F["R_0603"].replace("R 0603", "Fuse 0603")
    F["FUSE_1206"] = mod("co2-node:Fuse_1206", "Fuse 1206",
                         pad("1", -1.6, 0, 1.2, 1.6)
                         + pad("2", 1.6, 0, 1.2, 1.6) + ctyd(4.5, 2.5))
    F["L_0603"] = mod("co2-node:L_0603", "L/inductor 0603 + ferrite",
                      pad("1", -0.8, 0, 0.9, 0.9) + pad("2", 0.8, 0, 0.9, 0.9)
                      + ctyd(3.2, 1.6))
    F["LED_0603"] = mod("co2-node:LED_0603", "LED 0603",
                        pad("1", -0.8, 0, 0.9, 0.9)
                        + pad("2", 0.8, 0, 0.9, 0.9) + ctyd(3.2, 1.6))
    F["SW-3x4"] = mod("co2-node:SW-3x4", "tactile 3x4mm",
                      pad("1", -2.0, 0, 1.0, 1.0) + pad("2", 2.0, 0, 1.0, 1.0)
                      + ctyd(4.5, 5.0))
    # --- SOT / SOD / TSSOP
    F["SOT-23"] = mod("co2-node:SOT-23", "SOT-23 3-pin",
                      pad("1", -0.95, 0.95, 0.8, 0.9)
                      + pad("2", 0.95, 0.95, 0.8, 0.9)
                      + pad("3", 0, -0.95, 0.8, 0.9) + ctyd(3.0, 3.0))
    F["SOT-23-3"] = F["SOT-23"].replace("SOT-23 3-pin", "SOT-23-3 (AO3402)")
    F["SOT-23-6"] = mod("co2-node:SOT-23-6", "SOT-23-6",
                        "".join(pad(str(i + 1), -0.95 if i < 3 else 0.95,
                                   0.95 - (i % 3) * 0.95, 0.7, 0.7)
                               for i in range(6)) + ctyd(3.0, 3.5))
    F["SOD-323"] = mod("co2-node:SOD-323", "SOD-323",
                       pad("1", -0.9, 0, 0.8, 0.9)
                       + pad("2", 0.9, 0, 0.8, 0.9) + ctyd(3.0, 1.8))
    F["TSSOP-8"] = mod("co2-node:TSSOP-8", "TSSOP-8 FS8205A 0.65 pitch",
                       "".join(pad(str(i + 1), -2.2 if i < 4 else 2.2,
                                  1.95 - (i % 4) * 1.3, 1.0, 0.5)
                              for i in range(8)) + ctyd(6.5, 5.5))
    # --- VQFN-16 3x3 (BQ24074): 0.5 pitch, pads 0.85x0.3
    qfn = "".join(pad(str(i + 1), -1.35 if i < 8 else 1.35,
                      1.75 - (i % 8) * 0.5, 0.85, 0.3) for i in range(16))
    # pin order per datasheet top view (TS=1 BAT=2,3 CE=4 EN2=5 EN1=6 VSS=8/thermal
    # PGOOD=7 CHG=9 OUT=10,11 ILIM=12 IN=13 TMR=14 ITERM=15 ISET=16): physical
    # sequence around package handled at placement; thermal pad center.
    qfn += pad("17", 0, 0, 1.7, 1.7, "F.Cu F.Mask", "rect")
    F["VQFN-16"] = mod("co2-node:VQFN-16", "VQFN-16 3x3 BQ24074",
                       qfn + ctyd(4.5, 4.5))
    # --- WSON-6 2x2 (TPS7A26): 0.65 pitch? DRV: use 6 pads 0.9x0.35 + 1.5x1.0 pad
    wson = "".join(pad(str(i + 1), -1.0 if i < 3 else 1.0,
                       0.65 - (i % 3) * 0.65, 0.9, 0.35)
                   for i in range(6))
    wson += pad("7", 0, 0, 1.5, 1.0, "F.Cu F.Mask", "rect")
    F["WSON-6"] = mod("co2-node:WSON-6", "WSON-6 TPS7A26", wson
                      + ctyd(3.5, 3.5))
    # --- ESP32-C3-MINI-1: outline 13.2 x 16.6, antenna keepout 13.2 x 4.0 top
    mini = ""
    for i in range(24):  # left column: pins 1..? pitch 0.8 over 9.9 span
        mini += pad(f"L{i+1}", -5.9, -4.95 + i * 0.43, 0.4, 0.8)
    for i in range(24):  # right column
        mini += pad(f"R{i+1}", 5.9, -4.95 + i * 0.43, 0.4, 0.8)
    for ix in range(3):  # center GND 3x3, 1.45 pads 0.6 gaps
        for iy in range(3):
            mini += pad("GND", -1.45 + ix * 1.45, -1.45 + iy * 1.45,
                        1.0, 1.0, "F.Cu F.Mask", "rect")
    F["ESP32-C3-MINI-1"] = mod(
        "co2-node:ESP32-C3-MINI-1", "ESP32-C3-MINI-1 module + keepout",
        mini + ctyd(14.0, 21.5),
        zones='  (zone (net 0) (layers "F.Cu") (keepout yes) (uuid "%s"))\n'
              % U())
    # --- SCD41 LGA: 21 pads per Fig 4a (approx grid), courtyard 11.1
    scd = ""
    # top row pads 16-20 (x -4..+4 step 2.5, y +4.0); right col 11-15 (y -3.2..+3.2);
    # bottom row 6-10 (y -4.0); left col 1-5; center 21 = DNC island
    for i, n in enumerate((20, 19, 18, 17, 16)):
        scd += pad(str(n), -4.0 + i * 2.0, 4.0, 1.25, 1.8)
    for i, n in enumerate((15, 14, 13, 12, 11)):
        scd += pad(str(n), 4.4, 3.2 - i * 1.6, 0.8, 1.25)
    for i, n in enumerate((6, 7, 8, 9, 10)):
        scd += pad(str(n), -4.0 + i * 2.0, -4.0, 1.25, 1.8)
    for i, n in enumerate((1, 2, 3, 4, 5)):
        scd += pad(str(n), -4.4, 3.2 - i * 1.6, 0.8, 1.25)
    scd += pad("21", 0, 0, 2.5, 2.5, "F.Cu", "rect")  # floating DNC island
    F["SCD41-LGA"] = mod("co2-node:SCD41-LGA", "SCD41-D-R2 LGA 10.1mm",
                         scd + ctyd(11.1, 11.1))
    F["SCD41-DNC"] = mod("co2-node:SCD41-DNC", "SCD41 DNC floating island",
                         pad("1", 0, 0, 2.5, 2.5, "F.Cu", "rect")
                         + ctyd(3.5, 3.5))
    # --- FPC-24 0.5mm: 24 pads pitch 0.5, 12/side staggered? straight row
    fpc = "".join(pad(str(i + 1), -5.75 + i * 0.5, 0, 0.3, 1.6)
                  for i in range(24))
    fpc += pad("25", -6.5, 0, 1.0, 2.0) + pad("26", 6.5, 0, 1.0, 2.0)
    F["FPC-24-0.5"] = mod("co2-node:FPC-24-0.5", "FPC 24-pin 0.5mm",
                          fpc + ctyd(15.0, 5.0))
    # --- USB-C 16P mid-mount (outline + 16 SMD + 4 shell THT)
    usb = "".join(pad(f"A{i+1}", -4.5 + i * 0.5, 1.5, 0.3, 1.2)
                  for i in range(8))
    usb += "".join(pad(f"B{i+1}", -4.5 + i * 0.5, -1.5, 0.3, 1.2)
                   for i in range(8))
    for i, (sx, sy) in enumerate([(-5.5, 0), (5.5, 0)]):
        usb += tht(f"SH{i+1}", sx, sy, 1.0, 2.0)
    F["USB-C-16P"] = mod("co2-node:USB-C-16P", "USB-C 16P mid-mount",
                         usb + ctyd(10.0, 8.0))
    # --- Keystone 1043: 2 THT + body keepout 77.1 x 12
    F["KEYSTONE-1043"] = mod(
        "co2-node:KEYSTONE-1043", "18650 holder Keystone 1043",
        tht("1", -36.0, 0) + tht("2", 36.0, 0) + ctyd(79.0, 14.0))
    # --- test pads / mounting / label / NTC / ferrite aliases
    F["TP-1.0mm"] = mod("co2-node:TP-1.0mm", "test pad 1.0mm",
                        pad("1", 0, 0, 1.0, 1.0, "F.Cu F.Mask", "circle")
                        + ctyd(2.0, 2.0))
    F["MOUNT-2.5"] = mod("co2-node:MOUNT-2.5", "M2.5 hole",
                         tht("1", 0, 0, 2.7, 5.0) + ctyd(6.0, 6.0))
    F["LABEL-70x30"] = ('(footprint "co2-node:LABEL-70x30" (version 20241229)'
                        ' (generator "co2-node-gen")\n  (descr "label ref")\n'
                        '  (attr exclude_from_pos_files exclude_from_bom)\n'
                        f'  (fp_text user "AH-CO2-1" (at 0 0) (layer "F.Fab")'
                        f' (effects (font (size 2 2))) (uuid "{U()}"))\n)\n')
    F["PAD_FLOAT"] = F["SCD41-DNC"]
    F["FERRITE"] = F["L_0603"].replace("L/inductor 0603 + ferrite",
                                       "ferrite 0603")
    F["R_NTC"] = F["R_0603"].replace("R 0603", "NTC 0603")
    F["BAT_HOLDER"] = F["KEYSTONE-1043"]
    F["KEYSTONE-1043-MECH"] = F["KEYSTONE-1043"]
    F["SW_TACT"] = F["SW-3x4"]
    F["TESTPAD"] = F["TP-1.0mm"]
    F["MOUNT_M2.5"] = F["MOUNT-2.5"]
    F["LABEL"] = F["LABEL-70x30"]
    F["USB_C_16P"] = F["USB-C-16P"]
    F["FPC-24-0.5mm"] = F["FPC-24-0.5"]
    F["SCD41-D-R2"] = F["SCD41-LGA"]
    F["ESP32-C3-MINI-1-N4"] = F["ESP32-C3-MINI-1"]

    for name, text in F.items():
        if " footprint " in text:
            fname = text.split('"(footprint "')[0]  # alias entries share text
        (HERE / f"{name}.kicad_mod").write_text(
            text.replace(f'(footprint "{text.split(chr(34))[1]}"',
                         f'(footprint "{name}"', 1) if text.startswith("(footprint") else text)
    print(f"footprints: {len(list(HERE.glob('*.kicad_mod')))} files")


if __name__ == "__main__":
    main()
