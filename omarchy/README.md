# Personal Omarchy configuration

## Terminal clipboard shortcuts

Foot is the default terminal. After committing and pushing, install with
`bash omarchy/install-terminal-shortcuts.sh`, then open a new terminal window.
The installer validates the tracked configuration and backs up the existing file.

- Ctrl+C copies selected terminal text; Ctrl+V pastes the clipboard.
- Ctrl+Shift+C sends the interrupt character (stops a running command).
- Ctrl+Insert still copies; Shift+Insert and Ctrl+Shift+V still paste.

The tracked `foot.ini` retains the Omarchy theme include and existing font,
scrollback, and Enter bindings. Roll back by restoring the timestamped
`~/.config/foot/foot.ini.before-terminal-shortcuts.*` backup and opening a new window.

## Personal Omarchy power policy

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

## Open laptop panel (2026-10-22)

An open lid must keep the internal panel enabled and powered, including after
arranger saves, manual display toggles, and lock-screen DPMS. The existing policy
checks this every two seconds; a closed lid retains the normal clamshell behavior.
This intentionally overrides idle blanking on the internal panel while open.
The installer also installs the tracked monitor layout, with a backup at
`~/.config/hypr/monitors.lua.before-open-lid-policy`. DP-5 uses its preferred mode
because the connected T24i-30 supports 1920x1080, not the old forced 2560x1440.
The panel was disabled by a monitor-arranger rule saved at 11:43.
To roll back the layout, restore that backup after removing the service.

## HD24 VPN bar control

After configuring `HD24 Sophos VPN` with `setup-sophos-vpn.sh`, install the
persistent user plugin with `bash omarchy/install-vpn-widget.sh` after committing
and pushing. The shield beside the network icon is green when connected, amber
while connecting, and grey when disconnected. Click to connect through a Foot
credential prompt or disconnect. Passwords are not saved by this plugin.
Status refreshes every three seconds; repeated clicks cannot open duplicate
login prompts. Other bar settings are preserved and shell.json is backed up.
To remove, remove the `hd24.vpn` entry from the right bar layout in shell.json.

### Sophos MFA login

The OpenVPN password prompt requires the VPN password immediately followed by the
current authenticator passcode, with no separator (`<password><passcode>`).
There is no separate OTP field in this imported profile. Enter credentials only
in the Foot login window; never store combined passwords/passcodes or send them
in chat. The profile deliberately uses `password-flags=2` (not saved).

On 2026-10-23 the server was reachable but rejected login with `AUTH_FAILED`.
A later `No agents were available` occurred after retries; it does not establish
a routing or certificate fault. The launcher now explains the combined MFA input.
A successful login and internal-host access must be verified separately.

Reference: [Sophos password/passcode format](https://docs.sophos.com/nsg/sophos-firewall/21.0/Help/en-us/webhelp/onlinehelp/AdministratorHelp/Authentication/OneTimePassword/AuthenticationMFAThirdPartyAuthenticators/index.html).
