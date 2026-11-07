# Layout — KiCad-native rev A (gated by KiCad, not by text lints)

Generators: `tools/kicad/gen_sym.py` (`sym/co2-node.kicad_sym`),
`tools/gen_sch.py` (5 sheets + root), `tools/kicad/footprints.py`
(4 custom footprints in `fp/co2-node.pretty`), `tools/gen_pcb.py`
(`co2-node.kicad_pcb` + `co2-node.kicad_pro`), `tools/mfg.py` (exports).
Gate: `python3 tools/verify_all.py` — KiCad ERC/DRC are the gates.

## ERC gate (Step 5)

`kicad-cli sch erc --severity-error --severity-warning
--exit-code-violations` → **0 errors**. Warnings allowed only as listed in
`reports/erc-allowlist.txt` (exact `code<TAB>count<TAB>reason` match):
20× `isolated_pin_label` — 14× `NC_U10_*` (module NC pads float
individually), NC_TMR/NC_ITERM/NC_TD (datasheet float), EPD_P9/EPD_P10
(panel-only FPC pins), VDD33F (WeAct stub).

## DRC gate, pre-route (Steps 7–8)

`kicad-cli pcb drc --schematic-parity --severity-all` →
**schematic_parity: 0 mismatches** and every violation has
`type == "unconnected_items"` (261 ratsnest entries, tolerated until
routing), except 2× `silk_edge_clearance` accepted in
`reports/drc-allowlist.txt`: the ESP32 module keepout silk crosses the
top board edge where the antenna overhangs by design; fab clips it.

- D1 outline 95×45 proven by Edge.Cuts gerber extremes (0–95, 0–45).
- D2 antenna keepout x[70,86.5] y[30,46] rule area on both copper layers
  (tracks/vias/pours banned); only U10 inside; H4 moved to (48, 41.5) to
  clear the module courtyard (was a corner, now top-edge middle).
- D3 holder top edge 28.3 < keepout bottom 30.
- D4 SCD41 at (20, 7) bottom-front; D5 charger/LDO/boost away from sensor.
- D6 test pads y = 1.5 row x 64–86.4, clear of holder.
- D7 courtyard-clean per measured installed courtyard sizes (generator
  asserts overlap/keepout/thermal before DRC).
- D8 USB-C J1 (50, 4) overhangs bottom edge (mid-mount, by design);
  D9 FPC J2 (13, 34.5) top-left.
- D10 pad nets from the exported netlist (79 nets, 0 mismatches);
  mechanical-only pads (VQFN EP 17, WSON EP 7, FPC MP, USB SH, holes)
  assigned GND from `tools/kicad/netmap.py`.

## Netlist corrections applied in this pass

- Q4 BSS138: 1 = PWR_EN, 2 = GND, 3 = Q3_G (source to ground).
- J1 USB-C: A1/B1/A12/B12/SH = GND; A4/B4/A9/B9 = VBUS; A5 = USB_CC1,
  B5 = USB_CC2; A6/B6 = USB_DP; A7/B7 = USB_DM; A8/B8 = NC_SBU.
- Single net name `USB_DM` (datasheet D−); `USB_DN` removed.
- Q1_S merged into E_RESR (WeAct low-side sense node).
- Float pins carry explicit nets (no `""` remains): `NC_U10_*`,
  `NC_TMR/NC_ITERM/NC_TD`, `SCD_DNC` (13 DNC pads, one floating net),
  `NC_SBU`, `ILIM` (U1.12+R21.1, R21.2 = GND).

## Footprints

Installed (reused): 0603/0402 R/C, SOT-23(-6), SOD-323, 0603 LED,
0603/1206 Fuse, 0603 L, TSSOP-8_4.4x3mm (FS8205A per JEDEC MO-153 AA),
Hirose FH12-24S FPC, HCTL USB-C-16P, TestPoint 1.0mm,
MountingHole_2.7mm_M2.5_Pad (plated, GND), KMR2 switch,
**RF_Module:ESP32-C6-MINI-1** for the C3-MINI-1 (no C3 in libs; same
MINI-1 family/land pattern, datasheet wins on conflict — none found).
Custom (pcbnew-built, `fp/co2-node.pretty`): SCD41-LGA (matches installed
Sensirion_SCD4x pad-for-pad), BQ24074-VQFN-16 (EP 1.2 land for 0.2
clearance), TPS7A26-WSON-6, Keystone-1043 (2× Ø3.7 on 55.2 span).

## CPL/BOM counts (why 93/99, not 94)

- CPL 93 rows = 97 placed footprints minus H1–H4 (drilled, not placed).
  TP1–8 and DNP R21/C69 stay in (probe/placement convention).
- BOM 99 refs = 97 kicad-cli refs + LBL1/DNC-PAD mechanical lines appended
  from `tools/bom_data.py` (label + DNC island have no schematic symbol).
- The old CPL 94 counted a DNC-PAD footprint row; the DNC function is now
  served by the SCD41 footprint's own DNC pads on net `SCD_DNC`.

## Routing checklist (manual gate, KiCad GUI)

Bottom-layer continuous GND first, then power (VBUS → VSYS → 3V3 → P3V3)
at 0.5 mm, I²C, EPD bus with series resistors adjacent to the connector,
boost loop < 10 mm, no copper in x 70–86.5 / y 30–46 on either layer,
0.2 mm min clearance. After routing,
`kicad-cli pcb drc --exit-code-violations` must exit 0 with an empty
violation list; that is the "routed" gate. Bench matrix (rails, 20 µA
sleep, 500 mA charge, I²C 0x62, display checkerboard, 24 h soak) cannot
run without hardware — recorded here as unchecked.
