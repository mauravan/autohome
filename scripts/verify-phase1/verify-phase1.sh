#!/usr/bin/env bash
# Phase 1 Verification Script
# Run from workstation (SSH to autohome)

set -euo pipefail

AUTOHOME_HOST="${AUTOHOME_HOST:-autohome.local}"
SSH_USER="${SSH_USER:-root}"

echo "=== Phase 1 Verification: HAOS + WiFi + SSH ==="
echo "Target: $SSH_USER@$AUTOHOME_HOST"
echo

check_ssh() {
    echo "→ Testing SSH connectivity..."
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "$SSH_USER@$AUTOHOME_HOST" "echo 'SSH OK'"; then
        echo "✓ SSH OK"
        return 0
    else
        echo "✗ SSH FAILED"
        return 1
    fi
}

check_haos_version() {
    echo "→ Checking HAOS version..."
    local version
    version=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha os info --json" | jq -r '.version')
    if [[ "$version" =~ ^14\. ]]; then
        echo "✓ HAOS version: $version"
        return 0
    else
        echo "✗ HAOS version unexpected: $version"
        return 1
    fi
}

check_core_health() {
    echo "→ Checking Home Assistant Core health..."
    local state
    state=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha core info --json" | jq -r '.state')
    if [[ "$state" == "healthy" ]]; then
        echo "✓ Core state: $state"
        return 0
    else
        echo "✗ Core state: $state"
        return 1
    fi
}

check_supervisor_health() {
    echo "→ Checking Supervisor health..."
    local healthy
    healthy=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha supervisor info --json" | jq -r '.healthy')
    if [[ "$healthy" == "true" ]]; then
        echo "✓ Supervisor healthy: true"
        return 0
    else
        echo "✗ Supervisor healthy: $healthy"
        return 1
    fi
}

check_wifi() {
    echo "→ Checking WiFi connection..."
    local wifi_status
    wifi_status=$(ssh "$SSH_USER@$AUTOHOME_HOST" "nmcli -t -f DEVICE,STATE device status | grep wlan0")
    if [[ "$wifi_status" == *"connected"* ]]; then
        local ip
        ip=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ip -4 addr show wlan0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'")
        echo "✓ WiFi connected on wlan0: $ip"
        return 0
    else
        echo "✗ WiFi not connected: $wifi_status"
        return 1
    fi
}

check_ssh_addon() {
    echo "→ Checking SSH add-on status..."
    local state
    state=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha addons info --json" | jq -r '.[] | select(.slug=="ssh") | .state')
    if [[ "$state" == "started" ]]; then
        echo "✓ SSH add-on: $state"
        return 0
    else
        echo "✗ SSH add-on: $state"
        return 1
    fi
}

check_ha_ui() {
    echo "→ Checking HA UI accessibility..."
    if curl -sf -o /dev/null -w "%{http_code}" "http://$AUTOHOME_HOST:8123" | grep -q "200"; then
        echo "✓ HA UI accessible at http://$AUTOHOME_HOST:8123"
        return 0
    else
        echo "✗ HA UI not accessible"
        return 1
    fi
}

main() {
    local failed=0
    
    check_ssh || ((failed++))
    check_haos_version || ((failed++))
    check_core_health || ((failed++))
    check_supervisor_health || ((failed++))
    check_wifi || ((failed++))
    check_ssh_addon || ((failed++))
    check_ha_ui || ((failed++))
    
    echo
    echo "=== Phase 1 Verification Complete ==="
    if [[ $failed -eq 0 ]]; then
        echo "✓ ALL CHECKS PASSED"
        exit 0
    else
        echo "✗ $failed CHECK(S) FAILED"
        exit 1
    fi
}

main "$@"