#!/bin/bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
target="$HOME/.config/omarchy/plugins/hd24.vpn"
mkdir -p "$target"
install -m 644 "$source_dir"/hd24.vpn/{manifest.json,BarWidget.qml,toggle.sh,login.py} "$target/"
python - <<'PY'
import json, os, shutil, time
from pathlib import Path
p = Path.home() / '.config/omarchy/shell.json'
s = p.read_text()
c = json.loads(s)
right = c.setdefault('bar', {}).setdefault('layout', {}).setdefault('right', [])
if not any(x.get('id') == 'hd24.vpn' for x in right):
    index = next((i for i,x in enumerate(right) if x.get('id') == 'omarchy.network'), len(right))
    right.insert(index, {'id': 'hd24.vpn'})
    shutil.copy2(p, p.with_name('shell.json.before-vpn-' + str(time.time_ns())))
    tmp = p.with_name('shell.json.vpn-tmp')
    tmp.write_text(json.dumps(c, indent=2) + '\n')
    os.replace(tmp, p)
PY
omarchy-shell shell rescanPlugins
