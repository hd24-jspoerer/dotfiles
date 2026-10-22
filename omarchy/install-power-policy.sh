#!/usr/bin/env bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ ${1:-} == --remove ]]; then
  systemctl --user disable --now omarchy-personal-power-policy.service
  rm -f "$HOME/.config/systemd/user/omarchy-personal-power-policy.service" "$HOME/.local/lib/omarchy-power-policy/power-policy.py"
  systemctl --user daemon-reload
  echo 'Removed; logind lid handling restored. Current idle timeouts retained.'
  exit 0
fi
[[ $# == 0 ]] || exit 2
mkdir -p "$HOME/.local/lib/omarchy-power-policy" "$HOME/.config/systemd/user"
cp -an "$HOME/.config/omarchy/shell.json" "$HOME/.config/omarchy/shell.json.before-power-policy"
install -m 755 "$source_dir/power-policy.py" "$HOME/.local/lib/omarchy-power-policy/power-policy.py"
install -m 644 "$source_dir/power-policy.service" "$HOME/.config/systemd/user/omarchy-personal-power-policy.service"
systemctl --user daemon-reload
systemctl --user enable omarchy-personal-power-policy.service
systemctl --user restart omarchy-personal-power-policy.service
sleep 2
systemctl --user is-active omarchy-personal-power-policy.service
journalctl --user -u omarchy-personal-power-policy.service -n 8 --no-pager
