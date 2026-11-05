#!/usr/bin/env python3
"""Generate the co2-node KiCad 9 project skeleton (Phase 1).

Deterministic source of truth for project structure. Phase 2 extends the
SHEETS dict with full netlists; the generator is re-run, never hand-edited
output. Run: python3 tools/gen_kicad.py  (from hardware/co2-node/)
Requires: KiCad 9 (s-expr versions 20250114 / 20241229). No KiCad needed
to run the generator itself.
"""
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # hardware/co2-node/
REV = "A"
DATE = "2026-11-05"
COMPANY = "autohome"

# Sheet name -> (file, title, phase note). Phase 2 replaces note with netlist.
SHEETS = {
    "power": ("power.kicad_sch", "Power: USB-C, BQ24074, TPS7A26, protection, gate, divider"),
    "mcu": ("mcu.kicad_sch", "MCU: ESP32-C3-MINI-1-N4, USB, BOOT/RESET, decoupling, test pads"),
    "sensor": ("sensor.kicad_sch", "Sensor: SCD41-D-R2, ferrite, pull-ups, DNC float"),
    "display": ("display.kicad_sch", "Display: FPC-24 + WeAct boost (SSD1681), 3V3-fed, no ME6216"),
    "connectors": ("connectors.kicad_sch", "Connectors: 18650 holder, NTC, test pads, mounting, label"),
}

# Net id -> name. Net 0 is KiCad's unconnected placeholder.
NETS = ["GND", "VSYS", "3V3", "P3V3", "BAT+", "VBAT_SENSE",
        "I2C_SDA", "I2C_SCL", "EPD_SDA", "EPD_SCL", "EPD_CS",
        "EPD_DC", "EPD_RES", "EPD_BUSY", "PWR_EN", "USB_DM",
        "USB_DP", "BOOT_N", "RESET_N", "CHG_STAT", "TS_NTC"]


def U():
    return uuid.uuid4()


def title_block(title):
    return (f'(title_block (title "{title}") (date "{DATE}") (rev "{REV}") '
            f'(company "{COMPANY}"))')


def sheet_stub(name, fname, title):
    return f"""(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0")
  (uuid "{U()}")
  (paper "A3")
  {title_block(f"CO2 node rev {REV} - {title}")}
  (text "SHEET: {name} ({fname})\\nPhase 2: full netlist per hardware/co2-node/README.md.\\nDo not hand-edit: regenerate via tools/gen_kicad.py."
    (at 30 30 0) (effects (font (size 2 2))) (uuid "{U()}"))
)
"""


def root_sch():
    boxes = []
    x, y = 10.0, 10.0
    for name, (fname, title) in SHEETS.items():
        boxes.append(
            f'  (sheet (at {x:g} {y:g}) (size 110 70) (fields_autoplaced)\n'
            f'    (stroke (width 0.1524) (type solid)) (fill (color 255 255 255 0.0))\n'
            f'    (uuid "{U()}")\n'
            f'    (property "Sheetname" "{name}" (at {x:g} {(y - 2):g} 0)\n'
            f'      (effects (font (size 1.27 1.27))))\n'
            f'    (property "Sheetfile" "{fname}" (at {x:g} {(y - 0.5):g} 0)\n'
            f'      (effects (font (size 1.27 1.27))))\n'
            f'  )')
        x += 120.0
        if x > 380:
            x, y = 10.0, y + 90.0
    return f"""(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0")
  (uuid "{U()}")
  (paper "A2")
  {title_block(f"CO2 sensor node rev {REV} - root")}
{chr(10).join(boxes)}
)
"""


def pro_file():
    return f"""(kicad_pro (version 1)
  (general)
  (paper "A3")
  {title_block(f"CO2 sensor node rev {REV}")}
  (board (paper "A3"))
  (cvpcb (equivalence false))
)
"""


def pcb_file():
    nets = "\n".join(f'  (net {i} "{n}")' for i, n in enumerate([""] + NETS))
    return f"""(kicad_pcb (version 20241229) (generator "pcbnew") (generator_version "9.0")
  (uuid "{U()}")
  (general (thickness 1.6))
  (paper "A4")
  {title_block(f"CO2 sensor node rev {REV} - 95x45mm 2L ENIG")}
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "Drawings")
    (41 "Cmts.User" user "Comments")
    (42 "Eco1.User" user "Eco1")
    (43 "Eco2.User" user "Eco2")
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
  )
  (setup (pad_to_mask_clearance 0))
  (netclass "Default" ""
    (clearance 0.2) (trace_width 0.25)
    (via_dia 0.8) (via_drill 0.4) (uvia_dia 0.3) (uvia_drill 0.1))
  (netclass "Power" ""
    (clearance 0.25) (trace_width 0.5)
    (via_dia 0.9) (via_drill 0.5) (uvia_dia 0.3) (uvia_drill 0.1)
    (add_net "VSYS") (add_net "3V3") (add_net "P3V3") (add_net "BAT+") (add_net "GND"))
{nets}
  (gr_rect (start 0 0) (end 95 45)
    (stroke (width 0.1) (type solid)) (fill none) (layer "Edge.Cuts") (uuid "{U()}"))
)
"""


def sym_lib():
    return """(kicad_symbol_lib (version 7) (generator "eeschema") (generator_version "9.0"))
"""


def main():
    (HERE / "co2-node.kicad_sch").write_text(root_sch())
    (HERE / "co2-node.kicad_pro").write_text(pro_file())
    (HERE / "co2-node.kicad_pcb").write_text(pcb_file())
    for name, (fname, title) in SHEETS.items():
        (HERE / fname).write_text(sheet_stub(name, fname, title))
    (HERE / "sym" / "co2-node.kicad_sym").write_text(sym_lib())
    (HERE / "fp-lib-table").write_text(
        "(fp_lib_table (version 7)\n"
        '  (lib (name "co2-node") (type "KiCad") '
        '(uri "${KIPRJMOD}/fp/co2-node.pretty") (options "") (descr "Local footprints"))\n'
        ")\n")
    (HERE / "sym-lib-table").write_text(
        "(sym_lib_table (version 7)\n"
        '  (lib (name "co2-node") (type "KiCad") '
        '(uri "${KIPRJMOD}/sym/co2-node.kicad_sym") (options "") (descr "Local symbols"))\n'
        ")\n")
    for d in ("fp/co2-node.pretty", "gerbers", "bom"):
        (HERE / d).mkdir(parents=True, exist_ok=True)
    print(f"wrote project skeleton rev {REV} into {HERE}")


if __name__ == "__main__":
    main()
