"""Minimal official iRacing SDK client: read-only connection status and chat broadcast commands.

Mirrors irsdk_defines.h / irsdk_utils.cpp: the header starts with `int ver; int status; ...`,
status bit irsdk_stConnected = 1, and broadcasts are SendNotifyMessage(HWND_BROADCAST,
RegisterWindowMessage("IRSDK_BROADCASTMSG"), MAKELONG(msg, var1), MAKELONG(var2, var3)).
"""
import ctypes
import re
from ctypes import wintypes

MEMMAP_NAME = 'Local\\IRSDKMemMapFileName'
BROADCAST_NAME = 'IRSDK_BROADCASTMSG'
STATUS_CONNECTED = 1
BROADCAST_CHAT_COMMAND = 8   # irsdk_BroadcastChatComand
CHAT_BEGIN = 1               # irsdk_ChatCommand_BeginChat
CHAT_CANCEL = 3              # irsdk_ChatCommand_Cancel
HWND_BROADCAST = 0xFFFF
FILE_MAP_READ = 0x0004

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.OpenFileMappingW.restype = wintypes.HANDLE
kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
kernel32.MapViewOfFile.restype = ctypes.c_void_p
kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
user32.RegisterWindowMessageW.restype = wintypes.UINT
user32.SendNotifyMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendNotifyMessageW.restype = wintypes.BOOL

def make_long(low, high):
    return (low & 0xFFFF) | ((high & 0xFFFF) << 16)

class IRacingSDK:
    def __init__(self):
        self.message = 0

    def connected(self):
        """True when the simulator publishes telemetry with the connected bit set. Read-only, no handle kept."""
        handle = kernel32.OpenFileMappingW(FILE_MAP_READ, False, MEMMAP_NAME)
        if not handle:
            return False
        try:
            view = kernel32.MapViewOfFile(handle, FILE_MAP_READ, 0, 0, 8)
            if not view:
                return False
            try:
                return bool(ctypes.c_int.from_address(view + 4).value & STATUS_CONNECTED)
            finally:
                kernel32.UnmapViewOfFile(view)
        finally:
            kernel32.CloseHandle(handle)

    def session_yaml(self):
        """Session info YAML (header: sessionInfoLen at +16, sessionInfoOffset at +20), or '' when unavailable."""
        handle = kernel32.OpenFileMappingW(FILE_MAP_READ, False, MEMMAP_NAME)
        if not handle:
            return ''
        try:
            view = kernel32.MapViewOfFile(handle, FILE_MAP_READ, 0, 0, 0)
            if not view:
                return ''
            try:
                if not ctypes.c_int.from_address(view + 4).value & STATUS_CONNECTED:
                    return ''
                length = ctypes.c_int.from_address(view + 16).value
                offset = ctypes.c_int.from_address(view + 20).value
                if length <= 0 or offset <= 0:
                    return ''
                raw = ctypes.string_at(view + offset, length)
                return raw.split(b'\0', 1)[0].decode('cp1252', errors='replace')
            finally:
                kernel32.UnmapViewOfFile(view)
        finally:
            kernel32.CloseHandle(handle)

    def session_names(self):
        """Track name and driver names from the current session, for the speech-recognition vocabulary."""
        return session_names(self.session_yaml())

    def broadcast(self, command, var1=0, var2=0, var3=0):
        if not self.message:
            self.message = user32.RegisterWindowMessageW(BROADCAST_NAME)
            if not self.message:
                raise ctypes.WinError(ctypes.get_last_error())
        if not user32.SendNotifyMessageW(HWND_BROADCAST, self.message, make_long(command, var1), make_long(var2, var3)):
            raise ctypes.WinError(ctypes.get_last_error())

    def begin_chat(self):
        self.broadcast(BROADCAST_CHAT_COMMAND, CHAT_BEGIN)

    def cancel_chat(self):
        self.broadcast(BROADCAST_CHAT_COMMAND, CHAT_CANCEL)

def session_names(yaml_text):
    names = []
    for key in ('TrackDisplayName', 'TrackDisplayShortName', 'UserName', 'TeamName'):
        for value in re.findall(rf'^\s*{key}:\s*(.+?)\s*$', yaml_text, re.MULTILINE):
            value = value.strip().strip('"\'')
            if value and value.lower() not in ('pace car', 'safety car'):
                names.append(value)
    return list(dict.fromkeys(names))
