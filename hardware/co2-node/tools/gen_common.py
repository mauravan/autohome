#!/usr/bin/env python3
"""Shared emit helpers for gen_power/gen_mcu/gen_sensor/gen_display/gen_connectors."""
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

NETS = ["GND", "VBUS", "VSYS", "3V3", "P3V3", "BAT+", "CELL+",
        "CELL_F", "BAT_RAW", "PACK-", "DW_VCC", "DW_OD", "DW_OC", "DW_VM",
        "VBAT_SENSE", "BAT_SENSE_RAW", "I2C_SDA", "I2C_SCL", "SCD_VDD",
        "DNC_A", "EPD_SDA", "EPD_SCL", "EPD_CS", "EPD_DC", "EPD_RES",
        "EPD_BUSY", "E_BS", "E_VGL", "E_VGH", "E_GDR", "E_RESR", "E_MID",
        "EPD_P7", "EPD_P8", "EPD_P9", "EPD_P10", "EPD_P20",
        "E_SDA_P", "E_SCL_P", "E_CS_P", "E_DC_P", "E_RES_P", "E_BUSY_P",
        "Q1_S", "Q3_G", "VDD33F", "SW",
        "PWR_EN", "USB_DM", "USB_DP", "USB_DN", "USB_CC1", "USB_CC2",
        "BOOT_N", "RESET_N", "STRAP2", "STRAP8",
        "CHG_STAT", "PG_STAT", "PG_3V3", "TS_NTC", "ISET_MON"]

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


def txt(s, x, y, size=1.27):
    return (f'  (text "{s}" (at {x:g} {y:g} 0) (effects (font (size {size:g} {size:g})))'
            f' (uuid "{U()}"))')

def gnd(x, y):
    return (f'  (symbol (lib_id "power:GND") (at {x:g} {y:g} 0) (unit 1)'
            f' (in_bom no) (on_board yes) (fields_autoplaced) (uuid "{U()}")'
            f' (property "Reference" "#PWR" (at {x:g} {(y + 2):g} 0) (effects (font (size 1.27 1.27)) hide yes))'
            f' (property "Value" "GND" (at {x:g} {(y + 2):g} 0) (effects (font (size 1.27 1.27))))'
            f' (pin "1:GND" (uuid "{U()}")))')


def nc(x, y):
    return (f'  (no_connect (at {x:g} {y:g}) (effects (font (size 1.27 1.27)))'
            f' (uuid "{U()}"))')
