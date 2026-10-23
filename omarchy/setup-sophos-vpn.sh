#!/bin/bash
set -euo pipefail

# Profiles contain private keys: keep them outside this repository.
profile=${1:-"$HOME/Downloads/sslvpn-j.spoerer@hd24.co-client-config.ovpn"}
name='HD24 Sophos VPN'
[[ -f "$profile" ]] || { echo "Missing VPN profile: $profile" >&2; exit 1; }
if ! grep -q '^verify-x509-name ' "$profile"; then
  echo 'The profile must verify the VPN server identity.' >&2
  exit 1
fi

sudo omarchy pkg add openvpn networkmanager-openvpn
if ! nmcli -g connection.id connection show "$name" >/dev/null 2>&1; then
  result=$(nmcli connection import type openvpn file "$profile")
  uuid=$(printf '%s\n' "$result" | grep -oE '[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}' | tail -1)
  [[ -n "$uuid" ]] || { echo 'Could not identify imported VPN.' >&2; exit 1; }
  nmcli connection modify "$uuid" connection.id "$name" connection.autoconnect no
  nmcli connection modify "$uuid" +vpn.data 'username=j.spoerer,password-flags=2'
fi
echo 'Connecting to HD24. Enter VPN credentials in this terminal when prompted.'
nmcli --ask connection up "$name"
nmcli -f NAME,TYPE,DEVICE connection show --active
