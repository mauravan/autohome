# Layout — Phase 3 acceptance record (rev A)

Generators: `tools/gen_footprints.py` (38 `.kicad_mod`),
`tools/gen_placement.py` (`co2-node.kicad_pcb` + `placement.csv`),
checks: `tools/erc_lite.py`, `tools/drc_lite.py`.

## DRC-lite result

`DRC-lite PASS: 94 footprints, keepout/thermal/nets clean`
(94 = 99 schematic refs minus H1–H4/LBL1 mechanical-only.)

- D1 outline 95×45, all parts inside.
- D2 antenna keepout x[70,86.5] y[30,46] clear (U10 module only); MCU
  decoupling/strapping kept at x ≤ 68.5.
- D3 holder top edge 26 < keepout bottom 30 (4 mm margin).
- D4 SCD41 at (20, 6) bottom-front; D5 ≥ 25 mm from U1/U2/L1/Q1.
- D6 test pads y = 3 (pogo row, clear of holder y 14–26).
- D7 no center overlap < 2.5 mm (SCD41/DNC island exempt).
- D8 USB-C y = 2.0 at bottom edge; D9 FPC (12, 36) top-left.
- D10 every schematic pin-net + label in PCB net table (66 nets).

## AISLER 2-layer rules (by construction)

- 0.2 mm min trace/space, 0.3 mm min drill, 0.6 mm min via pad.
- 0603/0402/SOT/SOD/TSSOP/VQFN/WSON geometries per datasheet pads.
- Bottom GND continuous (pour in KiCad); no copper/traces under antenna
  on either layer (keepout zone in PCB file).

## Exports (run in KiCad 9 — no KiCad on this workstation)

```
kicad-cli sch erc co2-node.kicad_sch
kicad-cli pcb drc co2-node.kicad_pcb
kicad-cli sch export gerbers ... / pcb export gerbers (F.Cu B.Cu F.SilkS
  B.SilkS F.Mask B.Mask Edge.Cuts) + drill + pos + netlist (IPC-356)
kicad-cli pcb export step co2-node.step
```

`bom/BOM.csv` (99 lines, MPNs), `bom/CPL.csv` (94 placed),
`bom/netlist-audit.txt` (99 refs) are generated and committed.

## STEP / enclosure fit (blocking on KiCad)

Import `co2-node.step` into `enclosure/`: verify panel/FPC fold, holder
clearance, USB-C cutout, button access, antenna clearance, wall thickness,
screw bosses. No interference allowed before rev-A order.

## Known Phase 3 limits (honest)

- Traces are NOT routed — the PCB file carries footprints + nets + keepout
  + outline only. Routing happens in KiCad 9 (this workstation has no KiCad:
  `apt` needs sudo, unavailable). The netlist, placement, and DRC-lite
  constraints above are the binding input to that routing session.
- FPC `J1` contact side MUST be confirmed on a spare panel before routing
  the 8 panel signals (plan §display, checklist item).
- SCD41 pad grid is parametric from Fig 4a (not a DXF import) — verify
  against the Sensirion recommended pattern in KiCad before DFM submit.
- BQ24074 pin order around the VQFN is functional (datasheet Table 7-1);
  assign physical pads to the footprint pin-1 marker in KiCad.
