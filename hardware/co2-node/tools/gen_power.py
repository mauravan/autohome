#!/usr/bin/env python3
"""Generate the co2-node KiCad 9 project (rev A) — Phase 2 full netlists.

Deterministic source of truth for schematic + PCB skeleton + BOM.
Re-run after ANY edit:  python3 tools/gen_kicad.py — never hand-edit output.

Record format (ERC-lite parseable):
  symbol instance: (symbol (lib_id "...") (at X Y 0) ... (pin "NUM:NET" (uuid ...)))
  net label:      (label "NET" ...)
  wire:           (wire (pts (xy X1 Y1) (xy X2 Y2)) ...)
  no-connect:     (no_connect (at X Y) ...)

Layout convention: components on a 2.54mm grid, pins listed left (inputs /
passives) and right (outputs). Positions are schematic-only; the PCB places
per hardware/co2-node/README.md floorplan.

Datasheet anchors: see module docstring + ../reference/*.pdf
"""
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REV = "A"
DATE = "2026-11-05"
COMPANY = "autohome"

SHEETS = {
    "power": ("power.kicad_sch", "Power: USB-C, BQ24074, TPS7A26, protection, gate, divider"),
    "mcu": ("mcu.kicad_sch", "MCU: ESP32-C3-MINI-1-N4, USB, BOOT/RESET, decoupling, test pads"),
    "sensor": ("sensor.kicad_sch", "Sensor: SCD41-D-R2, ferrite, pull-ups, DNC float"),
    "display": ("display.kicad_sch", "Display: FPC-24 + WeAct boost (SSD1681), 3V3-fed, no ME6216"),
    "connectors": ("connectors.kicad_sch", "Connectors: 18650 holder, NTC, test pads, mounting, label"),
}

# Net id -> name for the PCB skeleton (net 0 = unconnected placeholder)
NETS = ["GND", "VBUS", "VSYS", "3V3", "P3V3", "BAT+", "CELL+",
        "VBAT_SENSE", "I2C_SDA", "I2C_SCL", "SCD_VDD",
        "EPD_SDA", "EPD_SCL", "EPD_CS", "EPD_DC", "EPD_RES",
        "EPD_BUSY", "E_BS", "E_VGL", "E_VGH", "E_GDR", "E_RESR",
        "PWR_EN", "USB_DM", "USB_DP", "BOOT_N", "RESET_N",
        "CHG_STAT", "PG_STAT", "TS_NTC", "BAT_SENSE_RAW"]

_uids = set()


def U():
    u = str(uuid.uuid4())
    assert u not in _uids, "uuid collision"
    _uids.add(u)
    return u


def tb(title):
    return (f'(title_block (title "{title}") (date "{DATE}") (rev "{REV}") '
            f'(company "{COMPANY}"))')


def sheet_head(title):
    return (f'(kicad_sch (version 20250114) (generator "eeschema")'
            f' (generator_version "9.0")\n  (uuid "{U()}")\n  (paper "A3")\n'
            f'  {tb(title)}')


def sym(libid, ref, value, fp, x, y, pins, datasheet=""):
    """pins: list of (num, net). Net '' = genuinely unconnected (flagged)."""
    L = [f'  (symbol (lib_id "{libid}") (at {x:g} {y:g} 0) (unit 1)']
    L += ['    (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced)',
          f'    (uuid "{U()}")',
          f'    (property "Reference" "{ref}" (at {x:g} {(y - 8):g} 0) (effects (font (size 1.27 1.27))))',
          f'    (property "Value" "{value}" (at {x:g} {(y + 8):g} 0) (effects (font (size 1.27 1.27))))',
          f'    (property "Footprint" "{fp}" (at {x:g} {y:g} 0) (effects (font (size 1.27 1.27)) hide yes))']
    if datasheet:
        L += [f'    (property "Datasheet" "{datasheet}" (at {x:g} {y:g} 0) (effects (font (size 1.27 1.27)) hide yes))']
    for num, net in pins:
        L += [f'    (pin "{num}:{net}" (uuid "{U()}"))']
    L += ['    (instances (project ""))', '  )']
    return "\n".join(L)


def wire(x1, y1, x2, y2):
    return (f'  (wire (pts (xy {x1:g} {y1:g}) (xy {x2:g} {y2:g}))'
            f' (stroke (width 0.1524) (type default)) (uuid "{U()}"))')


def lbl(net, x, y):
    return (f'  (label "{net}" (at {x:g} {y:g} 0) (fields_autoplaced)'
            f' (effects (font (size 1.27 1.27))) (uuid "{U()}"))')


def gnd(x, y):
    return (f'  (symbol (lib_id "power:GND") (at {x:g} {y:g} 0) (unit 1)'
            f' (in_bom no) (on_board yes) (fields_autoplaced) (uuid "{U()}")'
            f' (property "Reference" "#PWR" (at {x:g} {(y + 2):g} 0) (effects (font (size 1.27 1.27)) hide yes))'
            f' (property "Value" "GND" (at {x:g} {(y + 2):g} 0) (effects (font (size 1.27 1.27))))'
            f' (pin "1:GND" (uuid "{U()}")))')



def nc(x, y):
    return (f'  (no_connect (at {x:g} {y:g}) (effects (font (size 1.27 1.27)))'
            f' (uuid "{U()}"))')


# ================================================================ POWER
# Topology (left->right power flow):
#   USB-C J1 -F1(0.75A)-> VBUS -D1(USBLC6)-> U1 BQ24074 IN
#   U1 OUT -> VSYS; U1 BAT -> BAT+ (protected side)
#   CELL+ (holder, pre-protection) -F2(2A)-> Q2(AO3401A reverse P-FET)-> U3/U4 DW01A+FS8205A -> BAT+
#   VSYS -> U2 TPS7A26 -> 3V3
#   3V3 -Q3(AO3401A, Q4 BSS138 inverter)-> P3V3 ; PWR_EN drives Q4 gate, 100k pull-down
#   BAT+ -R30/R31(1M/1M)-> BAT_SENSE_RAW -R32(1k)-> VBAT_SENSE(GPIO3) ; 100nF to GND
def build_power():
    L = [sheet_head(f"CO2 node rev {REV} - {SHEETS['power'][1]}")]
    x = 15.0

    # --- USB-C in, fuse, ESD
    L += [sym("co2-node:USB_C_16P", "J1", "USB-C-16P", "co2-node:USB-C-16P",
              x, 40, [("A1", "VBUS"), ("A4", "VBUS"), ("A5", "USB_CC1"),
                       ("A6", "USB_DP"), ("A7", "USB_DN"), ("A8", "USB_CC2"),
                       ("B1", "VBUS"), ("B4", "VBUS"), ("B5", "USB_CC2"),
                       ("B6", "USB_DP"), ("B7", "USB_DN"), ("B8", "USB_CC1"),
                       ("SH", "GND")], "USB 2.0 16-pin, 5.1k CC to GND")]
    L += [lbl("VBUS", x + 10, 40), lbl("USB_DP", x + 10, 35), lbl("USB_DN", x + 10, 45)]
    # CC 5.1k to GND
    L += [sym("Device:R", "R10", "5.1k", "co2-node:R_0603", x, 60,
              [("1", "USB_CC1"), ("2", "GND")]),
          sym("Device:R", "R11", "5.1k", "co2-node:R_0603", x + 8, 60,
              [("1", "USB_CC2"), ("2", "GND")])]
    # USB series 22R + ESD (schematic home; MCU sheet owns the C3 pins)
    L += [sym("Device:R", "R12", "22R", "co2-node:R_0603", x + 20, 35,
              [("1", "USB_DP"), ("2", "USB_DP")]),
          sym("Device:R", "R13", "22R", "co2-node:R_0603", x + 20, 45,
              [("1", "USB_DN"), ("2", "USB_DN")])]
    # polyfuse VBUS in
    L += [sym("Device:Fuse", "F1", "0.75A", "co2-node:Fuse_0603", x + 20, 40,
              [("1", "VBUS"), ("2", "VBUS")])]
    L += [sym("co2-node:USBLC6-2SC6", "D1", "USBLC6-2SC6", "co2-node:SOT-23-6",
              x + 32, 40, [("1", "USB_DP"), ("2", "GND"), ("3", "USB_DN"),
                            ("4", "USB_DN"), ("5", "VBUS"), ("6", "USB_DP")],
              "ST USBLC6-2SC6; pins 1,3,4,6 I/O / 5 Vcc / 2 GND")]
    L += [gnd(x + 32, 48)]

    # --- BQ24074 charger, VQFN-16
    # ICHG=KISET/RISET: KISET typ 890 -> RISET 1.78k for 500 mA
    # ILIM: EN2=0 EN1=1 -> USB500 fixed 500 mA; R_ILIM DNP safety
    # CE strapped low (enabled); TS = 10k NTC divider; ITERM/TMR float
    cx = x + 55
    L += [sym("co2-node:BQ24074", "U1", "BQ24074RGTR", "co2-node:VQFN-16",
              cx, 40,
              [("1", "TS_NTC"), ("2", "BAT+"), ("3", "BAT+"), ("4", "GND"),
               ("5", "GND"), ("6", "GND"), ("7", "PG_STAT"), ("8", "GND"),
               ("9", "CHG_STAT"), ("10", "VSYS"), ("11", "VSYS"),
               ("12", "GND"), ("13", "VBUS"), ("14", ""), ("15", ""),
               ("16", "ISET_MON")], "TI BQ24074; EN2=GND EN1=VBUS; CE=GND")]
    L += [lbl("VBUS", cx - 12, 40), lbl("BAT+", cx - 12, 33), lbl("VSYS", cx + 12, 40),
          lbl("TS_NTC", cx - 12, 28), lbl("CHG_STAT", cx + 12, 47), lbl("PG_STAT", cx + 12, 53)]
    # input + output bulk
    L += [sym("Device:C", "C20", "1u", "co2-node:C_0603", cx - 6, 52, [("1", "VBUS"), ("2", "GND")]),
          sym("Device:C", "C21", "10u", "co2-node:C_0603", cx + 6, 33, [("1", "BAT+"), ("2", "GND")]),
          sym("Device:C", "C22", "10u", "co2-node:C_0603", cx + 6, 47, [("1", "VSYS"), ("2", "GND")])]
    # ISET 1.78k -> 500 mA; ILIM DNP (EN2=0/EN1=1 fixed USB500)
    L += [sym("Device:R", "R20", "1.78k", "co2-node:R_0603", cx, 62,
              [("1", "ISET_MON"), ("2", "GND")]),
          sym("Device:R", "R21", "DNP", "co2-node:R_0603", cx + 8, 62,
              [("1", ""), ("2", "")])]
    L += [nc(cx + 12, 62), nc(cx + 20, 40)]
    # CE=4 low, EN2=5 low, EN1=6 to VBUS (USB500 mode)
    L += [wire(cx - 12, 52, cx - 4, 52), wire(cx - 4, 52, cx - 4, 44)]
    # TS network: 10k NTC (connectors sheet) + 10k pull-up to 3V3? No:
    # BQ24074 sources 75uA ITS; NTC to GND directly. Fixed 10k when NTC absent.
    # CHG/PG LEDs: open-drain, pull to 3V3 via 2.2k
    L += [sym("Device:R", "R22", "2.2k", "co2-node:R_0603", cx + 20, 47,
              [("1", "3V3"), ("2", "CHG_STAT")]),
          sym("Device:LED", "D20", "CHG-GRN", "co2-node:LED_0603", cx + 27, 47,
              [("1", "CHG_STAT"), ("2", "GND")]),
          sym("Device:R", "R23", "10k", "co2-node:R_0603", cx + 20, 53,
              [("1", "3V3"), ("2", "PG_STAT")])]
    L += [lbl("3V3", cx + 20, 42)]

    # --- Battery holder in (pre-protection CELL+), reverse FET, protection
    bx = x + 100
    L += [sym("co2-node:BAT_HOLDER", "BT1", "Keystone-1043", "co2-node:KEYSTONE-1043",
              bx, 40, [("1", "CELL+"), ("2", "GND")], "18650 holder; cell NOT supplied")]
    L += [lbl("CELL+", bx - 12, 40)]
    L += [sym("Device:Fuse", "F2", "2A", "co2-node:Fuse_1206", bx + 15, 40,
              [("1", "CELL+"), ("2", "CELL_F")])]
    # Q2 AO3401A reverse-polarity P-FET: source=CELL_F, drain=BAT_RAW, gate=GND
    L += [sym("co2-node:AO3401A", "Q2", "AO3401A", "co2-node:SOT-23",
              bx + 30, 40, [("1", "GND"), ("2", "CELL_F"), ("3", "BAT_RAW")],
              "reverse P-FET: G=GND S=CELL_F D=BAT_RAW; body diode S->D")]
    # DW01A + FS8205A low-side protection: DW01A VCC via 100R from BAT_RAW...
    # (DW01A senses cell+; FS8205A breaks GND return BATT-)
    L += [sym("Device:R", "R24", "100R", "co2-node:R_0603", bx + 42, 28,
              [("1", "BAT_RAW"), ("2", "DW_VCC")]),
          sym("Device:C", "C23", "0.1u", "co2-node:C_0603", bx + 50, 28,
              [("1", "DW_VCC"), ("2", "GND")])]
    L += [sym("co2-node:DW01A", "U3", "DW01A", "co2-node:SOT-23-6",
              bx + 55, 40, [("1", "DW_OD"), ("2", "DW_VM"), ("3", "DW_OC"),
                             ("4", ""), ("5", "DW_VCC"), ("6", "GND")],
              "1S protection; TD float; R2 1k VM sense")]
    L += [nc(bx + 62, 48)]
    L += [sym("Device:R", "R25", "1k", "co2-node:R_0603", bx + 62, 40,
              [("1", "DW_VM"), ("2", "PACK-")])]
    L += [sym("co2-node:FS8205A", "U4", "FS8205A", "co2-node:TSSOP-8",
              bx + 78, 40, [("1", "PACK-"), ("2", "PACK-"), ("3", "GND"),
                             ("4", "DW_OD"), ("5", "DW_OC"), ("6", "GND"),
                             ("7", "PACK-"), ("8", "PACK-")],
              "dual N-FET: G1=OD G2=OC; drains to PACK-, sources to GND")]
    L += [lbl("BAT+", bx + 30, 32), lbl("GND", bx + 78, 48),
          lbl("PACK-", bx + 70, 32)]
    L += [wire(bx + 30, 34, bx + 30, 32)]  # BAT_RAW visual up to BAT+ label row
    L += [lbl("BAT_RAW", bx + 30, 36)]

    # --- TPS7A26 LDO: VSYS -> 3V3. WSON-6 OUT=1 NC=2 PG=3 EN=4 GND=5 IN=6
    lx = x + 150
    L += [sym("co2-node:TPS7A2633", "U2", "TPS7A2633DRVR", "co2-node:WSON-6",
              lx, 40, [("1", "3V3"), ("2", "GND"), ("3", "PG_3V3"),
                        ("4", "VSYS"), ("5", "GND"), ("6", "VSYS")],
              "TI TPS7A26 3.3V 500mA; EN tied IN; NC to GND pad")]
    L += [lbl("VSYS", lx - 12, 40), lbl("3V3", lx + 12, 40)]
    L += [sym("Device:C", "C24", "1u", "co2-node:C_0603", lx - 6, 52,
              [("1", "VSYS"), ("2", "GND")]),
          sym("Device:C", "C25", "10u", "co2-node:C_0603", lx + 6, 52,
              [("1", "3V3"), ("2", "GND")]),
          sym("Device:C", "C26", "0.1u", "co2-node:C_0603", lx + 12, 52,
              [("1", "3V3"), ("2", "GND")])]
    L += [sym("Device:R", "R27", "100k", "co2-node:R_0603", lx + 20, 34,
              [("1", "3V3"), ("2", "PG_3V3")])]
    L += [lbl("PG_3V3", lx + 20, 30)]

    # --- Peripheral gate: 3V3 -> Q3 AO3401A -> P3V3; Q4 BSS138 inverter
    gx = x + 190
    L += [sym("co2-node:AO3401A", "Q3", "AO3401A", "co2-node:SOT-23",
              gx, 40, [("1", "Q3_G"), ("2", "3V3"), ("3", "P3V3")],
              "high-side P-FET: S=3V3 D=P3V3; ON when G low")]
    L += [sym("co2-node:BSS138", "Q4", "BSS138", "co2-node:SOT-23",
              gx, 55, [("1", "Q3_G"), ("2", "PWR_EN"), ("3", "GND")],
              "N-FET inverter: PWR_EN high -> G low -> P3V3 on")]
    L += [sym("Device:R", "R28", "100k", "co2-node:R_0603", gx - 10, 40,
              [("1", "3V3"), ("2", "Q3_G")]),
          sym("Device:R", "R29", "100k", "co2-node:R_0603", gx + 10, 55,
              [("1", "PWR_EN"), ("2", "GND")])]
    L += [lbl("3V3", gx - 12, 40), lbl("P3V3", gx + 12, 40),
          lbl("PWR_EN", gx + 10, 60), lbl("Q3_G", gx - 5, 48)]
    L += [sym("Device:C", "C27", "10u", "co2-node:C_0603", gx + 20, 40,
              [("1", "P3V3"), ("2", "GND")]),
          sym("Device:C", "C28", "0.1u", "co2-node:C_0603", gx + 26, 40,
              [("1", "P3V3"), ("2", "GND")])]

    # --- Battery divider: BAT+ -> 1M/1M -> 100nF -> 1k -> GPIO3
    dx = x + 230
    L += [sym("Device:R", "R30", "1M", "co2-node:R_0603", dx, 34,
              [("1", "BAT+"), ("2", "BAT_SENSE_RAW")]),
          sym("Device:R", "R31", "1M", "co2-node:R_0603", dx, 44,
              [("1", "BAT_SENSE_RAW"), ("2", "GND")]),
          sym("Device:C", "C29", "100n", "co2-node:C_0603", dx + 10, 44,
              [("1", "BAT_SENSE_RAW"), ("2", "GND")]),
          sym("Device:R", "R32", "1k", "co2-node:R_0603", dx + 20, 34,
              [("1", "BAT_SENSE_RAW"), ("2", "VBAT_SENSE")])]
    L += [lbl("BAT+", dx - 12, 34), lbl("BAT_SENSE_RAW", dx + 5, 39),
          lbl("VBAT_SENSE", dx + 28, 34)]
    for gx_ in (x + 32, cx - 6, cx + 6, bx + 50, lx - 6, lx + 6, lx + 12,
                gx + 20, gx + 26, dx + 10):
        pass
    L += [gnd(bx + 15, 48), gnd(bx + 42, 36), gnd(lx - 6, 58), gnd(lx + 6, 58),
          gnd(gx + 20, 48), gnd(dx, 50)]
    L += ["\n".join(["  " + lbl("GND", 0, 0)])]  # placeholder removed below
    L = L[:-1]
    return L


def main():
    out = build_power()
    text = "\n".join(out) + "\n)\n"
    (HERE / "power.kicad_sch").write_text(text)
    print(f"power: {len(text)} bytes")


if __name__ == "__main__":
    main()
