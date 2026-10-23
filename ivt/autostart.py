"""Optional start with Windows via HKCU\\...\\Run (current user only, no administrator rights)."""
import sys
import winreg
from pathlib import Path

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
NAME = 'iRacingVoiceTranslator'

def command():
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    exe = Path(sys.executable)
    pythonw = exe.with_name('pythonw.exe')
    return f'"{pythonw if pythonw.exists() else exe}" "{Path(__file__).resolve().parents[1] / "run.py"}"'

def enabled(key=RUN_KEY):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
            winreg.QueryValueEx(handle, NAME)
            return True
    except OSError:
        return False

def set_enabled(on, key=RUN_KEY):
    if on:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as handle:
            winreg.SetValueEx(handle, NAME, 0, winreg.REG_SZ, command())
    elif enabled(key):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as handle:
            winreg.DeleteValue(handle, NAME)
