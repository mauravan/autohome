#!/usr/bin/env python3
"""Single source of every pin->net assignment.

ref -> {pin: net}. Also SHEETS (ref -> sheet), MECH_NETS (non-netlist pads
assigned a net on the board), and DNP set. The schematic emitter, the PCB
pad-net pass, and the netlist assertions all read this file, so a typo shows
up as a DRC parity failure instead of a silent wrong board.

Corrections applied vs the old invalid generators:
- Q4 BSS138: 1 = PWR_EN, 2 = GND, 3 = Q3_G (source to ground, drain pulls
  the P-FET gate low).
- J1 USB-C: A1/B1/A12/B12/SH -> GND; A4/B4/A9/B9 -> VBUS; A5 -> USB_CC1;
  B5 -> USB_CC2; A6/B6 -> USB_DP; A7/B7 -> USB_DM; A8/B8 -> "" (no-connect).
- USB_DN eliminated: the single net name is USB_DM (datasheet D-).
- U10, IC-SCD assignments per plan Step 4.
- No lambda/label string is constructed by concatenation anywhere.
"""
from __future__ import annotations

# ref -> {pin_number: net}. "" = intentionally unconnected (no_connect marker).
NETS: dict[str, dict[str, str]] = {
    # --- power sheet
    "J1": {"A1": "GND", "A4": "VBUS", "A5": "USB_CC1", "A6": "USB_DP",
           "A7": "USB_DM", "A8": "NC_SBU", "A9": "VBUS", "A12": "GND",
           "B1": "GND", "B4": "VBUS", "B5": "USB_CC2", "B6": "USB_DP",
           "B7": "USB_DM", "B8": "NC_SBU", "B9": "VBUS", "B12": "GND",
           "SH": "GND"},
    "F1": {"1": "VBUS", "2": "VBUS"},
    "R10": {"1": "USB_CC1", "2": "GND"},
    "R11": {"1": "USB_CC2", "2": "GND"},
    "R12": {"1": "USB_DP", "2": "USB_DP"},
    "R13": {"1": "USB_DM", "2": "USB_DM"},
    "D1": {"1": "USB_DP", "2": "GND", "3": "USB_DM",
           "4": "USB_DM", "5": "VBUS", "6": "USB_DP"},
    "U1": {"1": "TS_NTC", "2": "BAT+", "3": "BAT+", "4": "GND",
           "5": "GND", "6": "VBUS", "7": "PG_STAT", "8": "GND",
           "9": "CHG_STAT", "10": "VSYS", "11": "VSYS", "12": "ILIM",
           "13": "VBUS", "14": "NC_TMR", "15": "NC_ITERM", "16": "ISET_MON",
           "17": "GND"},
    "C20": {"1": "VBUS", "2": "GND"},
    "C21": {"1": "BAT+", "2": "GND"},
    "C22": {"1": "VSYS", "2": "GND"},
    "R20": {"1": "ISET_MON", "2": "GND"},
    "R21": {"1": "ILIM", "2": "GND"},
    "R22": {"1": "3V3", "2": "CHG_STAT"},
    "D20": {"1": "CHG_STAT", "2": "GND"},
    "R23": {"1": "3V3", "2": "PG_STAT"},
    "BT1": {"1": "CELL+", "2": "GND"},
    "F2": {"1": "CELL+", "2": "CELL_F"},
    "Q2": {"1": "GND", "2": "CELL_F", "3": "BAT_RAW"},
    "R24": {"1": "BAT_RAW", "2": "DW_VCC"},
    "C23": {"1": "DW_VCC", "2": "GND"},
    "U3": {"1": "DW_OD", "2": "DW_VM", "3": "DW_OC",
           "4": "NC_TD", "5": "DW_VCC", "6": "GND"},
    "R25": {"1": "DW_VM", "2": "PACK-"},
    "U4": {"1": "PACK-", "2": "PACK-", "3": "GND",
           "4": "DW_OD", "5": "DW_OC", "6": "GND",
           "7": "PACK-", "8": "PACK-"},
    "U2": {"1": "3V3", "2": "GND", "3": "PG_3V3",
           "4": "VSYS", "5": "GND", "6": "VSYS", "7": "GND"},
    "C24": {"1": "VSYS", "2": "GND"},
    "C25": {"1": "3V3", "2": "GND"},
    "C26": {"1": "3V3", "2": "GND"},
    "R27": {"1": "3V3", "2": "PG_3V3"},
    "Q3": {"1": "Q3_G", "2": "3V3", "3": "P3V3"},
    "Q4": {"1": "PWR_EN", "2": "GND", "3": "Q3_G"},
    "R28": {"1": "3V3", "2": "Q3_G"},
    "R29": {"1": "PWR_EN", "2": "GND"},
    "C27": {"1": "P3V3", "2": "GND"},
    "C28": {"1": "P3V3", "2": "GND"},
    "R30": {"1": "BAT+", "2": "BAT_SENSE_RAW"},
    "R31": {"1": "BAT_SENSE_RAW", "2": "GND"},
    "C29": {"1": "BAT_SENSE_RAW", "2": "GND"},
    "R32": {"1": "BAT_SENSE_RAW", "2": "VBAT_SENSE"},
    # --- mcu sheet
    "U10": {"1": "GND", "2": "GND", "3": "3V3", "4": "NC_U10_4",
            "5": "STRAP2", "6": "VBAT_SENSE", "7": "NC_U10_7",
            "8": "RESET_N", "9": "NC_U10_9", "10": "NC_U10_10", "11": "GND",
            "12": "EPD_RES", "13": "I2C_SDA", "14": "GND",
            "15": "NC_U10_15", "16": "EPD_BUSY", "17": "NC_U10_17",
            "18": "EPD_SCL", "19": "EPD_DC", "20": "EPD_SDA",
            "21": "EPD_CS", "22": "STRAP8", "23": "BOOT_N",
            "24": "NC_U10_24", "25": "NC_U10_25", "26": "USB_DM", "27": "USB_DP",
            "28": "NC_U10_28", "29": "NC_U10_29", "30": "PWR_EN", "31": "I2C_SCL",
            "32": "NC_U10_32", "33": "NC_U10_33", "34": "NC_U10_34", "35": "NC_U10_35",
            **{str(i): "GND" for i in range(36, 54)}},
    "C40": {"1": "3V3", "2": "GND"},
    "C41": {"1": "3V3", "2": "GND"},
    "C42": {"1": "3V3", "2": "GND"},
    "R40": {"1": "3V3", "2": "RESET_N"},
    "C43": {"1": "RESET_N", "2": "GND"},
    "R41": {"1": "3V3", "2": "BOOT_N"},
    "R42": {"1": "3V3", "2": "STRAP2"},
    "R43": {"1": "3V3", "2": "STRAP8"},
    # --- sensor sheet
    "IC-SCD": {"1": "SCD_DNC", "2": "SCD_DNC", "3": "SCD_DNC", "4": "SCD_DNC",
               "5": "SCD_DNC",
               "6": "GND", "7": "SCD_VDD", "8": "SCD_DNC",
               "9": "I2C_SCL", "10": "I2C_SDA",
               "11": "SCD_DNC", "12": "SCD_DNC", "13": "SCD_DNC", "14": "SCD_DNC",
               "15": "SCD_DNC", "16": "SCD_DNC", "17": "SCD_DNC", "18": "SCD_DNC",
               "19": "SCD_VDD", "20": "GND", "21": "GND"},
    "C50": {"1": "SCD_VDD", "2": "GND"},
    "FB50": {"1": "P3V3", "2": "SCD_VDD"},
    "C51": {"1": "P3V3", "2": "GND"},
    "R50": {"1": "P3V3", "2": "I2C_SDA"},
    "R51": {"1": "P3V3", "2": "I2C_SCL"},
    # --- display sheet
    "J2": {"1": "GND", "2": "E_VGL", "3": "GND", "4": "E_VGH",
           "5": "GND", "6": "GND", "7": "EPD_P7", "8": "EPD_P8",
           "9": "EPD_P9", "10": "EPD_P10", "11": "E_SDA_P",
           "12": "E_SCL_P", "13": "E_CS_P", "14": "E_DC_P",
           "15": "E_RES_P", "16": "E_BUSY_P", "17": "E_BS",
           "18": "GND", "19": "GND", "20": "EPD_P20", "21": "GND",
           "22": "E_RESR", "23": "E_GDR", "24": "GND",
           "MP": "GND"},
    "R60": {"1": "EPD_SDA", "2": "E_SDA_P"},
    "R61": {"1": "EPD_SCL", "2": "E_SCL_P"},
    "R62": {"1": "EPD_CS", "2": "E_CS_P"},
    "R63": {"1": "EPD_DC", "2": "E_DC_P"},
    "R64": {"1": "EPD_RES", "2": "E_RES_P"},
    "R65": {"1": "EPD_BUSY", "2": "E_BUSY_P"},
    "R66": {"1": "3V3", "2": "E_BS"},
    "C60": {"1": "EPD_P20", "2": "GND"},
    "C61": {"1": "VDD33F", "2": "GND"},
    "C62": {"1": "EPD_P8", "2": "GND"},
    "C63": {"1": "EPD_P7", "2": "GND"},
    "C64": {"1": "E_VGH", "2": "GND"},
    "C65": {"1": "E_VGL", "2": "GND"},
    "C66": {"1": "3V3", "2": "GND"},
    "C67": {"1": "3V3", "2": "GND"},
    "L1": {"1": "3V3", "2": "SW"},
    "C68": {"1": "3V3", "2": "GND"},
    "Q1": {"1": "E_GDR", "2": "SW", "3": "E_RESR"},
    "R1": {"1": "E_GDR", "2": "GND"},
    "R2": {"1": "E_RESR", "2": "GND"},
    "C69": {"1": "E_RESR", "2": "GND"},
    "D23": {"1": "SW", "2": "E_VGH"},
    "C70": {"1": "E_VGH", "2": "GND"},
    "C71": {"1": "SW", "2": "E_MID"},
    "D22": {"1": "SW", "2": "E_MID"},
    "D21": {"1": "E_MID", "2": "E_VGL"},
    "C72": {"1": "E_VGL", "2": "E_MID"},
    # --- connectors sheet
    "RT1": {"1": "TS_NTC", "2": "GND"},
    "SW1": {"1": "BOOT_N", "2": "GND"},
    "SW2": {"1": "RESET_N", "2": "GND"},
    "TP1": {"1": "3V3"},
    "TP2": {"1": "GND"},
    "TP3": {"1": "BAT+"},
    "TP4": {"1": "P3V3"},
    "TP5": {"1": "RESET_N"},
    "TP6": {"1": "BOOT_N"},
    "TP7": {"1": "I2C_SCL"},
    "TP8": {"1": "PWR_EN"},
    "H1": {"1": "GND"},
    "H2": {"1": "GND"},
    "H3": {"1": "GND"},
    "H4": {"1": "GND"},
}

# ref -> sheet file stem.
SHEETS: dict[str, str] = {}
for _ref in ("J1", "F1", "R10", "R11", "R12", "R13", "D1", "U1", "C20",
             "C21", "C22", "R20", "R21", "R22", "D20", "R23", "BT1",
             "F2", "Q2", "R24", "C23", "U3", "R25", "U4", "U2", "C24",
             "C25", "C26", "R27", "Q3", "Q4", "R28", "R29", "C27",
             "C28", "R30", "R31", "C29", "R32"):
    SHEETS[_ref] = "power"
for _ref in ("U10", "C40", "C41", "C42", "R40", "C43", "R41", "R42", "R43"):
    SHEETS[_ref] = "mcu"
for _ref in ("IC-SCD", "C50", "FB50", "C51", "R50", "R51"):
    SHEETS[_ref] = "sensor"
for _ref in ("J2", "R60", "R61", "R62", "R63", "R64", "R65", "R66",
             "C60", "C61", "C62", "C63", "C64", "C65", "C66", "C67",
             "L1", "C68", "Q1", "R1", "R2", "C69", "D23", "C70",
             "C71", "D22", "D21", "C72"):
    SHEETS[_ref] = "display"
for _ref in ("RT1", "SW1", "SW2", "TP1", "TP2", "TP3", "TP4", "TP5",
             "TP6", "TP7", "TP8", "H1", "H2", "H3", "H4"):
    SHEETS[_ref] = "connectors"

# Pads present in footprints but absent from the netlist, assigned a net on
# the board explicitly so no pad is left netless.
MECH_NETS: dict[tuple[str, str], str] = {
    ("U1", "17"): "GND",   # BQ24074 EP
    ("U2", "7"): "GND",    # TPS7A26 EP
    ("J2", "MP"): "GND",   # FPC shell (netlist already GND; harmless)
    ("J1", "SH"): "GND",   # USB-C shell
    ("H1", "1"): "GND", ("H2", "1"): "GND",
    ("H3", "1"): "GND", ("H4", "1"): "GND",
}

# DNP refs (excluded from placement on the board).
DNP = {"R21", "C69"}
