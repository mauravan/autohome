#!/usr/bin/env bash
# Phase 2 Verification Script
# Run from workstation (SSH to autohome)

set -euo pipefail

AUTOHOME_HOST="${AUTOHOME_HOST:-autohome.local}"
SSH_USER="${SSH_USER:-root}"
MQTT_USER="${MQTT_USER:-mqtt_user}"
MQTT_PASS="${MQTT_PASS:-}"
SAMBA_USER="${SAMBA_USER:-samba_user}"
SAMBA_PASS="${SAMBA_PASS:-}"

echo "=== Phase 2 Verification: Add-ons + Lovelace ==="
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

check_addon() {
    local slug="$1"
    local name="$2"
    echo "→ Checking $name add-on..."
    local state
    state=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha addons info --json" | jq -r ".[] | select(.slug==\"$slug\") | .state")
    if [[ "$state" == "started" ]]; then
        echo "✓ $name: $state"
        return 0
    else
        echo "✗ $name: $state (expected: started)"
        return 1
    fi
}

check_mqtt() {
    echo "→ Testing MQTT broker..."
    if [[ -z "$MQTT_PASS" ]]; then
        echo "⚠ MQTT_PASS not set, skipping auth test"
        return 0
    fi
    
    local test_topic="verify/phase2/$(date +%s)"
    local test_msg="phase2-test"
    
    # Subscribe in background
    mosquitto_sub -h "$AUTOHOME_HOST" -u "$MQTT_USER" -P "$MQTT_PASS" -t "$test_topic" -C 1 -W 5 &
    local sub_pid=$!
    
    sleep 1
    
    # Publish
    if mosquitto_pub -h "$AUTOHOME_HOST" -u "$MQTT_USER" -P "$MQTT_PASS" -t "$test_topic" -m "$test_msg"; then
        wait $sub_pid
        echo "✓ MQTT pub/sub works with auth"
        return 0
    else
        wait $sub_pid 2>/dev/null || true
        echo "✗ MQTT pub/sub failed"
        return 1
    fi
}

check_samba() {
    echo "→ Testing Samba shares..."
    if [[ -z "$SAMBA_PASS" ]]; then
        echo "⚠ SAMBA_PASS not set, skipping auth test"
        return 0
    fi

    local shares=("config" "addons" "backup" "share")
    local failed=0

    for share in "${shares[@]}"; do
        if smbclient "//$AUTOHOME_HOST/$share" -U "$SAMBA_USER%$SAMBA_PASS" -c "ls" >/dev/null 2>&1; then
            echo "  ✓ $share"
        else
            echo "  ✗ $share (not accessible)"
            ((failed++))
        fi
    done

    if [[ $failed -eq 0 ]]; then
        echo "✓ All Samba shares accessible"
        return 0
    else
        echo "✗ $failed share(s) not accessible"
        return 1
    fi
}

check_file_editor() {
    echo "→ Checking File Editor access..."
    if curl -sf -o /dev/null -w "%{http_code}" "http://$AUTOHOME_HOST:8123/hassio/app/entry/hassio_file_editor" | grep -q "200"; then
        echo "✓ File Editor UI accessible"
        return 0
    else
        echo "✗ File Editor UI not accessible"
        return 1
    fi
}

check_lovelace() {
    echo "→ Checking Lovelace YAML mode..."
    
    # Check files exist
    local files
    files=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ls -1 /config/lovelace/" 2>/dev/null)
    
    local required=("lovelace.yaml" "lighting_cards.yaml")
    local missing=0
    
    for req in "${required[@]}"; do
        if echo "$files" | grep -q "^$req$"; then
            echo "  ✓ $req"
        else
            echo "  ✗ $req (missing)"
            ((missing++))
        fi
    done
    
    # Check HA is in YAML mode
    local mode
    mode=$(ssh "$SSH_USER@$AUTOHOME_HOST" "cat /config/.storage/lovelace.dashboard" 2>/dev/null | jq -r '.data.mode // "unknown"')
    if [[ "$mode" == "yaml" ]]; then
        echo "  ✓ Lovelace mode: yaml"
    else
        echo "  ⚠ Lovelace mode: $mode (expected: yaml)"
    fi
    
    if [[ $missing -eq 0 ]]; then
        echo "✓ Lovelace files present"
        return 0
    else
        echo "✗ $missing Lovelace file(s) missing"
        return 1
    fi
}

check_dashboard() {
    echo "→ Checking HA dashboard loads..."
    if curl -sf -o /dev/null -w "%{http_code}" "http://$AUTOHOME_HOST:8123" | grep -q "200"; then
        echo "✓ Dashboard accessible at http://$AUTOHOME_HOST:8123"
        return 0
    else
        echo "✗ Dashboard not accessible"
        return 1
    fi
}

check_areas() {
    echo "→ Checking area configuration..."
    local areas
    areas=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha areas list --json" 2>/dev/null | jq -r '.[].name' | sort -u)
    
    local expected=("Top Floor" "Mid Floor" "Bottom Floor")
    local missing=0
    
    for area in "${expected[@]}"; do
        if echo "$areas" | grep -q "^$area$"; then
            echo "  ✓ $area"
        else
            echo "  ✗ $area (missing)"
            ((missing++))
        fi
    done
    
    if [[ $missing -eq 0 ]]; then
        echo "✓ All floor areas configured"
        return 0
    else
        echo "✗ $missing area(s) missing"
        return 1
    fi
}

check_scenes() {
    echo "→ Checking scenes..."
    local scenes
    scenes=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha states --json" | jq -r '.[] | select(.entity_id | startswith("scene.")) | .entity_id' | sort -u)
    
    local expected=("scene.good_morning" "scene.movie_night" "scene.good_night" "scene.all_off")
    local missing=0
    
    for scene in "${expected[@]}"; do
        if echo "$scenes" | grep -q "^$scene$"; then
            echo "  ✓ $scene"
        else
            echo "  ✗ $scene (missing)"
            ((missing++))
        fi
    done
    
    if [[ $missing -eq 0 ]]; then
        echo "✓ All expected scenes present"
        return 0
    else
        echo "✗ $missing scene(s) missing"
        return 1
    fi
}

main() {
    local failed=0
    
    check_ssh || ((failed++))
    check_addon "mosquitto" "Mosquitto" || ((failed++))
    check_addon "samba" "Samba" || ((failed++))
    check_addon "file_editor" "File Editor" || ((failed++))
    check_addon "ssh" "SSH & Web Terminal" || ((failed++))
    check_mqtt || ((failed++))
    check_samba || ((failed++))
    check_file_editor || ((failed++))
    check_lovelace || ((failed++))
    check_dashboard || ((failed++))
    check_areas || ((failed++))
    check_scenes || ((failed++))
    
    echo
    echo "=== Phase 2 Verification Complete ==="
    if [[ $failed -eq 0 ]]; then
        echo "✓ ALL CHECKS PASSED"
        exit 0
    else
        echo "✗ $failed CHECK(S) FAILED"
        exit 1
    fi
}

main "$@"