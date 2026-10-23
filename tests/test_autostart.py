import unittest
import uuid
import winreg
from unittest.mock import patch
from ivt import autostart

class AutostartTests(unittest.TestCase):
    def setUp(self):
        # A throw-away key instead of the real Run key.
        self.key=r'Software\IVT-test-'+uuid.uuid4().hex
        self.addCleanup(lambda:winreg.DeleteKey(winreg.HKEY_CURRENT_USER,self.key) if self.exists() else None)
    def exists(self):
        try:winreg.OpenKey(winreg.HKEY_CURRENT_USER,self.key).Close();return True
        except OSError:return False
    def test_enable_disable(self):
        self.assertFalse(autostart.enabled(self.key))
        autostart.set_enabled(True,self.key);self.assertTrue(autostart.enabled(self.key))
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,self.key) as handle:
            value,kind=winreg.QueryValueEx(handle,autostart.NAME)
        self.assertEqual(kind,winreg.REG_SZ);self.assertEqual(value,autostart.command())
        autostart.set_enabled(False,self.key);self.assertFalse(autostart.enabled(self.key))
        autostart.set_enabled(False,self.key)
    def test_command(self):
        self.assertIn('run.py',autostart.command());self.assertIn('pythonw.exe',autostart.command().lower())
        with patch('sys.frozen',True,create=True),patch('sys.executable',r'C:\Apps\IVT\iRacingVoiceTranslator.exe'):
            self.assertEqual(autostart.command(),r'"C:\Apps\IVT\iRacingVoiceTranslator.exe"')
    def test_targets_current_user_run_key(self):
        self.assertEqual(autostart.RUN_KEY,r'Software\Microsoft\Windows\CurrentVersion\Run')

if __name__=='__main__':unittest.main()
