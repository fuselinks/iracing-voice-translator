import ctypes
import os
from ctypes import wintypes
import psutil
from . import keyboard
from .irsdk import IRacingSDK

SIM_PROCESSES = {'iracingsim64dx11.exe'}

user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
ERROR_ACCESS_DENIED = 5

def elevated(pid):
    """True/False for the process' elevation; True also when its token is unreadable (higher integrity level)."""
    process = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not process:
        return None
    try:
        token = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(process, 0x0008, ctypes.byref(token)):  # TOKEN_QUERY
            return True if ctypes.get_last_error() == ERROR_ACCESS_DENIED else None
        try:
            value, size = wintypes.DWORD(), wintypes.DWORD()
            if not advapi32.GetTokenInformation(token, 20, ctypes.byref(value), 4, ctypes.byref(size)):  # TokenElevation
                return None
            return bool(value.value)
        finally:
            kernel32.CloseHandle(token)
    finally:
        kernel32.CloseHandle(process)

class WindowsChat:
    def __init__(self, config):
        self.config = config
        self.sdk = IRacingSDK()

    def target(self):
        """Foreground window handle when it belongs to the iRacing simulator, else None."""
        hwnd = user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            if psutil.Process(pid.value).name().lower() in SIM_PROCESSES:
                return hwnd
        except psutil.Error:
            pass
        return None

    def input_problem(self, window):
        """Windows silently drops SendInput aimed at a more privileged (elevated) window (UIPI)."""
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(window, ctypes.byref(pid))
        if elevated(pid.value) and not elevated(os.getpid()):
            return 'iRacing działa jako administrator — Windows zablokuje wpisywanie. Uruchom iRacing bez uprawnień administratora (albo tłumacza jako administrator).'
        return ''

    def sdk_connected(self):
        return self.sdk.connected()

    def begin_chat(self):
        self.sdk.begin_chat()

    def cancel_chat(self):
        self.sdk.cancel_chat()

    def prepare(self, text, window):
        return keyboard.plan(text, window)

    def character(self, keys):
        keyboard.press(keys)

    def enter(self):
        keyboard.enter()
