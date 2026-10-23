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

if ! pacman -Q openvpn networkmanager-openvpn >/dev/null 2>&1; then
  sudo omarchy pkg add openvpn networkmanager-openvpn
fi
if ! nmcli -g connection.id connection show "$name" >/dev/null 2>&1; then
  # NetworkManager manages the gateway exception itself and cannot import
  # OpenVPN's remote_host token. Preserve every other directive and certificate.
  umask 077
  import_dir=$(mktemp -d "${XDG_RUNTIME_DIR:-/tmp}/hd24-vpn.XXXXXX")
  trap 'rm -rf -- "$import_dir"' EXIT
  sed '/^route remote_host 255\.255\.255\.255 net_gateway$/d' "$profile" > "$import_dir/hd24.ovpn"
  result=$(LC_ALL=C nmcli connection import type openvpn file "$import_dir/hd24.ovpn")
  uuid=$(printf '%s\n' "$result" | grep -oE '[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}' | tail -1)
  [[ -n "$uuid" ]] || { echo 'Could not identify imported VPN.' >&2; exit 1; }
  nmcli connection modify "$uuid" connection.id "$name" connection.autoconnect no
  nmcli connection modify "$uuid" +vpn.data 'username=j.spoerer,password-flags=2'
fi
echo 'HD24 VPN: Im Passwortfeld Passwort direkt gefolgt vom aktuellen Authenticator-Code eingeben (ohne Leerzeichen).'
nmcli --ask connection up "$name"
nmcli -f NAME,TYPE,DEVICE connection show --active
