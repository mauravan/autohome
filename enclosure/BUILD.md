# Enclosure build record (Phase 7 — CAD + print + fit)

Status: PRE-BUILD. CAD starts after the routed PCB STEP exists
(`hardware/co2-node/LAYOUT.md`).

## Binding envelope (from plan)

- Case 101 × 51 × 26 mm, PETG; front bezel + back cover.
- PCB 95 × 45 mm; e-paper top-left; ESP32 antenna overhangs top edge,
  15 mm keepout (plastic case only).
- 18650 holder back, top edge y = 15 mm; access via back cover.
- SCD41 bottom-front at vent grille (6× 2×10 mm slots).
- USB-C bottom cutout; BOOT/RESET pinholes; charge-LED light pipe.
- Open bezel, 1 mm overlap (no glass); 70 × 30 label recess on back.
- 4× M2.5 heat-set inserts, M2.5×8 screws; keyhole wall mount.

## CAD checklist (FreeCAD)

1. Front bezel: panel opening (outline from panel drawing, NOT the
   31.8×37.3 estimate), 1 mm overlap lip, FPC fold channel (panel held
   2 mm above PCB), PCB standoffs at H1–H4.
2. Back cover: battery bulge, holder clearance, label recess 70×30,
   keyhole, USB-C cutout, button pinholes ⌀1.5, LED pipe ⌀2.
3. Vent grille: 6 slots 2×10 mm bottom-front, aligned to SCD41 at (20, 6).
4. Interference check vs PCB STEP: no touch except standoffs/screws.

## Print profile

PETG, 0.2 mm layers, 4 perimeters, 25% gyroid; heat-set M2.5 inserts.

## Acceptance (per plan §Phase 7)

- 5 cases fit; panel flush/dust-free; FPC not pinched; cell in/out by hand;
  USB cable seats; buttons reachable by pin; label flat.
- Thermal: closed-case SCD41 temp vs reference after 30 min → per-unit
  `temp_offset` recorded.
- CO2: exhale test, rise within 2–3 min (τ63% = 60 s).
- Drop: 1 m in retail box; no cracks/rattles; display intact.
