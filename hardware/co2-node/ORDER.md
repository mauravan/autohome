# Rev-A order package (Phase 4, 5 boards)

Status: PRE-ORDER — no order placed. Routing (traces) is still open in
KiCad 9; do not order until `kicad-cli pcb drc` is clean on a ROUTED board.
This file records what was verified so all details are ready at order time.

## Distributor stock (checked 2026-11-06, web)

| Part | Source | Stock signal |
|---|---|---|
| `SCD41-D-R2` | Mouser listing live; TrustedParts/DigiPart aggregate stock | order sealed tape, MSL3 label |
| `ESP32-C3-MINI-1-N4` | Mouser listing live; DigiKey TR/CT; LCSC | tape-and-reel |
| `BQ24074RGTR` | Mouser ~4.8–5.8k in stock (~$2.45) | cut tape OK |
| `TPS7A2633DRVR` | FindChips aggregates DigiKey+ stock | cut tape OK |
| `FH12-24S-0.5SH(55)` | DigiKey 15k in stock (~$2.41); JLC/LCSC alt | confirm contact side on spare panel first |
| `DW01A` + `FS8205A` | LCSC/JLC commodity | SOT-23-6 + TSSOP-8 |
| `Keystone 1043` | Mouser/DigiKey commodity | hand-solder THT |
| Passives (0603/0402) | AISLER catalog | assigned in BOM tool |

Re-verify quantities at order time. If any line is short, hold the order —
no substitutions without re-qualifying (plan §Assumptions).

## AISLER self-supply (confirmed 2026-10-15 terms)

- Mark parts "You supply it" in the BOM tool; €15 one-time fee per unique
  MPN; parts must reach AISLER within 8 days (EU shipping label provided).
- Self-supply candidates: `SCD41-D-R2` (MSL3 sealed bag + bake note),
  `ESP32-C3-MINI-1-N4` (if absent from catalog). Contact
  support@aisler.net with specs if a part is missing from the catalog.
- Confirm in the upload: 2-layer, ENIG, both-side assembly, holder as THT
  (or hand-solder).

## Fallback: Eurocircuits

Customer-supplied parts, 1–50 pcs, no design-file change. Use only if
AISLER rejects the self-supply or the holder.

## Panel split

- 3 existing WeAct 1.54" panels → home units (top/mid/bottom).
- 2 NEW `YRD0150BBS810F0-M7` panels → product units (gift + compliance).
- Do not harvest a bench-reference module panel.

## No-cell rule

Do NOT order 18650 cells. Holders + NTCs + labels + packaging only.
Ship/product units go out WITHOUT a cell (no dangerous-goods paperwork).

## Order acceptance (plan)

Order confirmation with dispatch date; every part allocated to a unit;
no dev board / breakout / display-module PCB in the BOM.
