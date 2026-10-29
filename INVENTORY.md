# Inventory

| Item | Qty | Specs | Standards/Interfaces | Allocated role | Notes |
|---|---|---|---|---|---|
| Raspberry Pi Display v1.1 | 1 | Official 7" touchscreen, 800x480, DSI | DSI, I2C (touch) | Wall dashboard on the hub Pi | Mounts via DSI ribbon |
| Raspberry Pi 5 Model B | 1 | BCM2712, 2.4 GHz quad Cortex-A76, 8 GB, Wi-Fi 5/BT 5.0, USB 3, GbE | Wi-Fi 5 (802.11ac), BT/BLE 5.0, GPIO, I2C, SPI, UART, USB 3 | **Hub** — Home Assistant OS + dashboard + MQTT broker | Primary hub; replaces Pi 3B #1 |
| Raspberry Pi 3 Model B v1.2 | 1 (spare) | BCM2837, 1.2 GHz, 1 GB, Wi-Fi/BT 4.1 | Wi-Fi 2.4 GHz, BT/BLE, GPIO, I2C, SPI, 1-Wire (bitbang) | Retired from CO₂ duty; spare | Displaced from hub duty by RPi 5; kept as spare / dev bench |
| Raspberry Pi Zero W v1.1 | 2 | 1 GHz, 512 MB, Wi-Fi/BT | Wi-Fi 2.4 GHz, BT/BLE, GPIO, I2C, SPI | Retired from CO₂ duty; Zero#1 = nRF52 BLE mesh host (top); Zero#2 = LoRa pHAT host (bottom) | Need micro-USB power + micro-SD |
| HifiBerry | 1 | I2S DAC HAT for Pi | I2S, I2C | Audio output on hub (doorbell/alarm/tts announcements) | Stacks on RPi 5 GPIO |
| 64 GB micro-SD card | 1 | Class 10 / A2 | — | OS for HAOS hub (RPi 5) | Plenty of headroom for HAOS + add-ons + recorder history |
| 8 GB micro-SD card | 3 | Class 10 | — | OS for sensor nodes (Pi Zero W ×2 + Pi 3B spare) | Pi 3B #1 (old hub) repurposed as floor node or spare |
| STM32MP157F-DK2 + display | 1 | STM32MP157F dual Cortex-A7 + Cortex-M4, 4.3" panel | Ethernet, USB, I2C, SPI, UART | Edge compute / optional dedicated blind+window controller via RFLink API or direct GPIO; display = local control panel | Unallocated initially; Phase 5 |
| nRF52 development kit | 1 | nRF52832, BLE, ultra-low-power | BLE 5, UART, GPIO, I2C, SPI | BLE mesh sensor node for battery-powered sensors (reed, tilt, ADXL335) | Programmed via SEGGER / Arduino |
| STEVAL-MKI109V3 | 1 | ProfiMEMS motherboard, STM32F401VE, USB | USB, I2C, SPI (to adapter) | MEMS eval/bench tooling (not deployed) | Pairs with STEVAL-MKI197V1 |
| STEVAL-MKI197V1 | 1 | LSM6DSOX accel + gyro DIL24 adapter | I2C/SPI to MKI109V3 | MEMS eval: blind/window vibration + tilt sensing R&D | Stacks on MKI109V3 |
| IoT LoRa Node pHAT (10948) | 1 | Pi Supply LoRaWAN node, 868/915 MHz | LoRaWAN, SPI (to Pi), The Things Network | Long-range outdoor/garden node (soil moisture, garage, hill-bottom sensor) | Stacks on a Pi Zero W |
| ADXL335 BBoard v2 | 1 | Analog 3-axis accelerometer ±3g | Analog (3× voltage) | Tilt/vibration on a blind/window motor or door | Needs ADC (Analog Discovery bench, or Pi via an ADC HAT later) |
| Joy-Pi dev kit + Joy-It remote + Pi 3B + display | 1 | Sensor breadboard kit + IR remote on a Pi 3B | GPIO, IR, I2C, SPI | Bench sensor lab + IR remote control prototyping | Pi 3B counted in the 3 above |
| micro-HDMI adapter (Joy-It) | 1 | micro-HDMI to HDMI adapter | — | Video out for Pi Zero / Pi 4 | — |
| Seeed Studio XIAO-RP2040 | 1 | RP2040 dual Cortex-M0+, 133 MHz, 264 KB SRAM, USB-C, compact 21×17.8 mm | USB, I2C, SPI, UART, PWM, GPIO | Microcontroller node for sensor/actuator projects; programmable via CircuitPython/Arduino/MicroPython | Can offload real-time tasks from Pi nodes; low-power sleep modes |
| Sensirion SCD41 CO₂ sensor | 3 | I2C, 0–40000 ppm CO₂, ±(40 ppm + 5% reading), ±0.8°C, ±3% RH | I2C (0x62), 3.3 V | Per-floor ESP32 battery nodes | One per floor (ESP32-C6); requires SCD4x library |
| ESP32 WROOM 32 DevKit | 1–2 | ESP32 dual-core, Wi-Fi/BT, USB | GPIO, I2C, SPI, UART | Dev bench for `firmware/co2-node/` | `esp32dev` board; USB-powered, no VCC gating |
| ESP32-C6 mini | 3+ | RISC-V, Wi-Fi 6/BLE 5, deep-sleep ~7 µA | GPIO, I2C, SPI, UART | Production CO₂ node (1 per floor + spares) | Battery port (Li-ion + LDO + MOSFET gating) is a documented final step |
| WeAct 1.54" 200×200 B/W e-paper | 3+ | SSD1681, 200×200, black/white | SPI | Per-floor CO₂/T/RH display | `waveshare_epaper` model `1.54in` |