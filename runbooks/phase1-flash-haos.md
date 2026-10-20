# Phase 1 Runbook: Flash HAOS + WiFi + SSH

**Target**: Raspberry Pi 5 (Autohome Hub)
**Goal**: Boot HAOS 18.1, connect to WiFi, enable SSH add-on

---

## Prerequisites

- Raspberry Pi 5 Model B (BCM2712, 4/8 GB RAM)
- 64 GB microSD card (Class 10 / A2)
- USB-C power supply (5V 3A / 27W recommended for RPi 5)
- Ethernet cable (optional, for initial boot)
- WiFi credentials (SSID + WPA2-PSK)
- SSH key for GitHub/GitLab or ed25519 key

---

## Step 1: Flash HAOS 18.1 to microSD

1. Download HAOS 18.1 (Raspberry Pi 5 64-bit) from https://github.com/home-assistant/operating-system/releases
2. Flash with Raspberry Pi Imager:
   - Choose OS → Home Assistant → Home Assistant OS
   - Choose Storage → microSD card
   - Gear icon → Set hostname: `autohome`, enable SSH (authorized_keys from GitHub), configure WiFi (SSID + WPA2-PSK), set locale/timezone
   - Write

**Alternative (CLI)**:
```bash
# Find device
lsblk
# Flash (replace /dev/sdX)
sudo dd if=haos_rpi5-64-18.1.img of=/dev/sdX bs=4M status=progress conv=fsync
sync
```

---

## Step 2: First Boot (Headless via Ethernet)

1. Insert microSD, connect Ethernet, power on
2. Wait 5-10 min for HAOS to boot, expand FS, pull containers
3. Find IP: `arp -a | grep autohome` or router DHCP list
3. SSH: `ssh root@autohome.local` (or IP)
   - Password: none (SSH key auth via Imager)

---

## Step 3: Verify HAOS Boot

```bash
# Check HAOS version
ha os info

# Check Supervisor status
ha supervisor info

# Check Core status
ha core info

# Verify Supervisor containers running
ha supervisor logs --follow
```

Expect: Home Assistant Core healthy, Supervisor healthy, no unhealthy add-ons.

---

## Step 4: Switch to WiFi (if booted via Ethernet)

```bash
# Use nmcli (NetworkManager) - HAOS uses NM
nmcli device wifi list
nmcli device wifi connect "YOUR_SSID" password "YOUR_PSK"
nmcli connection show
```

Verify:
```bash
nmcli device status
ip addr show wlan0
ping -c 3 8.8.8.8
```

Remove Ethernet, verify SSH still works over WiFi.

---

## Step 5: Enable SSH Add-on (for key-based access)

1. HA UI → Settings → Add-ons → Add-on Store → **SSH & Web Terminal**
2. Install → Configuration:
   ```yaml
   authorized_keys:
     - "ssh-ed25519 AAAAC3... your-key-comment"
   allow_agent: true
   allow_remote_forwarding: true
   ```
3. Start → Enable "Start on boot" → "Watchdog"
4. SSH test: `ssh root@autohome.local`

---

## Step 6: Configure Static DHCP Reservation (Router)

- Reserve IP for `autohome` MAC (wlan0 MAC)
- Set hostname `autohome.local` in router DNS

---

## Step 7: Verify Phase 1 Complete

Run verification script:
```bash
~/Work/autohome/scripts/verify-phase1/verify-phase1.sh
```

**Acceptance Criteria**:
- [ ] HAOS 18.1 running on RPi 5 (`ha os info` shows 18.1)
- [ ] Home Assistant Core healthy (`ha core info` shows healthy)
- [ ] Supervisor healthy (`ha supervisor info` shows healthy)
- [ ] WiFi connected (`nmcli device status` shows wlan0 connected)
- [ ] SSH over WiFi works (`ssh root@autohome.local`)
- [ ] SSH add-on running with authorized_keys
- [ ] Static DHCP reservation active
- [ ] HA UI accessible at `http://autohome.local:8123`