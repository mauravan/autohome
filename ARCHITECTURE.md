# Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HOME ASSISTANT HUB                               │
│                         (Raspberry Pi 5 — Hub)                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Home Asst   │  │    MQTT      │  │   Hue Bridge │  │  RFLink      │     │
│  │   Core       │◄─┤   Broker     │  │   (LAN API)  │  │  (serial/TCP)│     │
│  └──────────────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│                           │                   │                 │             │
│         ┌─────────────────┼───────────────────┼─────────────────┘             │
│         │                 │                   │                               │
│  ┌──────▼──────┐   ┌───────▼────────┐  ┌──────▼────────┐                      │
│  │   Pi#1      │   │   Floor Nodes  │  │   Bridges     │                      │
│  │  (dashboard)│   │  (MQTT over    │  │  (LAN/433MHz) │                      │
│  │  7" touch   │   │   Wi-Fi)       │  │               │                      │
│  └─────────────┘   └────────────────┘  └───────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────┘
                ▲                   ▲                   ▲
                │ Wi-Fi             │ Wi-Fi             │ 433 MHz / LAN
                ▼                   ▼                   ▼
        ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
        │  TOP FLOOR    │   │  MID FLOOR    │   │ BOTTOM FLOOR  │
        │ ESP32-C6 node │   │ ESP32-C6 node │   │ ESP32-C6 node │
        │               │   │               │   │               │
        │ SCD41 (CO₂/T/ │   │ SCD41 (CO₂/T/ │   │ SCD41 (CO₂/T/ │
        │  RH)          │   │  RH)          │   │  RH)          │
        │ WeAct e-paper │   │ WeAct e-paper │   │ WeAct e-paper │
        │ (200x200 B/W) │   │ (200x200 B/W) │   │ (200x200 B/W) │
        │ battery       │   │ battery       │   │ battery       │
        │               │   │               │   │               │
        │ Pi Zero W#1:  │   │ Pi 3B #2:     │   │ Pi Zero W#2:  │
        │ nRF52 BLE mesh│   │ HifiBerry     │   │ LoRa pHAT     │
        │ reed,tilt,ADXL│   │ (audio out)   │   │ (outdoor)     │
        └───────────────┘   └───────────────┘   └───────────────┘
                ▲                   ▲                   ▲
                │                   │                   │
        ┌───────┴───────┐   ┌───────┴───────┐   ┌───────┴───────┐
        │  Hue lamps    │   │  Hue lamps    │   │  Hue lamps    │
        │  (Zigbee)     │   │  (Zigbee)     │   │  (Zigbee)     │
        └───────────────┘   └───────────────┘   └───────────────┘
                ▲                   ▲                   ▲
                │ 433 MHz RTS       │ 433 MHz RTS       │ 433 MHz RTS
                ▼                   ▼                   ▼
        ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
        │ Somfy RTS     │   │ Somfy RTS     │   │ Somfy RTS     │
        │ blinds        │   │ blinds        │   │ blinds        │
        │ Velux io*     │   │ Velux io*     │   │ Velux io*     │
        │ roof windows  │   │ roof windows  │   │ roof windows  │
        └───────────────┘   └───────────────┘   └───────────────┘
```
* Velux io only if confirmed; otherwise RFLink covers Velux RTS too.

## Mermaid Network Diagram

```mermaid
flowchart TB
    subgraph Hub["Home Assistant Hub (RPi 5)"]
        HA["Home Assistant Core"]
        MQTT["MQTT Broker (Mosquitto)"]
        HUE["Philips Hue Bridge\n(Zigbee coordinator)"]
        RFLINK["RFLink Gateway\n(433 MHz, serial/TCP)"]
        DASH["7in Touchscreen Dashboard"]
        HIFI["HifiBerry DAC + Speaker"]
    end

    subgraph Top["Top Floor Node (ESP32-C6)"]
        ESP1["ESP32-C6 (battery)"]
        SCD1["SCD41 CO2/T/RH\n(I2C 0x62)"]
        EPD1["WeAct 1.54in e-paper\n(SPI, SSD1681)"]
        Z1["Pi Zero W #1\n(non-CO2 duties)"]
        NRF["nRF52 DK\n(BLE 5 mesh)"]
        REED["Reed switch\n(door/window)"]
        TILT["Tilt sensor"]
        ADXL["ADXL335\n(accel, needs ADC)"]
    end

    subgraph Mid["Mid Floor Node (ESP32-C6)"]
        ESP2["ESP32-C6 (battery)"]
        SCD2["SCD41 CO2/T/RH\n(I2C 0x62)"]
        EPD2["WeAct 1.54in e-paper\n(SPI, SSD1681)"]
        PI2["Pi 3B #2\n(non-CO2 duties)"]
    end

    subgraph Bot["Bottom Floor Node (ESP32-C6)"]
        ESP3["ESP32-C6 (battery)"]
        SCD3["SCD41 CO2/T/RH\n(I2C 0x62)"]
        EPD3["WeAct 1.54in e-paper\n(SPI, SSD1681)"]
        Z2["Pi Zero W #2\n(non-CO2 duties)"]
        LORA["LoRa pHAT\n(868 MHz TTN)"]
    end

    subgraph PerFloor["Per-Floor Devices (all floors)"]
        HUEL["Philips Hue Lamps\n(Zigbee)"]
        SOMFY["Somfy RTS Blinds"]
        VELUX["Velux io Roof Windows*"]
    end

    subgraph TTN["The Things Network"]
        TTNNODE["TTN Gateway"]
    end

    HA --- MQTT
    HA --- HUE
    HA --- RFLINK
    HUE --- HUEL
    RFLINK --- SOMFY
    RFLINK --- VELUX
    MQTT -.-> ESP1
    MQTT -.-> ESP2
    MQTT -.-> ESP3
    ESP1 --- SCD1
    ESP1 --- EPD1
    ESP2 --- SCD2
    ESP2 --- EPD2
    ESP3 --- SCD3
    ESP3 --- EPD3
    Z1 --- NRF
    NRF --- REED
    NRF --- TILT
    NRF --- ADXL
    PI2 --- HIFI
    Z2 --- LORA
    LORA -.-> TTNNODE
    TTNNODE -.-> MQTT
```
* Velux io only if confirmed; otherwise RFLink covers Velux RTS too.
## Per-Floor Sensor Assignment

| Floor | Node | Sensors on Node | Bridge / Bus | Notes |
|---|---|---|---|---|
| Top (attic/bedroom) | ESP32-C6 (battery) | SCD41 (I2C 0x62) — CO₂, temp, humidity | I2C | Primary env sensor for sleeping area |
|  |  | WeAct 1.54" e-paper (SSD1681) | SPI | Local CO₂/T/RH display |
|  | Pi Zero W #1 (non-CO₂) | nRF52 DK → BLE mesh | BLE 5 | Battery-powered reed (bedroom window), tilt (skylight), ADXL335 (blind motor vibration) |
|  |  | LoRa not used here | — | Range covered by bottom node |
| Mid (living/kitchen) | ESP32-C6 (battery) | SCD41 (I2C 0x62) — CO₂, temp, humidity | I2C | High-occupancy zone, CO₂-driven ventilation |
|  |  | WeAct 1.54" e-paper (SSD1681) | SPI | Local CO₂/T/RH display |
|  | Pi 3B #2 (non-CO₂) | HifiBerry DAC | I2S | Audio announcements / doorbell / TTS |
|  |  | 7" Touchscreen (on Pi#1 hub) | DSI | Dashboard lives on hub, not this node |
| Bottom (garden entry/utility) | ESP32-C6 (battery) | SCD41 (I2C 0x62) — CO₂, temp, humidity | I2C | Basement / utility CO₂ monitoring |
|  |  | WeAct 1.54" e-paper (SSD1681) | SPI | Local CO₂/T/RH display |
|  | Pi Zero W #2 (non-CO₂) | IoT LoRa pHAT | SPI → LoRaWAN | Outdoor: soil moisture, garage door, hill-bottom sensor via TTN |

## Bridging Summary

| Bridge | Connects | HA Integration | Transport |
|---|---|---|---|
| Philips Hue Bridge | Zigbee lamps → HA | `hue` (LAN) | HTTPS + WebSocket |
| RFLink Gateway | Somfy RTS (433 MHz) → HA | `rflink` (serial/TCP) | USB/TCP |
| MQTT Broker (Mosquitto) | ESP32 CO₂ nodes + Pi nodes → HA | `mqtt` + auto-discovery | TCP 1883 / 8883 |
| The Things Network | LoRa pHAT → MQTT | `mqtt` (via TTN webhook) | Internet → MQTT |
| nRF52 BLE Mesh | Battery sensors → Pi Zero → MQTT | custom / ESPHome proxy | BLE → GPIO/UART → MQTT |

## Network

 ESP32 CO₂ nodes + Pi nodes: Wi-Fi → home AP → MQTT broker on RPi 5 hub
 Hue Bridge & RFLink: wired Ethernet preferred; Wi-Fi fallback
 nRF52: BLE 5 mesh to nearest Pi Zero W (top floor)
 LoRa: 868 MHz EU868 → TTN gateway (community or own) → internet → webhook → MQTT