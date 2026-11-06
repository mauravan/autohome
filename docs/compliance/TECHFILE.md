# Technical file index (Phase 8 — sell-ready gate)

Status: PRE-FILE. Started so nothing is forgotten; formal test follows
Gate C approval.

## Contents (one folder per line when created)

- `01-description/`: product description, intended use, model AH-CO2-1,
  photos of unit + label + packaging.
- `02-design/`: schematic PDF, layout PDF, `bom/BOM.csv`, layer stack,
  `ORDER.md` (assembly evidence).
- `03-manual/`: DE/EN manual (safety, 18650 spec 65 mm ≥2500 mAh protected,
  charging, setup, HA MQTT, calibration, display, updates, disposal,
  support, simplified DoC + full-DoC URL).
- `04-risk/`: risk assessment (battery, charger, thermal, RF, enclosure),
  security assessment (unique AP password, web auth, NVS enc, signed OTA,
  downgrade protection, no default MQTT creds, update policy 2-yr/5-yr,
  vulnerability contact).
- `05-reports/`: ESP32-C3-MINI-1 module RED reports (request from Espressif/
  distributor) + host EMC pre-scan (≥6 dB margin) + formal RED/EMC report +
  EN 18031-1 cyber assessment.
- `06-registrations/`: WEEE (stiftung ear) + packaging (LUCID/VerpackG)
  numbers — BEFORE first sale.
- `07-doc/`: signed EU Declaration of Conformity (RED 2014/53/EU).

## Standards baseline

RED 2014/53/EU 3.1(a)(b), 3.2, 3.3(d)(e)(f); EN 62368-1; EN 55032/55035;
EN 300 328; EN 301 489-1/-17; EN 62479/50663; EN 18031-1; EN IEC 63000;
WEEE 2012/19/EU; Battery (EU) 2023/1542; GPSR (EU) 2023/988; Pack 94/62/EC.

## Gate C (business — binding)

~€1,200–2,600/unit at 5 units. Approve a 50–100 unit batch
(~€120–260/unit amortized) or stop before the formal test and keep units
personal/gift. NO SALE WITHOUT THE DoC.

## Cyber fallback (if assessor rejects plain MQTT/HTTP)

Per plan: MQTT-TLS 8883 (compile-time CA), or native API + encryption,
or no-web build with MQTT-number calibration. Re-run pre-assessment.
