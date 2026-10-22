import ctypes
from ctypes import wintypes
from pathlib import Path
import numpy as np
import psutil
from PIL import Image, ImageGrab
from pynput.keyboard import Controller, Key
from .config import DATA

user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.SetProcessDPIAware()

class WindowsChat:
    def __init__(self, config):
        self.config = config
        self.keyboard = Controller()

    def target(self):
        hwnd = user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            if psutil.Process(pid.value).name().lower() in {'iracingsim64dx11.exe', 'iracingsim64.exe'}:
                return hwnd
        except psutil.Error:
            pass
        return None

    def capture(self):
        coords = tuple(int(v.strip()) for v in self.config.roi.split(','))
        if len(coords) != 4 or coords[2] <= coords[0] or coords[3] <= coords[1]:
            raise ValueError('Obszar kalibracji: left,top,right,bottom')
        return ImageGrab.grab(bbox=coords, all_screens=True).convert('L')

    def calibrate(self, state):
        if not self.target():
            raise RuntimeError('Aktywuj symulator iRacing przed upływem odliczania')
        DATA.mkdir(parents=True, exist_ok=True)
        self.capture().save(DATA / (state + '.png'))

    def matches(self, state):
        try:
            current = np.asarray(self.capture(), dtype=float)
            reference = np.asarray(Image.open(DATA / (state + '.png')), dtype=float)
            other = np.asarray(Image.open(DATA / (('closed' if state == 'open' else 'open') + '.png')), dtype=float)
            if current.shape != reference.shape or other.shape != reference.shape:
                return False
            error = np.abs(current - reference).mean()
            separation = np.abs(reference - other).mean()
            return separation > 2 * self.config.visual_threshold and error < self.config.visual_threshold and error + self.config.visual_threshold < np.abs(current - other).mean()
        except (OSError, ValueError):
            return False

    def opened(self): return self.matches('open')
    def closed(self): return self.matches('closed')

    def key(self, name):
        key = Key.enter if name == 'enter' else name
        self.keyboard.press(key)
        self.keyboard.release(key)

    def character(self, char):
        # pynput uses Windows Unicode input for characters outside the active layout.
        self.keyboard.type(char)
