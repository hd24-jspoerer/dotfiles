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
  # The supervised login leaves nmcli on its real terminal and logs only safe categories.
  directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
  foot --title='HD24 VPN login' python3 "$directory/login.py" --connect
fi
