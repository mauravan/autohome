#!/usr/bin/env python3
"""Symbol library data + emitter for sym/co2-node.kicad_sym.

One flat (no extends) definition per part: {"name", "ref_prefix",
"pins": [(number, name, etype, x, y, angle)], "rects": [...]} in library
coordinates (y up), body rectangle ±12.7 unless stated.

Pin numbers are authoritative (see ../schematic-notes.md, read off the
datasheet figures). Do not renumber.

Electrical types follow the ERC drive matrix (probed 2026-11-07):
  input+passive => pin_not_driven (passive does NOT drive input)
  power_out+power_in => clean (PWR_FLAG drives power_in)
  passive+power_in => power_pin_not_driven (passive does NOT drive power_in)
  no_connect pins must never be wired (use no_connect markers).
"""
from __future__ import annotations

# Pin: (number, name, etype, x, y, angle). angle = outward direction deg.
# Left column x=-12.7 (angle 180), right column x=+12.7 (angle 0).
L, R = -12.7, 12.7


def _col(start_y, step, items):
    """Lay items top-to-bottom starting at start_y."""
    return [(n, t, e, x, start_y - i * step, a)
            for i, (n, t, e, x, a) in enumerate(items)]


def _split(pins, n_left):
    left, right = pins[:n_left], pins[n_left:]
    out = _col(12.7 - 2.54, 5.08, [(n, t, e, L, 180) for n, t, e in left])
    out += _col(12.7 - 2.54, 5.08, [(n, t, e, R, 0) for n, t, e in right])
    return out

# --- BQ24074 VQFN-16 + EP.
_bq = [
    ("1", "TS", "passive"), ("2", "BAT", "power_out"),
    ("3", "BAT", "passive"), ("4", "CE", "input"),
    ("5", "EN2", "input"), ("6", "EN1", "input"),
    ("7", "PGOOD", "open_collector"), ("8", "VSS", "power_in"),
    ("9", "CHG", "open_collector"), ("10", "OUT", "power_out"),
    ("11", "OUT", "passive"), ("12", "ILIM", "passive"),
    ("13", "IN", "power_in"), ("14", "TMR", "passive"),
    ("15", "ITERM", "passive"), ("16", "ISET", "passive"),
    ("17", "EP", "power_in"),
]

 # --- ESP32-C3-MINI-1: 53 pins; signal on left, GND/NC split, power right.
_esp_sig = [
    ("5", "IO2", "bidirectional"), ("6", "IO3", "bidirectional"),
    ("8", "EN", "input"), ("12", "IO0", "bidirectional"),
    ("13", "IO1", "bidirectional"), ("16", "IO10", "bidirectional"),
    ("18", "IO4", "bidirectional"), ("19", "IO5", "bidirectional"),
    ("20", "IO6", "bidirectional"), ("21", "IO7", "bidirectional"),
    ("22", "IO8", "bidirectional"), ("23", "IO9", "bidirectional"),
    ("26", "IO18", "bidirectional"), ("27", "IO19", "bidirectional"),
    ("30", "IO20", "bidirectional"), ("31", "IO21", "bidirectional"),
]
_esp_gnd = [(str(i), "GND", "power_in")
            for i in (1, 2, 11, 14, *range(36, 54))]
_esp_nc = [(str(i), "NC", "passive")
           for i in (4, 7, 9, 10, 15, 17, 24, 25, 28, 29, 32, 33, 34, 35)]
_esp_pwr = [("3", "3V3", "power_in")]

_tps = [
    ("1", "OUT", "power_out"), ("2", "NC", "passive"),
    ("3", "PG", "open_collector"), ("4", "EN", "input"),
    ("5", "GND", "power_in"), ("6", "IN", "power_in"),
    ("7", "EP", "power_in"),
]


# --- DW01A SOT-23-6.
_dw = [
    ("1", "OD", "output"), ("2", "CS", "input"), ("3", "OC", "output"),
    ("4", "TD", "passive"), ("5", "VCC", "power_in"),
    ("6", "GND", "power_in"),
]

# --- FS8205A TSSOP-8 (p.3: 1 D12, 2 S1, 3 S1, 4 G1, 5 G2, 6 S2, 7 S2, 8 D12).
_fs = [
    ("1", "D12", "passive"), ("2", "S1", "passive"),
    ("3", "S1", "passive"), ("4", "G1", "input"),
    ("5", "G2", "input"), ("6", "S2", "passive"),
    ("7", "S2", "passive"), ("8", "D12", "passive"),
]

# --- SCD41: 21 pads. VDD/VDDH power_in, GND power_in, SDA bidir, SCL input,
# --- DNC no_connect (floating pad, soldered, no net).
_scd = (
    [(str(i), "DNC", "passive") for i in (1, 2, 3, 4, 5)]
    + [("6", "GND", "power_in"), ("7", "VDD", "power_in"),
       ("8", "DNC", "passive"), ("9", "SCL", "input"),
       ("10", "SDA", "bidirectional")]
    + [(str(i), "DNC", "passive") for i in (11, 12, 13, 14, 15, 16, 17, 18)]
    + [("19", "VDD", "passive"), ("20", "GND", "passive"),
       ("21", "GND", "passive")]
)

# --- USB-C 16P (authoritative: A1 GND, A4 VBUS, A5 CC1, A6 D+, A7 D−,
# --- A8 SBU1, A9 VBUS, A12 GND, B1 GND, B4 VBUS, B5 CC2, B6 D+, B7 D−,
# --- B8 SBU2, B9 VBUS, B12 GND, SH GND).
_usb = [
    ("A1", "GND", "passive"), ("A4", "VBUS", "passive"),
    ("A5", "CC1", "bidirectional"), ("A6", "D+", "bidirectional"),
    ("A7", "D-", "bidirectional"), ("A8", "SBU1", "passive"),
    ("A9", "VBUS", "passive"), ("A12", "GND", "passive"),
    ("B1", "GND", "passive"), ("B4", "VBUS", "passive"),
    ("B5", "CC2", "bidirectional"), ("B6", "D+", "bidirectional"),
    ("B7", "D-", "bidirectional"), ("B8", "SBU2", "passive"),
    ("B9", "VBUS", "passive"), ("B12", "GND", "passive"),
    ("SH", "SH", "passive"),
]

# --- FPC-24: 1–24 per weact-transcription.md + shell MP.
_fpc = ([(str(i), f"P{i}", "passive") for i in range(1, 25)]
        + [("MP", "MP", "passive")])

# Named nets for FPC pins (weact-transcription.md + display topology).
FPC_PIN_NAMES = {
    "1": "GND", "2": "E_VGL", "3": "GND", "4": "E_VGH", "5": "GND",
    "6": "GND", "7": "EPD_P7", "8": "EPD_P8", "9": "EPD_P9",
    "10": "EPD_P10", "11": "EPD_SDA", "12": "EPD_SCL", "13": "EPD_CS",
    "14": "EPD_DC", "15": "EPD_RES", "16": "EPD_BUSY", "17": "E_BS",
    "18": "GND", "19": "GND", "20": "EPD_P20", "21": "GND",
    "22": "E_RESR", "23": "E_GDR", "24": "GND", "25": "GND", "26": "GND",
}


def _named(pins, names):
    return [(n, names.get(n, nm), e) for n, nm, e in pins]


SYMBOLS = [
    {"name": "ESP32-C3-MINI-1", "ref_prefix": "U",
     "pins": ([(n, t, e) for n, t, e in _esp_sig]
              + [(n, t, e) for n, t, e in _esp_pwr]
              + [(n, t, e) for n, t, e in _esp_gnd]
              + [(n, t, e) for n, t, e in _esp_nc]),
     "rects": [(-12.7, 25.4, 12.7, -30.0)]},
    {"name": "BQ24074", "ref_prefix": "U",
     "pins": _split(_bq, 9), "rects": [(-12.7, 12.7, 12.7, -12.7)]},
    {"name": "TPS7A2633", "ref_prefix": "U",
     "pins": _split(_tps, 4), "rects": [(-12.7, 12.7, 12.7, -12.7)]},
    {"name": "DW01A", "ref_prefix": "U",
     "pins": _split(_dw, 3), "rects": [(-12.7, 12.7, 12.7, -12.7)]},
    {"name": "FS8205A", "ref_prefix": "U",
     "pins": _split(_fs, 4), "rects": [(-12.7, 12.7, 12.7, -12.7)]},
    {"name": "AO3401A", "ref_prefix": "Q",
     "pins": [("1", "G", "input"), ("2", "S", "passive"),
              ("3", "D", "passive")],
     "rects": [(-12.7, 12.7, 12.7, -12.7)]},
    {"name": "AO3402", "ref_prefix": "Q",
     "pins": [("1", "G", "input"), ("2", "S", "passive"),
              ("3", "D", "passive")],
     "rects": [(-12.7, 12.7, 12.7, -12.7)]},
    {"name": "BSS138", "ref_prefix": "Q",
     "pins": [("1", "G", "input"), ("2", "S", "passive"),
              ("3", "D", "passive")],
     "rects": [(-12.7, 12.7, 12.7, -12.7)]},
    {"name": "USBLC6-2SC6", "ref_prefix": "D",
     "pins": [("1", "I/O1", "bidirectional"), ("2", "GND", "power_in"),
              ("3", "I/O2", "bidirectional"), ("4", "I/O2", "bidirectional"),
              ("5", "VCC", "power_in"), ("6", "I/O1", "bidirectional")],
     "rects": [(-12.7, 12.7, 12.7, -12.7)]},
    {"name": "SCD41", "ref_prefix": "IC",
     "pins": _scd, "rects": [(-12.7, 12.7, 12.7, -12.7)]},
    {"name": "USB_C_16P", "ref_prefix": "J",
     "pins": _usb, "rects": [(-12.7, 12.7, 12.7, -12.7)]},
    {"name": "FPC-24", "ref_prefix": "J",
     "pins": _named(_fpc, FPC_PIN_NAMES),
     "rects": [(-12.7, 12.7, 12.7, -12.7)]},
    {"name": "BAT_HOLDER", "ref_prefix": "BT",
     "pins": [("1", "+", "passive"), ("2", "-", "power_in")],
     "rects": [(-12.7, 12.7, 12.7, -12.7)]},
    {"name": "R", "ref_prefix": "R",
     "pins": [("1", "~", "passive"), ("2", "~", "passive")],
     "rects": [(-2.0, 2.0, 2.0, -2.0)]},
    {"name": "C", "ref_prefix": "C",
     "pins": [("1", "~", "passive"), ("2", "~", "passive")],
     "rects": [(-2.0, 2.0, 2.0, -2.0)]},
    {"name": "L", "ref_prefix": "L",
     "pins": [("1", "~", "passive"), ("2", "~", "passive")],
     "rects": [(-2.0, 2.0, 2.0, -2.0)]},
    {"name": "D", "ref_prefix": "D",
     "pins": [("1", "K", "passive"), ("2", "A", "passive")],
     "rects": [(-2.0, 2.0, 2.0, -2.0)]},
    {"name": "LED", "ref_prefix": "D",
     "pins": [("1", "K", "passive"), ("2", "A", "passive")],
     "rects": [(-2.0, 2.0, 2.0, -2.0)]},
    {"name": "FUSE", "ref_prefix": "F",
     "pins": [("1", "~", "passive"), ("2", "~", "passive")],
     "rects": [(-2.0, 2.0, 2.0, -2.0)]},
    {"name": "NTC", "ref_prefix": "RT",
     "pins": [("1", "~", "passive"), ("2", "~", "passive")],
     "rects": [(-2.0, 2.0, 2.0, -2.0)]},
    {"name": "SW", "ref_prefix": "SW",
     "pins": [("1", "~", "passive"), ("2", "~", "passive")],
     "rects": [(-2.0, 2.0, 2.0, -2.0)]},
    {"name": "TP", "ref_prefix": "TP",
     "pins": [("1", "~", "passive")],
     "rects": [(-2.0, 2.0, 2.0, -2.0)]},
    {"name": "MOUNT", "ref_prefix": "H",
     "pins": [("1", "~", "passive")],
     "rects": [(-2.0, 2.0, 2.0, -2.0)]},
    {"name": "GND", "ref_prefix": "#PWR", "power": True,
     "pins": [("1", "GND", "power_in", 0, 0, 270)], "rects": []},
    {"name": "PWR_FLAG", "ref_prefix": "#PWR", "power": True,
     "pins": [("1", "PWR", "power_out", 0, 0, 270)], "rects": []},
]
