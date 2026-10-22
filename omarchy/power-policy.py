#!/usr/bin/env python3
"""Personal Omarchy lid and idle policy. Run only inside a lid-switch inhibitor."""
import json
import os
from pathlib import Path
import subprocess
import time


def external_monitor(root=Path('/sys/class/drm')):
    for path in root.glob('card*-*/status'):
        connector = path.parent.name.split('-', 1)[-1]
        if not connector.startswith(('eDP-', 'LVDS-', 'DSI-')) and path.read_text().strip() == 'connected':
            return True
    return False


def external_power(root=Path('/sys/class/power_supply')):
    for supply in root.iterdir():
        online = supply / 'online'
        if online.exists() and online.read_text().strip() == '1':
            return True
    return False


def lid_closed(root=Path('/proc/acpi/button/lid')):
    states = list(root.glob('*/state'))
    if not states:
        raise RuntimeError('No ACPI lid state; refusing to take over lid handling')
    return any('closed' in state.read_text() for state in states)


def update_idle(powered, path):
    original = path.read_text()
    config = json.loads(original)
    idle = config.setdefault('idle', {})
    desired = {'screensaver': 1200, 'lock': 3600 if powered else 1200}
    if all(idle.get(key) == value for key, value in desired.items()):
        return
    idle.update(desired)
    # Replace atomically; preserve all unrelated JSON settings and file mode.
    tmp = path.with_name(path.name + '.power-policy.tmp')
    try:
        with tmp.open('x') as stream:
            stream.write(json.dumps(config, indent=2, ensure_ascii=False) + '\n')
        tmp.chmod(path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    print('Idle profile:', desired, flush=True)


def main():
    pending_since = None
    handled = False
    path = Path.home() / '.config/omarchy/shell.json'
    while True:
        # Read errors terminate the process and release the inhibitor, restoring
        # logind's normal lid handling instead of leaving it disabled silently.
        monitor = external_monitor()
        closed = lid_closed()
        update_idle(monitor or external_power(), path)
        eligible = closed and not monitor
        if not eligible:
            pending_since, handled = None, False
        elif pending_since is None:
            pending_since = time.monotonic()
        elif not handled and time.monotonic() - pending_since >= 5:
            # Debounce dock hotplug. Re-read immediately before requesting sleep.
            if lid_closed() and not external_monitor():
                print('Closed lid without external display: requesting suspend', flush=True)
                subprocess.run(['omarchy-system-lid-close'], check=True, timeout=20)
                subprocess.run(['systemctl', 'suspend'], check=True, timeout=30)
                handled = True
        time.sleep(2)


if __name__ == '__main__':
    main()
