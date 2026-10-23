import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

spec=importlib.util.spec_from_file_location('vpn_login',Path(__file__).parents[1]/'hd24.vpn/login.py')
vpn=importlib.util.module_from_spec(spec);spec.loader.exec_module(vpn)


class VpnDiagnosticsTests(unittest.TestCase):
    def test_auth_rejection_not_mistaken_for_network_failure(self):
        self.assertEqual(vpn.classify('AUTH: Received control message: AUTH_FAILED'),'auth_rejected')
        self.assertEqual(vpn.classify('No agents were available for this request.'),'secret_agent_missing')
    def test_separate_certificate_timeout_and_cipher(self):
        for message,category in [('VERIFY ERROR: certificate has expired','certificate_error'),
            ('connect timeout exceeded','timeout'),('failed to negotiate cipher','cipher_mismatch'),
            ('RESOLVE: Cannot resolve host address','dns_error')]:
            self.assertEqual(vpn.classify(message),category)
        self.assertIsNone(vpn.classify('DEPRECATED OPTION: --cipher set to AES-128-CBC'))
    def test_first_auth_failure_cancels_pending_attempt(self):
        process=Mock();process.poll.side_effect=[None,None,1];process.wait.return_value=1
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'XDG_STATE_HOME':directory}), \
             patch.object(vpn.sys.stdin,'isatty',return_value=True), \
             patch.object(vpn.termios,'tcgetattr',return_value=[]), \
             patch.object(vpn.termios,'tcsetattr'),patch.object(vpn,'state',return_value='deactivated'), \
             patch.object(vpn,'last_cursor',return_value='cursor'), \
             patch.object(vpn,'journal',return_value=[{'MESSAGE':'AUTH_FAILED'}]), \
             patch.object(vpn.subprocess,'Popen',return_value=process) as launch, \
             patch.object(vpn,'cancel_pending') as cancel,patch.object(vpn,'display_error') as display:
            log=vpn.Log()
            self.assertEqual(vpn.connect(log),1)
            cancel.assert_called_once();launch.assert_called_once()
            self.assertEqual(display.call_args.args[0],'auth_rejected')
            process.terminate.assert_called_once();log.close()

    def test_log_cannot_include_raw_secret_or_journal_message(self):
        raw='AUTH_FAILED password=synthetic-secret OTP=654321'
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'XDG_STATE_HOME':directory}):
            log=vpn.Log();log.event('classified_error',code=vpn.classify(raw))
            with self.assertRaises(ValueError):log.event(raw)
            with self.assertRaises(ValueError):log.event('failed',code=raw)
            log.close();text=log.path.read_text()
            self.assertNotIn('synthetic-secret',text);self.assertNotIn('654321',text)
            self.assertEqual(log.path.stat().st_mode & 0o777,0o600)
            self.assertEqual(log.path.parent.stat().st_mode & 0o777,0o700)
            self.assertEqual(json.loads(text)['code'],'auth_rejected')


if __name__=='__main__':unittest.main()
