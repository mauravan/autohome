# autohome

Home Assistant companion firmware for battery-powered ESP32-C3 CO₂ / temperature / humidity sensor nodes with an e-paper display.

## What this is

- ESPHome project built on ESP-IDF, targeting the `esp32-c3-devkitm-1`.
- Each node wakes on a timer, takes one SCD41 single-shot measurement, refreshes a WeAct e-paper display, publishes the reading, then deep-sleeps.
- Two transport families:
  - **WiFi + MQTT** with Home Assistant discovery.
  - **BLE BTHome** advertisement (WiFi stays off on timer wakes).

## Repository layout

```
INVENTORY.md          Hardware inventory
SENSORS.md            Sensor/module catalog
AGENTS.md             Detailed architecture and development guidelines
firmware/co2-node/    ESPHome project, components, tools and runbook
```

See [`firmware/co2-node/README.md`](firmware/co2-node/README.md) for flashing, MQTT verification, troubleshooting and power notes.

## Quick start

```bash
pip install esphome
cd firmware/co2-node
cp secrets.yaml.example secrets.yaml   # fill in mqtt_* and ota_password
esphome config top.yaml
esphome run top.yaml --device /dev/ttyACM0
```

For BLE builds use `top-ble.yaml`, `mid-ble.yaml`, etc. instead.
