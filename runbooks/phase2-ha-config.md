# Phase 2 Runbook: HA Core Config + Add-ons + Lovelace

**Target**: Raspberry Pi 5 (Autohome) — HAOS 18.1
**Goal**: Core config (secrets, MQTT, Hue, Velux), add-ons installed & configured, Lovelace dashboard deployed

---

## Prerequisites

- Phase 1 complete: HAOS booted, WiFi, SSH, HA UI accessible
- MQTT credentials (username/password)
- Samba credentials
- Hue Bridge IP (auto-discovery works if on same LAN)
- Velux KLF200 IP (if available, else add later)
- SSH key for GitHub (for File Editor git sync)

---

## Step 1: Configure Secrets

1. HA UI → Settings → Devices & Services → **Secrets** (or edit `/config/secrets.yaml` via File Editor)
2. Add:

```yaml
# /config/secrets.yaml
mqtt_username: "mqtt_user"
mqtt_password: "your_mqtt_password"
samba_username: "samba_user"
samba_password: "your_samba_password"
velux_host: "192.168.1.xxx"   # KLF200 IP
velux_password: "klf200_password"
```

---

## Step 2: Core Configuration (configuration.yaml)

Edit `/config/configuration.yaml` via File Editor add-on:

```yaml
# /config/configuration.yaml
homeassistant:
  name: "AutoHome"
  latitude: 48.1234
  longitude: 11.5678
  elevation: 520
  unit_system: metric
  time_zone: "Europe/Berlin"
  country: "DE"
  currency: "EUR"
  external_url: "https://autohome.local"
  internal_url: "http://autohome.local:8123"

# MQTT Broker (Mosquitto add-on)
mqtt:
  broker: "core-mosquitto"
  port: 1883
  username: "!secret mqtt_username"
  password: "!secret mqtt_password"
  discovery: true
  discovery_prefix: "homeassistant"
  birth_message:
    topic: "homeassistant/status"
    payload: "online"
  will_message:
    topic: "homeassistant/status"
    payload: "offline"

# Philips Hue (auto-discovery works if on same LAN)
hue:
  # Bridges auto-discovered via SSDP/UPnP
  # Manual override if needed:
  # bridges:
  #   - host: "192.168.1.xxx"
  #     allow_unreachable: false
  #     allow_hue_groups: true

# Velux KLF200
velux:
  host: "!secret velux_host"
  password: "!secret velux_password"
  # gateway_id: auto-detected

# Logger
logger:
  default: info
  logs:
    homeassistant.components.mqtt: debug
    homeassistant.components.hue: debug
    homeassistant.components.velux: debug

# Recorder (SQLite default, keep 3 days — reduced from 10 due to 16GB storage)
recorder:
  purge_keep_days: 3
  commit_interval: 30
  exclude:
    domains:
      - automation
      - script
      - input_boolean
      - input_number
      - input_text
      - input_select
      - input_datetime
    entity_globs:
      - "sensor.*_last_*"
      - "sensor.*_battery"

# History
history:
  include:
    domains:
      - sensor
      - binary_sensor
      - climate
      - cover
      - light
      - switch

# Person tracking (optional)
person:
  - name: "Resident"
    id: "resident"
    device_trackers: []

# Zones
zone:
  - name: "Home"
    latitude: 48.1234
    longitude: 11.5678
    radius: 100
    icon: "mdi:home"

# Default config (includes frontend, api, etc.)
default_config:

# Frontend
frontend:
  themes:
    default: "auto"
  extra_module_url:
    - "/local/lovelace/custom.js"

# Lovelace (UI mode: yaml)
lovelace:
  mode: yaml
  resources:
    - url: /local/lovelace/custom.js
      type: module

# Automation / Script / Scene (separate files)
automation: !include automations.yaml
script: !include scripts.yaml
scene: !include scenes.yaml

# ESPHome (for future sensor nodes)
esphome:
  external_url: "http://autohome.local:6052"
  internal_url: "http://autohome.local:6052"
```

---

## Step 3: Install & Configure Add-ons

### 3.1 Mosquitto Broker

1. Settings → Add-ons → Add-on Store → **Mosquitto broker** → Install
2. Configuration (use `configs/ha-addons/mosquitto/configuration.yaml`):
   - Copy content, update secrets references
3. Start → Enable "Start on boot" + "Watchdog"
4. Test: `mosquitto_sub -h autohome.local -u mqtt_user -P 'password' -t '#' -v`

### 3.2 Samba

1. Add-on Store → **Samba share** → Install
2. Configuration (use `configs/ha-addons/samba/configuration.yaml`)
3. Start → Enable "Start on boot"
4. Test: `smbclient -L //autohome.local -U samba_user`

### 3.3 File Editor

1. Add-on Store → **File editor** → Install
2. Configuration (use `configs/ha-addons/file_editor/configuration.yaml`)
3. Start → Enable "Start on boot"
4. Access: HA UI → sidebar → File Editor

### 3.4 SSH & Web Terminal

1. Add-on Store → **SSH & Web Terminal** → Install
2. Configuration (use `configs/ha-addons/ssh/configuration.yaml`)
   - Add your `ssh-ed25519` public key
3. Start → Enable "Start on boot" + "Watchdog"
4. Test: `ssh root@autohome.local -p 22222`

---

## Step 4: Deploy Lovelace Dashboard

1. File Editor → Create `/config/lovelace/` directory
2. Copy `configs/lovelace/ui-lovelace.yaml` → `/config/lovelace/ui-lovelace.yaml`
3. Copy `configs/lovelace/custom.js` → `/config/www/lovelace/custom.js`
4. Restart HA Core: Settings → System → Restart → Restart Home Assistant
5. Verify: `http://autohome.local:8123` shows dashboard

---

## Step 5: Configure MQTT Auto-Discovery Prefix

Ensure Mosquitto and HA Core use same prefix (`homeassistant`). Test:

```bash
# From workstation
mosquitto_sub -h autohome.local -u mqtt_user -P 'password' -t 'homeassistant/#' -v
```

Trigger discovery:
```bash
mosquitto_pub -h autohome.local -u mqtt_user -P 'password' \
  -t 'homeassistant/sensor/test/config' \
  -m '{"name": "Test Sensor", "state_topic": "homeassistant/sensor/test/state", "unique_id": "test_sensor_001"}'
mosquitto_pub -h autohome.local -u mqtt_user -P 'password' \
  -t 'homeassistant/sensor/test/state' -m '42'
```

Entity `sensor.test_sensor` should appear in HA.

---

## Step 6: Verify Phase 2 Complete

Run verification script:
```bash
~/Work/autohome/scripts/verify-phase2/verify-phase2.sh
```

**Acceptance Criteria**:
- [ ] `configuration.yaml` valid (HA restarts cleanly)
- [ ] Secrets loaded (no `!secret` errors in logs)
- [ ] Mosquitto add-on running, MQTT broker accepts connections
- [ ] Samba shares accessible from workstation
- [ ] File Editor opens in HA UI
- [ ] SSH add-on running on port 22222, key auth works
- [ ] Hue Bridge discovered (entities appear)
- [ ] Velux KLF200 configured (entities appear when bridge online)
- [ ] Lovelace dashboard loads at `http://autohome.local:8123`
- [ ] MQTT auto-discovery works (test sensor appears)