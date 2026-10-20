# AutoHome — 3-Story Hill House DIY Automation

DIY home automation for a 3-story hill house on a budget. Hub: Home Assistant on Raspberry Pi 5. Lighting via Philips Hue/Zigbee. Blinds (Somfy io) and roof windows (Velux io-homecontrol) via Velux KLF200. Per-floor SCD41 CO₂/temp/humidity sensors on Pi Zero W / nRF52 nodes.

[Inventory](INVENTORY.md) · [Sensors](SENSORS.md) · [Standards](STANDARDS.md) · [Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md)

## Finding a Sensor Again

Search `SENSORS.md` by the **Sensor / Module** column name:

```bash
grep -i "KY-040" SENSORS.md
grep -i "YL-69" SENSORS.md
grep -i "MQ-2" SENSORS.md
```