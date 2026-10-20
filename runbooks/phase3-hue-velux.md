# Phase 3 Runbook: Hue + Velux KLF200

**Target**: autohome.local (HAOS on RPi 5)
**Goal**: Philips Hue lamps + Somfy io / Velux io blinds & windows controllable from HA

---

## Prerequisites

- Phase 1 & 2 complete
- Philips Hue Bridge v2 connected to LAN (Ethernet)
- Velux KLF200 connected to LAN (Ethernet)
- Somfy io blinds & Velux io roof windows paired to KLF200 (via KLF200 app/USB)
- Static DHCP reservations for Hue Bridge & KLF200

---

## Step 1: Philips Hue Integration

### 1.1 Verify Hue Bridge Discovery

```bash
# From HAOS SSH
ha discovery list | grep -i hue
# Or check UI: Settings → Devices & Services → Integrations → "Discovered"
```

Should show: `Philips Hue (192.168.x.x)`

### 1.2 Configure Hue Integration

1. HA UI → Settings → Devices & Services → **Integrations**
2. Find "Philips Hue" → **Configure**
3. Press link button on Hue Bridge → **Submit**
4. Select areas for each light
5. Done

### 1.3 Verify Lights Appear

```bash
# Check entities
ha states | grep -i hue
# Or via UI: Developer Tools → States → filter "light."
```

Expect: `light.living_room_main`, `light.bedroom_left`, etc.

---

## Step 2: Velux KLF200 Integration

### 2.1 Enable KLF200 LAN API

1. Connect to KLF200 WiFi hotspot (or Ethernet)
2. Browse to `http://klf200.local` (or its IP)
3. Login (default: admin / admin)
4. Settings → **LAN API** → Enable → Set password
5. Note: **GW Password** (different from admin password)

### 2.2 Add Velux Integration

1. HA UI → Settings → Devices & Services → **Add Integration**
2. Search "Velux" → Select **Velux KLF200**
3. Host: `klf200.local` (or static IP)
4. Password: **GW Password** from step 2.1
5. Submit

### 2.3 Verify Covers

```bash
ha states | grep -i cover
```

Expect entities like:
- `cover.top_floor_bedroom_blind_left`
- `cover.top_floor_bedroom_blind_right`
- `cover.top_floor_skylight`
- `cover.mid_floor_living_blind`
- `cover.mid_floor_kitchen_window`
- etc.

---

## Step 3: Organize Entities (Areas + Labels)

### 3.1 Assign Areas

Settings → Areas → Create per floor:
- `Top Floor`
- `Mid Floor`
- `Bottom Floor`

Assign each light/cover to appropriate area.

### 3.2 Add Labels (Optional but Recommended)

Settings → Labels → Create:
- `blind` — all Somfy io blinds
- `roof_window` — all Velux io windows
- `hue_light` — all Hue lamps
- `co2_sensor` — SCD41 sensors (Phase 4)

---

## Step 4: Create Scenes & Automations

### 4.1 Scenes (via UI or YAML)

**File**: `/config/scenes.yaml` (include in `configuration.yaml`)

```yaml
# File: /config/scenes.yaml (include in configuration.yaml)
# Scenes for lighting + blinds

- name: "Good Morning"
  entities:
    light.top_floor_bedroom_main: on
    light.mid_floor_kitchen_main: on
    cover.top_floor_bedroom_blind_left: open
    cover.top_floor_bedroom_blind_right: open
    cover.mid_floor_living_room_blind: open

- name: "Movie Night"
  entities:
    light.mid_floor_living_room_main:
      state: on
      brightness: 30
      color_temp: 370
    light.mid_floor_living_room_accent:
      state: on
      brightness: 10
      rgb_color: [255, 50, 0]
    cover.mid_floor_living_room_blind: closed

- name: "Good Night"
  entities:
    light.all_lights: off
    cover.all_blinds: closed
    cover.all_roof_windows: closed

- name: "All Off"
  entities:
    light.all_lights: off
```

### 4.2 Automation: Blind Position Sync (Optional)

```yaml
# File: /config/automations/blind_sync.yaml
automation:
  - alias: "Sync bedroom blinds position"
    trigger:
      - platform: state
        entity_id: cover.top_floor_bedroom_blind_left
        attribute: current_position
    action:
      - service: cover.set_cover_position
        target:
          entity_id: cover.top_floor_bedroom_blind_right
        data:
          position: "{{ trigger.to_state.attributes.current_position }}"
```

---

## Step 5: Add to Lovelace Dashboard

Update `/config/lovelace/lovelace.yaml` to include lighting cards (already in `lighting_cards.yaml`).

Verify on touchscreen:
- Each light shows color/brightness controls
- Each cover shows position slider (0-100%)
- Scenes appear as buttons

---

## Step 6: Run Phase 3 Verification

```bash
~/Work/autohome/scripts/verify-phase3/verify-phase3.sh
```

**Acceptance Criteria**:
- [ ] All Hue lights controllable from HA (on/off/brightness/color)
- [ ] All Somfy io blinds open/close/position from HA
- [ ] All Velux io roof windows open/close/position from HA
- [ ] Scenes "Good Morning", "Movie Night", "Good Night", "All Off" work
- [ ] Entities organized by Area (Top/Mid/Bottom Floor)
- [ ] Dashboard shows all lights + covers with correct controls

---

## Troubleshooting

### Hue not discovered
- Ensure Bridge on same VLAN/subnet
- Check mDNS: `avahi-browse -t _hue._tcp`
- Manual config in `configuration.yaml`:
```yaml
hue:
  bridges:
    - host: 192.168.1.xx
      allow_unreachable: true
```

### KLF200 connection fails
- Verify GW Password (not admin password)
- Check KLF200 firmware ≥ 2.0.0
- LAN API must be enabled in KLF200 settings
- Try IP instead of hostname: `192.168.1.xx`

### Covers show "unknown" position
- KLF200 only reports position for io-homecontrol devices
- RTS (433MHz) devices report open/closed only
- Pair io devices via KLF200 app first

### Entity names are cryptic
- Use HA UI → Settings → Devices → click device → rename entity
- Or customize via `customize.yaml`:
```yaml
homeassistant:
  customize:
    cover.klf200_1_2_3:
      friendly_name: "Top Floor Bedroom Blind Left"
```