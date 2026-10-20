# Phase 2 Runbook: Add-ons + Lovelace
# File: runbooks/phase2-addons-lovelace.md
# Target: autohome.local (HAOS on RPi 5)
# Goal: Install core add-ons, deploy Lovelace dashboard, verify MQTT/Samba/SSH access

---

## Prerequisites

- Phase 1 complete (HAOS 18.1, WiFi, SSH add-on running)
- SSH access: `ssh root@autohome.local`
- Secrets prepared (see Step 0 in phase2-ha-config.md)

---

## Note

Core configuration (secrets, MQTT, Hue, Velux) is documented in `phase2-ha-config.md`.
This runbook focuses on add-on installation and Lovelace deployment.

---

## Step 1: Install Core Add-ons

Via HA UI → Settings → Add-ons → Add-on Store, install and configure:

### 1.1 Mosquitto Broker
- Install → Configuration (use `configs/ha-addons/mosquitto/configuration.yaml`)
- Start → Enable "Start on boot" + "Watchdog"

### 1.2 Samba
- Install → Configuration (use `configs/ha-addons/samba/configuration.yaml`)
- Start → Enable "Start on boot" + "Watchdog"

### 1.3 File Editor
- Install → Configuration (use `configs/ha-addons/file_editor/configuration.yaml`)
- Start → Enable "Start on boot" + "Watchdog"

### 1.4 SSH & Web Terminal (if not done in Phase 1)
- Install → Configuration (use `configs/ha-addons/ssh/configuration.yaml`)
- Start → Enable "Start on boot" + "Watchdog"

---

## Step 2: Verify Add-ons Running

```bash
# SSH to autohome
ssh root@autohome.local

# Check all add-ons
ha addons list --json | jq -r '.[] | "\(.name): \(.state) \(.version)"'

# Expected: all show "started"
```

---

## Step 3: Test MQTT Broker

```bash
# From workstation (install mosquitto-clients if needed)
# Subscribe to all topics
mosquitto_sub -h autohome.local -u mqtt_user -P 'password' -t '#' -v

# In another terminal, publish test
mosquitto_pub -h autohome.local -u mqtt_user -P 'password' -t 'test/hello' -m 'world'
```

Expect: `test/hello world` appears in subscriber.

---

## Step 4: Test Samba Shares

From workstation (Linux/macOS/Windows):

```bash
# Linux/macOS
smbclient //autohome.local/config -U samba_user
# Enter password when prompted
# Should show: Domain=[WORKGROUP] OS=[] Server=[]
# smb: \> ls

# Windows: Win+R → \\autohome.local\config
```

Verify all 4 shares accessible: `config`, `addons`, `backup`, `share`.

---

## Step 5: Deploy Lovelace Dashboard

### 5.1 Copy Lovelace Files to HAOS

```bash
# From workstation (~/Work/autohome)
scp -r configs/lovelace/* root@autohome.local:/config/lovelace/

# Verify
ssh root@autohome.local "ls -la /config/lovelace/"
```

Expected:
```
/config/lovelace/
├── lovelace.yaml
├── lighting_cards.yaml
├── cover_cards.yaml
└── climate_cards.yaml
```

### 5.2 Configure HA to Use YAML Mode

1. HA UI → Settings → Dashboards → **three dots** → **Manage dashboards**
2. Click **three dots** on "Overview" → **Edit dashboard**
3. Toggle **"Take control"** → **YAML mode**
4. Save → HA will reload dashboard

**Alternative (CLI)**:
```bash
ssh root@autohome.local "cat > /config/lovelace.yaml << 'EOF'
# This file tells HA to use YAML mode
lovelace:
  mode: yaml
EOF
ha core restart"
```

Wait for restart, then visit `http://autohome.local:8123` — should show the custom dashboard with 7" touchscreen layout.

---

## Step 6: Verify Touchscreen Dashboard

If 7" DSI touchscreen attached to RPi 5:

1. HAOS auto-detects DSI display
2. Kiosk mode: Settings → Dashboards → **Overview** → **Configure** → **Kiosk mode** → Enable
3. Or create kiosk user: Settings → People → Add person → "kiosk" → assign dashboard

Test: Touchscreen shows dashboard, touch navigation works.

---

## Step 7: Run Phase 2 Verification

```bash
# From workstation
AUTOHOME_HOST=autohome.local MQTT_PASS='mqtt_password' SAMBA_PASS='samba_password' \
  ~/Work/autohome/scripts/verify-phase2/verify-phase2.sh
```

**Acceptance Criteria**:
- [ ] Mosquitto add-on running (`started`)
- [ ] Samba add-on running, 4 shares accessible
- [ ] File Editor add-on running
- [ ] SSH add-on running on port 22222
- [ ] MQTT pub/sub works with auth
- [ ] Lovelace YAML loads at `http://autohome.local:8123`
- [ ] Touchscreen shows dashboard (if attached)
- [ ] All 4 floors' sensor placeholders visible in dashboard