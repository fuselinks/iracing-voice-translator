import ctypes
from ctypes import wintypes
import psutil
from pynput.keyboard import Controller, Key
from .irsdk import IRacingSDK

SIM_PROCESSES = {'iracingsim64dx11.exe'}

user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

class WindowsChat:
    def __init__(self, config):
        self.config = config
        self.sdk = IRacingSDK()
        self.keyboard = Controller()

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

    def sdk_connected(self):
        return self.sdk.connected()

    def begin_chat(self):
        self.sdk.begin_chat()

    def cancel_chat(self):
        self.sdk.cancel_chat()

    def character(self, char):
        self.keyboard.type(char)

    def enter(self):
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)
