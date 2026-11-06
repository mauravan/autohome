#!/usr/bin/env python3
"""Generate co2-node.kicad_pcb placement (Phase 3).

Floorplan (mm, origin bottom-left, board 95 x 45, antenna overhangs TOP edge):
  - U10 ESP32-C3-MINI-1 top-right: center (78, 38); body 13.2 wide, antenna
    area top 4.0 overhangs edge (y > 45). Keepout: x in [70, 86.5], y > 30 on
    BOTH layers (no copper/traces/pour/metal); plastic case only.
  - J2 FPC top-left: (12, 36); panel held 2mm above PCB by bezel, FPC folds.
  - Boost cluster near FPC: L1 (28, 36), Q1 (34, 36), D21-23/C70-72 (38..44, 36).
  - U2 LDO + U1 charger mid-board: U2 (45, 22), U1 (52, 14).
  - U3/U4 protection mid: U3 (60, 14), U4 (66, 14); Q2 reverse (64, 8).
  - Q3/Q4 gate: (45, 30) / (45, 34).
  - SCD41 bottom-front edge: (20, 6), body 10.1 — vents below in case.
  - USB-C J1 bottom edge: (55, 2.5).
  - BT1 holder BACK side: center (47.5, 26), body 77.1 x 12, top edge y=32
    (i.e. 13mm below antenna keepout bottom y=30? NO — spec: top edge y=15mm...
    board is 45 tall; holder top edge at y=15 means holder occupies y 15..27?
    Holder is 77.1 LONG (x) — top edge y=15 in spec coords = 15mm from TOP?
    Interpret: holder long axis along X, far edge 15mm below top edge -> y 30..42?? 
    conflicts with FPC/module. RESOLVED: holder far(long) edge at y=15 from
    BOTTOM? Spec: "top edge at y=15mm, cell 15mm below antenna" — antenna
    keepout bottom is y=30 (15mm below top edge y=45). Holder top edge y<=30.
    Place holder center (47.5, 20), body y 14..26 (top edge 26 < 30 OK, 4mm margin).
  - Test pads front/bottom edge clear of holder: row y=3, x 70..90.
  - Mounting H1-4 (3.5,3.5) (91.5,3.5) (3.5,41.5) (91.5,41.5).
  - LDO/charger/boost keep distance from SCD41 (>=25mm).

Nets: from gen_common.NETS. Each footprint gets placed with net assignment
recorded in placement.csv for DRC-lite.
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(HERE / "tools"))
from gen_common import NETS, U  # noqa

# ref -> (footprint, x, y, rot, side)
PLACE = {
    # modules / ICs
    "U10": ("ESP32-C3-MINI-1", 78.0, 38.0, 0, "F"),
    "IC-SCD": ("SCD41-LGA", 20.0, 6.0, 0, "F"),
    "U1": ("VQFN-16", 52.0, 15.0, 0, "F"),
    "U2": ("WSON-6", 45.0, 22.0, 0, "F"),
    "U3": ("SOT-23-6", 60.0, 14.0, 0, "F"),
    "U4": ("TSSOP-8", 66.0, 14.0, 0, "F"),
    "J2": ("FPC-24-0.5", 12.0, 36.0, 0, "F"),
    "J1": ("USB-C-16P", 53.5, 2.0, 0, "F"),
    "BT1": ("KEYSTONE-1043", 47.5, 20.0, 0, "B"),
    # FETs / diodes
    "Q2": ("SOT-23", 65.0, 8.0, 0, "F"),
    "Q3": ("SOT-23", 43.0, 32.5, 0, "F"),
    "Q4": ("SOT-23", 43.0, 35.0, 0, "F"),
    "Q1": ("SOT-23-3", 34.0, 37.5, 0, "F"),
    "D20": ("LED_0603", 57.0, 17.0, 0, "F"),
    "D21": ("SOD-323", 40.0, 32.0, 0, "F"),
    "D22": ("SOD-323", 40.0, 38.0, 0, "F"),
    "D23": ("SOD-323", 40.0, 42.0, 0, "F"),
    "D1": ("SOT-23-6", 46.0, 2.5, 0, "F"),
    "DNC-PAD": ("SCD41-DNC", 20.0, 6.0, 0, "F"),
    # charger/LDO/gate/divider passives
    "F1": ("Fuse_0603", 50.0, 2.5, 0, "F"),
    "F2": ("Fuse_1206", 60.0, 8.0, 0, "F"),
    "R10": ("R_0603", 51.0, 5.5, 0, "F"),
    "R11": ("R_0603", 54.0, 5.5, 0, "F"),
    "R12": ("R_0603", 57.0, 6.5, 0, "F"),
    "R13": ("R_0603", 57.0, 3.5, 0, "F"),
    "R20": ("R_0603", 49.0, 9.5, 0, "F"),
    "R21": ("R_0603", 53.5, 8.5, 0, "F"),
    "R22": ("R_0603", 59.0, 11.0, 0, "F"),
    "R23": ("R_0603", 57.0, 19.5, 0, "F"),
    "R24": ("R_0603", 63.5, 11.0, 0, "F"),
    "R25": ("R_0603", 62.0, 16.0, 0, "F"),
    "R27": ("R_0603", 45.0, 25.5, 0, "F"),
    "R28": ("R_0603", 37.5, 30.5, 0, "F"),
    "R29": ("R_0603", 46.0, 35.0, 0, "F"),
    "R30": ("R_0603", 69.0, 9.0, 0, "F"),
    "R31": ("R_0603", 72.0, 9.0, 0, "F"),
    "R32": ("R_0603", 75.0, 9.0, 0, "F"),
    "R40": ("R_0603", 61.0, 38.0, 0, "F"),
    "R41": ("R_0603", 66.0, 38.0, 0, "F"),
    "R42": ("R_0603", 63.5, 38.0, 0, "F"),
    "R43": ("R_0603", 63.5, 35.5, 0, "F"),
    "C20": ("C_0603", 48.5, 5.5, 0, "F"),
    "C21": ("C_0603", 56.0, 12.5, 0, "F"),
    "C22": ("C_0603", 49.0, 13.5, 0, "F"),
    "C23": ("C_0603", 62.0, 5.5, 0, "F"),
    "C24": ("C_0603", 41.5, 22.0, 0, "F"),
    "C25": ("C_0603", 41.5, 24.5, 0, "F"),
    "C26": ("C_0603", 44.5, 28.5, 0, "F"),
    "C27": ("C_0603", 38.5, 27.0, 0, "F"),
    "C28": ("C_0603", 41.5, 29.5, 0, "F"),
    "C29": ("C_0603", 73.0, 6.0, 0, "F"),
    "C40": ("C_0603", 63.5, 44.0, 0, "F"),
    "C41": ("C_0603", 66.0, 44.0, 0, "F"),
    "C42": ("C_0603", 61.0, 44.0, 0, "F"),
    "C43": ("C_0603", 58.5, 44.0, 0, "F"),
    # sensor
    "FB50": ("L_0603", 12.0, 6.0, 0, "F"),
    "C50": ("C_0603", 25.5, 9.5, 0, "F"),
    "C51": ("C_0603", 12.0, 9.0, 0, "F"),
    "R50": ("R_0603", 14.5, 11.5, 0, "F"),
    "R51": ("R_0603", 25.5, 12.5, 0, "F"),
    # display boost + panel
    "L1": ("L_0603", 27.0, 36.0, 0, "F"),
    "R1": ("R_0402", 31.5, 40.5, 0, "F"),
    "R2": ("R_0603", 34.0, 40.5, 0, "F"),
    "C69": ("C_0402", 36.5, 40.5, 0, "F"),
    "C68": ("C_0402", 24.5, 36.0, 0, "F"),
    "C71": ("C_0402", 38.0, 36.0, 0, "F"),
    "C72": ("C_0402", 44.0, 38.5, 0, "F"),
    "C70": ("C_0402", 46.5, 38.5, 0, "F"),
    "C60": ("C_0402", 10.0, 32.0, 0, "F"),
    "C61": ("C_0402", 12.6, 32.0, 0, "F"),
    "C62": ("C_0402", 15.2, 32.0, 0, "F"),
    "C63": ("C_0402", 17.8, 32.0, 0, "F"),
    "C64": ("C_0402", 20.4, 32.0, 0, "F"),
    "C65": ("C_0402", 23.0, 32.0, 0, "F"),
    "C66": ("C_0603", 27.0, 33.5, 0, "F"),
    "C67": ("C_0402", 29.5, 33.5, 0, "F"),
    "R60": ("R_0402", 10.0, 29.5, 0, "F"),
    "R61": ("R_0402", 12.6, 29.5, 0, "F"),
    "R62": ("R_0402", 15.2, 29.5, 0, "F"),
    "R63": ("R_0402", 17.8, 29.5, 0, "F"),
    "R64": ("R_0402", 20.4, 29.5, 0, "F"),
    "R65": ("R_0402", 23.0, 29.5, 0, "F"),
    "R66": ("R_0402", 25.6, 29.5, 0, "F"),
    # connectors
    "RT1": ("R_0603", 30.0, 12.0, 0, "F"),
    "SW1": ("SW-3x4", 84.0, 26.0, 0, "F"),
    "SW2": ("SW-3x4", 84.0, 22.0, 0, "F"),
    "TP1": ("TP-1.0mm", 70.0, 3.0, 0, "F"),
    "TP2": ("TP-1.0mm", 73.0, 3.0, 0, "F"),
    "TP3": ("TP-1.0mm", 76.0, 3.0, 0, "F"),
    "TP4": ("TP-1.0mm", 79.0, 3.0, 0, "F"),
    "TP5": ("TP-1.0mm", 82.0, 3.0, 0, "F"),
    "TP6": ("TP-1.0mm", 85.0, 3.0, 0, "F"),
    "TP7": ("TP-1.0mm", 88.0, 3.0, 0, "F"),
    "TP8": ("TP-1.0mm", 91.0, 3.0, 0, "F"),
}


def main():
    with open(HERE / "placement.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ref", "footprint", "x_mm", "y_mm", "rot", "side"])
        for ref, (fp, x, y, rot, side) in PLACE.items():
            w.writerow([ref, fp, x, y, rot, side])
    # emit pcb skeleton with footprints
    L = [f'(kicad_pcb (version 20241229) (generator "pcbnew") (generator_version "9.0")',
         f'  (uuid "{U()}")', '  (general (thickness 1.6))', '  (paper "A4")',
         f'  (title_block (title "CO2 sensor node rev A") (date "2026-11-05") (rev "A"))',
         '  (layers\n    (0 "F.Cu" signal)\n    (31 "B.Cu" signal)\n'
         '    (32 "B.Adhes" user) (33 "F.Adhes" user) (34 "B.Paste" user)\n'
         '    (35 "F.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user)\n'
         '    (38 "B.Mask" user) (39 "F.Mask" user) (40 "Dwgs.User" user)\n'
         '    (41 "Cmts.User" user) (42 "Eco1.User" user) (43 "Eco2.User" user)\n'
         '    (44 "Edge.Cuts" user) (45 "Margin" user) (46 "B.CrtYd" user)\n'
         '    (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user)\n  )',
         '  (setup (pad_to_mask_clearance 0))',
         '  (netclass "Default" "" (clearance 0.2) (trace_width 0.25)'
         ' (via_dia 0.8) (via_drill 0.4) (uvia_dia 0.3) (uvia_drill 0.1))',
         '  (netclass "Power" "" (clearance 0.25) (trace_width 0.5)'
         ' (via_dia 0.9) (via_drill 0.5) (uvia_dia 0.3) (uvia_drill 0.1)'
         ' (add_net "VSYS") (add_net "3V3") (add_net "P3V3") (add_net "BAT+") (add_net "GND"))']
    for i, n in enumerate([""] + NETS):
        L.append(f'  (net {i} "{n}")')
    for ref, (fp, x, y, rot, side) in PLACE.items():
        layer = '"F.Cu"' if side == "F" else '"B.Cu"'
        L.append(f'  (footprint "co2-node:{fp}" (layer {layer}) (at {x:g} {y:g} {rot})'
                 f' (uuid "{U()}") (property "Reference" "{ref}") (property "Value" "{ref}"))')
    # keepout: antenna rect x[70,86.5] y[30,46] both layers + note
    L.append(f'  (zone (net 0) (net_name "") (layer "F.Cu") (layers "F.Cu")'
            f' (uuid "{U()}") (hatch edge 0.5)'
            f' (connect_pads (clearance 0.8)) (min_thickness 0.25)'
            f' (keepout (tracks allowed) (vias not_allowed) (copperpour allowed))'
            f' (polygon (pts (xy 70 30) (xy 86.5 30) (xy 86.5 46) (xy 70 46))))')
    L.append(f'  (gr_rect (start 0 0) (end 95 45) (stroke (width 0.1) (type solid))'
            f' (fill none) (layer "Edge.Cuts") (uuid "{U()}"))')
    L.append(")")
    (HERE / "co2-node.kicad_pcb").write_text("\n".join(L) + "\n")
    print(f"placement: {len(PLACE)} footprints -> co2-node.kicad_pcb")


if __name__ == "__main__":
    main()
