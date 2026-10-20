# Standards / Protocols

| Standard | Layer / frequency | Used by | Bridge into HA | Notes |
|---|---|---|---|---|
| Wi-Fi 5 (802.11ac) | IP / 802.11ac 2.4+5 GHz | RPi 5 hub, 3× Pi 3B/spare, 2× Pi Zero W | Direct (HA runs on hub) | Hub has dual-band Wi-Fi 5; floor nodes on 2.4 GHz; MQTT over Wi-Fi |
| Zigbee 3.0 (ZLL) | 802.15.4 / 2.4 GHz | Philips Hue lamps | Hue Bridge (Zigbee coordinator) → HA `hue` integration over LAN API | Need to buy a Hue Bridge (not in inventory) |
| Somfy RTS | 433 MHz OOK | Somfy RTS blinds (rolling code) | RFLink gateway (Arduino Mega + 433 MHz) → HA `rflink` integration over serial/TCP | RFLink handles rolling codes natively. Primary bridge for blinds. Velux RTS also covered if applicable. Velux io → KLF200 only if confirmed io (separate check).
| LoRaWAN | 868/915 MHz | IoT LoRa Node pHAT (outdoor/garden) | TTN / ChirpStack → HA MQTT discovery | For long-range hill-bottom/outdoor sensors |
| Bluetooth / BLE 5 | 2.4 GHz | RPi 5 (BT 5.0), Pi 3B, Pi Zero W, nRF52 dev kit | HA `ble_monitor` / ESPHome BLE proxy / nRF52 mesh → MQTT | Hub has BT 5.0; nRF52 = battery BLE sensor nodes |
| I2C | 2-wire bus | HifiBerry (DAC config), SCD41 env sensors, LSM6DSOX MEMS (via MKI109V3), ST MEMS | Read on the node Pi; publish over MQTT | SCD41 = 0x62 default addr |
| 1-Wire | single-wire bus | DS18B20 probe (S05) | Pi GPIO bitbang → MQTT | Extra temp points |
| SPI | 4-wire bus | LoRa pHAT, (MEMS adapter) | Node-local | |
| GPIO / single-wire digital | pin-level | DHT11, reed (S02), tilt (S13), relays (S08/S18), IR (S01/S16), sound (S09/S17), light (S10/S22), flame (S19), RGB/LED (S12/S14/S15) | Node reads → MQTT | Most loose sensors land here |
| Analog | voltage | ADXL335 (3-axis accel), KY-013 thermistor (S06), analog outputs of sound/light/flame | Needs ADC: Digilent Analog Discovery (bench) or an ADS1115/MCP3008 HAT for deploy | |
| MQTT | app / TCP | all nodes → hub | HA MQTT integration, auto-discovery | Lingua franca between nodes and hub |