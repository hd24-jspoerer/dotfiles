#!/bin/bash
set -uo pipefail
exec 9>"${XDG_RUNTIME_DIR:?}/hd24-vpn-toggle.lock"
flock -n 9 || exit 0
name='HD24 Sophos VPN'
state=$(nmcli -g GENERAL.STATE connection show "$name")
if [[ "$state" == activated ]]; then
  if nmcli connection down "$name"; then
    notify-send 'HD24 VPN' 'Disconnected'
  else
    notify-send -u critical 'HD24 VPN' 'Could not disconnect'
  fi
elif [[ "$state" == activating ]]; then
  notify-send 'HD24 VPN' 'Connection in progress. Complete the VPN login prompt.'
else
  # Keep credentials in the interactive terminal, never in arguments or files.
  foot --title='HD24 VPN login' bash -c '
    echo "HD24 VPN — enter your VPN password and required MFA."
    if nmcli --ask connection up "HD24 Sophos VPN"; then
      notify-send "HD24 VPN" "Connected"
    else
      notify-send -u critical "HD24 VPN" "Connection failed or cancelled"
      read -r -p "Press Enter to close."
    fi
  '
fi
