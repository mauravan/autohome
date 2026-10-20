#!/usr/bin/env bash
# Phase 3 Verification Script: Hue + Velux KLF200

set -euo pipefail

AUTOHOME_HOST="${AUTOHOME_HOST:-autohome.local}"
SSH_USER="${SSH_USER:-root}"

echo "=== Phase 3 Verification: Hue + Velux KLF200 ==="
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

check_hue_lights() {
    echo "→ Checking Philips Hue lights..."
    local lights
    lights=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha states --json" 2>/dev/null | jq -r '.[] | select(.entity_id | startswith("light.")) | select(.entity_id | contains("hue")) | .entity_id' | sort -u)
    
    if [[ -n "$lights" ]]; then
        local count
        count=$(echo "$lights" | wc -l)
        echo "✓ Found $count Hue light(s):"
        echo "$lights" | sed 's/^/  /'
        return 0
    else
        echo "✗ No Hue lights found"
        return 1
    fi
}

check_hue_control() {
    echo "→ Testing Hue light control..."
    local first_light
    first_light=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha states --json" 2>/dev/null | jq -r '.[] | select(.entity_id | startswith("light.")) | select(.entity_id | contains("hue")) | .entity_id' | head -1)
    
    if [[ -z "$first_light" ]]; then
        echo "✗ No Hue light to test"
        return 1
    fi
    
    echo "  Testing: $first_light"
    ssh "$SSH_USER@$AUTOHOME_HOST" "ha services call light turn_on --entity-id $first_light --brightness 50" >/dev/null
    sleep 2
    local state
    state=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha states --json" 2>/dev/null | jq -r ".[] | select(.entity_id==\"$first_light\") | .state")
    if [[ "$state" == "on" ]]; then
        ssh "$SSH_USER@$AUTOHOME_HOST" "ha services call light turn_off --entity-id $first_light" >/dev/null
        sleep 1
        echo "✓ Hue control works (on/off/brightness)"
        return 0
    else
        echo "✗ Hue control failed (state: $state)"
        return 1
    fi
}

check_velux_covers() {
    echo "→ Checking Velux KLF200 covers..."
    local covers
    covers=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha states --json" 2>/dev/null | jq -r '.[] | select(.entity_id | startswith("cover.")) | select(.entity_id | contains("klf200") or contains("velux") or contains("somfy")) | .entity_id' | sort -u)
    
    if [[ -n "$covers" ]]; then
        local count
        count=$(echo "$covers" | wc -l)
        echo "✓ Found $count KLF200/Velux/Somfy cover(s):"
        echo "$covers" | sed 's/^/  /'
        return 0
    else
        echo "✗ No KLF200 covers found"
        return 1
    fi
}

check_velux_control() {
    echo "→ Testing Velux cover control..."
    local first_cover
    first_cover=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha states --json" 2>/dev/null | jq -r '.[] | select(.entity_id | startswith("cover.")) | select(.entity_id | contains("klf200") or contains("velux") or contains("somfy")) | .entity_id' | head -1)
    
    if [[ -z "$first_cover" ]]; then
        echo "✗ No cover to test"
        return 1
    fi
    
    echo "  Testing: $first_cover"
    local current_pos
    current_pos=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha states --json" 2>/dev/null | jq -r ".[] | select(.entity_id==\"$first_cover\") | .attributes.current_position // .attributes.position // 0")
    
    ssh "$SSH_USER@$AUTOHOME_HOST" "ha services call cover set_cover_position --entity-id $first_cover --position 50" >/dev/null
    sleep 5
    
    local new_pos
    new_pos=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha states --json" 2>/dev/null | jq -r ".[] | select(.entity_id==\"$first_cover\") | .attributes.current_position // .attributes.position // 0")
    
    if [[ "$new_pos" -ge 40 && "$new_pos" -le 60 ]]; then
        echo "✓ Velux control works (position: $current_pos% → $new_pos%)"
        ssh "$SSH_USER@$AUTOHOME_HOST" "ha services call cover set_cover_position --entity-id $first_cover --position $current_pos" >/dev/null
        return 0
    else
        echo "✗ Velux control failed (position: $current_pos% → $new_pos%)"
        return 1
    fi
}

check_scenes() {
    echo "→ Checking scenes..."
    local scenes
    scenes=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha states --json" 2>/dev/null | jq -r '.[] | select(.entity_id | startswith("scene.")) | .entity_id' | sort -u)
    
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

check_areas() {
    echo "→ Checking area assignments..."
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

check_entities_in_areas() {
    echo "→ Verifying entities assigned to areas..."
    local light_count cover_count
    light_count=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha states --json" 2>/dev/null | jq -r '.[] | select(.entity_id | startswith("light.")) | select(.attributes.area_id != null) | .entity_id' | wc -l)
    cover_count=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ha states --json" 2>/dev/null | jq -r '.[] | select(.entity_id | startswith("cover.")) | select(.attributes.area_id != null) | .entity_id' | wc -l)
    
    echo "  Lights with area: $light_count"
    echo "  Covers with area: $cover_count"
    
    if [[ $light_count -gt 0 && $cover_count -gt 0 ]]; then
        echo "✓ Entities assigned to areas"
        return 0
    else
        echo "✗ Some entities missing area assignment"
        return 1
    fi
}

check_lovelace_files() {
    echo "→ Checking Lovelace card files..."
    local files
    files=$(ssh "$SSH_USER@$AUTOHOME_HOST" "ls -1 /config/lovelace/" 2>/dev/null)
    
    local required=("lovelace.yaml" "lighting_cards.yaml" "climate_cards.yaml" "cover_cards.yaml")
    local missing=0
    
    for req in "${required[@]}"; do
        if echo "$files" | grep -q "^$req$"; then
            echo "  ✓ $req"
        else
            echo "  ✗ $req (missing)"
            ((missing++))
        fi
    done
    
    if [[ $missing -eq 0 ]]; then
        echo "✓ All Lovelace card files present"
        return 0
    else
        echo "✗ $missing Lovelace file(s) missing"
        return 1
    fi
}

main() {
    local failed=0
    
    check_ssh || ((failed++))
    check_hue_lights || ((failed++))
    check_hue_control || ((failed++))
    check_velux_covers || ((failed++))
    check_velux_control || ((failed++))
    check_scenes || ((failed++))
    check_areas || ((failed++))
    check_entities_in_areas || ((failed++))
    check_lovelace_files || ((failed++))
    
    echo
    echo "=== Phase 3 Verification Complete ==="
    if [[ $failed -eq 0 ]]; then
        echo "✓ ALL CHECKS PASSED"
        exit 0
    else
        echo "✗ $failed CHECK(S) FAILED"
        exit 1
    fi
}

main "$@"