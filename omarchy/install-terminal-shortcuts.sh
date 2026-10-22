#!/bin/bash
set -euo pipefail

source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
target="${XDG_CONFIG_HOME:-$HOME/.config}/foot/foot.ini"
foot --check-config --config "$source_dir/foot.ini"
mkdir -p -- "$(dirname -- "$target")"
if [[ -e "$target" ]]; then
  cp -p -- "$target" "$target.before-terminal-shortcuts.$(date +%Y%m%d-%H%M%S-%N)"
fi
install -m 644 -- "$source_dir/foot.ini" "$target"
foot --check-config --config "$target"
echo 'Foot shortcuts installed. Open a new terminal window to use them.'
