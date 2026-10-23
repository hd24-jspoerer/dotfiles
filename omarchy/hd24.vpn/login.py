#!/usr/bin/env python3
"""Interactive VPN login with sanitized per-attempt diagnostics.

nmcli keeps its real terminal: password/OTP input is never intercepted, copied,
redirected or recorded. Only whitelisted journal error categories are logged.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import termios
import time

PROFILE = 'HD24 Sophos VPN'
MESSAGES = {
    'auth_rejected': ('Anmeldung vom Sophos-Server abgelehnt.',
        'Passwort oder Einmalcode wurden nicht akzeptiert. Passwort direkt gefolgt von einem FRISCHEN Authenticator-Code eingeben, ohne Leerzeichen. Keine weiteren automatischen Anmeldeversuche.'),
    'secret_agent_missing': ('Die Passwortabfrage ist nicht verfügbar.',
        'VPN über das HD24-Schild starten und die Anmeldung im geöffneten Terminal abschließen.'),
    'certificate_error': ('VPN-Zertifikat konnte nicht geprüft werden.',
        'Systemzeit und das VPN-Profil prüfen lassen. Zertifikatsprüfung nicht abschalten.'),
    'cipher_mismatch': ('Client und Server konnten keine gemeinsame Verschlüsselung auswählen.',
        'VPN-Profil und unterstützte Verschlüsselung mit der IT abgleichen.'),
    'timeout': ('Der VPN-Verbindungsaufbau hat zu lange gedauert.',
        'Internetverbindung und Erreichbarkeit des Sophos-VPN-Zugangs prüfen.'),
    'dns_error': ('Der VPN-Servername konnte nicht aufgelöst werden.',
        'Internetverbindung und DNS prüfen.'),
    'tls_error': ('Der sichere VPN-Verbindungsaufbau ist fehlgeschlagen.',
        'VPN-Profil, Systemzeit und Servererreichbarkeit prüfen; dies belegt kein falsches Passwort.'),
    'unknown_error': ('Die VPN-Verbindung ist fehlgeschlagen.',
        'Keine eindeutige technische Ursache erkennbar. Diagnoseprotokoll prüfen lassen.'),
    'cancelled': ('VPN-Anmeldung abgebrochen.', 'Es wurde kein erfolgreicher Verbindungsaufbau bestätigt.'),
}


def classify(message):
    text = str(message).casefold()
    rules = (
        ('auth_rejected', ('auth_failed',)),
        ('secret_agent_missing', ('no agents were available', 'no valid secrets', 'could not read auth username/password')),
        ('certificate_error', ('verify error', 'certificate verify failed', 'certificate has expired')),
        ('cipher_mismatch', ('failed to negotiate cipher', 'data channel cipher negotiation failed')),
        ('dns_error', ('cannot resolve host address', 'temporary failure in name resolution')),
        ('timeout', ('connect timeout exceeded', 'tls key negotiation failed', 'inactivity timeout')),
        ('tls_error', ('tls error:', 'tls handshake failed')),
    )
    for category, markers in rules:
        if any(marker in text for marker in markers):
            return category
    return None


class Log:
    def __init__(self):
        directory = Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state'))) / 'hd24-vpn'
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        self.path = directory / ('attempt-' + str(time.time_ns()) + '.jsonl')
        self.started = time.monotonic()
        self.stream = os.fdopen(os.open(self.path, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600), 'w')

    def event(self, event, *, code=None, exit_code=None):
        # No arbitrary journal text, terminal output, credentials or caller data.
        allowed = {'start', 'journal_unavailable', 'classified_error', 'connected', 'failed', 'cancelled', 'diagnose'}
        if event not in allowed or (code is not None and code not in MESSAGES):
            raise ValueError('Non-whitelisted log entry')
        row = {'time': datetime.now(timezone.utc).isoformat(), 'profile': PROFILE,
               'event': event, 'elapsed_ms': round((time.monotonic()-self.started)*1000)}
        if code is not None: row['code'] = code
        if exit_code is not None: row['exit_code'] = int(exit_code)
        self.stream.write(json.dumps(row, ensure_ascii=False)+'\n'); self.stream.flush()

    def close(self): self.stream.close()


def state():
    result = subprocess.run(['nmcli', '-g', 'GENERAL.STATE', 'connection', 'show', PROFILE],
                            capture_output=True, text=True, timeout=8)
    return result.stdout.strip() if result.returncode == 0 else 'unknown'


def journal(cursor=None, since=None):
    command = ['journalctl', '-u', 'NetworkManager', '--no-pager', '-o', 'json']
    if cursor: command += ['--after-cursor', cursor]
    else: command += ['--since', since or '-5 minutes']
    result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    if result.returncode: raise RuntimeError('journal unavailable')
    rows = []
    for line in result.stdout.splitlines():
        try: rows.append(json.loads(line))
        except ValueError: continue
    return rows


def last_cursor():
    result = subprocess.run(['journalctl', '-u', 'NetworkManager', '-n', '0', '--show-cursor', '--no-pager'],
                            capture_output=True, text=True, timeout=5)
    for line in result.stdout.splitlines():
        if line.startswith('-- cursor: '): return line.removeprefix('-- cursor: ')
    return None


def cancel_pending():
    if state() == 'activating':
        subprocess.run(['nmcli', '-w', '5', 'connection', 'down', PROFILE],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)


def display_error(category, log):
    title, hint = MESSAGES[category]
    print('\n'+title+'\n'+hint+'\nDiagnoseprotokoll: '+str(log.path), flush=True)
    subprocess.run(['notify-send', '-u', 'normal' if category == 'cancelled' else 'critical',
                    'HD24 VPN', title+'\n'+hint], check=False)


def connect(log):
    if not sys.stdin.isatty(): raise RuntimeError('Interactive terminal required; credentials are never accepted as arguments.')
    if state() == 'activated':
        print('HD24 VPN ist bereits verbunden.');log.event('connected');return 0
    if state() == 'activating':
        print('Eine Anmeldung läuft bereits. Bitte das vorhandene VPN-Loginfenster verwenden.');return 2
    print('HD24 Sophos VPN — Anmeldung mit MFA\n'
          'Im Passwortfeld: Passwort DIREKT gefolgt vom FRISCHEN Authenticator-Code.\n'
          'Kein Leerzeichen, kein Pluszeichen; kein separates OTP-Feld.\n'
          'Passwort und Einmalcode werden weder mitgelesen noch protokolliert.\n'
          'Diagnoseprotokoll: '+str(log.path)+'\n', flush=True)
    saved_terminal = termios.tcgetattr(sys.stdin.fileno())
    since = '@'+str(time.time())
    try: cursor = last_cursor()
    except (OSError, subprocess.TimeoutExpired): cursor = None
    process = None; category = None; journal_ok = True
    log.event('start')
    try:
        # Inherit the terminal directly. Never PIPE/tee the interactive output.
        process = subprocess.Popen(['nmcli', '--ask', '-w', '120', 'connection', 'up', PROFILE])
        while process.poll() is None:
            if journal_ok:
                try:
                    for row in journal(cursor, since):
                        cursor = row.get('__CURSOR', cursor)
                        code = classify(row.get('MESSAGE', ''))
                        if code:
                            category = code; log.event('classified_error', code=code); break
                    if category:
                        cancel_pending();break
                except (OSError, RuntimeError, subprocess.TimeoutExpired):
                    journal_ok = False;log.event('journal_unavailable')
            time.sleep(0.3)
        if category and process.poll() is None:
            process.terminate()
        try: result = process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill();result = process.wait(timeout=3)
        if result == 0 and state() == 'activated':
            log.event('connected');print('\nHD24 VPN erfolgreich verbunden.', flush=True)
            subprocess.run(['notify-send', 'HD24 VPN', 'Erfolgreich verbunden'], check=False)
            return 0
        if category is None and journal_ok:
            try:
                for row in journal(cursor, since):
                    code = classify(row.get('MESSAGE', ''))
                    if code:
                        category = code; log.event('classified_error', code=code); break
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                log.event('journal_unavailable')
        category = category or ('cancelled' if result in (130, -2, -15) else 'unknown_error')
        log.event('cancelled' if category == 'cancelled' else 'failed', code=category, exit_code=result)
        display_error(category, log);return 1
    except KeyboardInterrupt:
        cancel_pending();log.event('cancelled', code='cancelled');display_error('cancelled', log);return 130
    finally:
        if process and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, saved_terminal)


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--connect', action='store_true')
    parser.add_argument('--diagnose', action='store_true');args = parser.parse_args()
    log = Log();result = 0
    try:
        if args.diagnose:
            log.event('diagnose');codes = []
            for row in journal():
                code = classify(row.get('MESSAGE', ''))
                if code and code not in codes:codes.append(code);log.event('classified_error', code=code)
            print('Aktueller VPN-Status: '+state())
            for code in codes: print(MESSAGES[code][0]+' '+MESSAGES[code][1])
            if not codes:print('Keine bekannte Fehlerkategorie im letzten 5-Minuten-Zeitraum.')
            print('Geschütztes Diagnoseprotokoll: '+str(log.path))
        else:
            result = connect(log)
            if result and sys.stdin.isatty():
                try:input('\nEnter zum Schließen. ')
                except (EOFError, KeyboardInterrupt):pass
        return result
    except (OSError, RuntimeError, subprocess.TimeoutExpired, termios.error):
        log.event('failed', code='unknown_error')
        print('VPN-Diagnose konnte nicht abgeschlossen werden. Netzwerkdienst und Journalzugriff prüfen.\n'
              'Diagnoseprotokoll: '+str(log.path), flush=True)
        if sys.stdin.isatty():
            try: input('Enter zum Schließen. ')
            except (EOFError, KeyboardInterrupt): pass
        return 1
    finally: log.close()


if __name__ == '__main__': raise SystemExit(main())
