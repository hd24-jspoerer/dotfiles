# Personal Omarchy power policy

For Jan's Omarchy laptop. This lives in the personal dotfiles repository, not the
shared agent-skills repository. Commit/push before installing:

```bash
bash omarchy/install-power-policy.sh
```

The graphical-session service holds a **handle-lid-switch** inhibitor while its
child process handles the lid. A physically connected external DRM monitor keeps
lid closure from suspending, including when the internal panel is disabled.
Closing the lid without an external monitor requests suspend after a five-second
hotplug grace period, including on wall power. Disconnecting the last external
monitor with the lid closed also requests suspend. It does not inhibit explicit
manual suspend, critical-battery actions, or shutdown. Failure releases the lid
inhibitor and restores logind defaults. The existing Omarchy lid binding is left
in place for clamshell display reconciliation and pre-suspend locking.

Screensaver starts at 20 minutes idle. On external power **or** with an external
monitor physically connected, locking happens at 60 minutes idle (40 minutes of
screensaver). Otherwise locking remains at 20 minutes. The policy refreshes on
connection changes every two seconds, updating shell.json only when needed and
preserving unrelated settings. Omarchy blanks displays five seconds after lock;
this is display power-off, not system suspend. This does not add idle suspend.

Verification from the host terminal:

```bash
systemctl --user status omarchy-personal-power-policy.service
systemd-inhibit --list
journalctl --user -u omarchy-personal-power-policy.service --no-pager -n 30
```

Test closing/reopening the lid with external monitors, then with only a charger,
then on battery. Check disconnecting monitors with the lid closed, and reopening
and reconnecting after resume. Do not claim those physical checks verified from
unit tests. No reboot is required. A session restart starts the enabled service.
A cable alone is insufficient: a DRM connector must report `connected`.

Rollback: `bash omarchy/install-power-policy.sh --remove`. This retains the last
idle profile; the original shell.json backup is `shell.json.before-power-policy`.
