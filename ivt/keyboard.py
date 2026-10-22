"""Scan-code keyboard injection (SendInput + KEYEVENTF_SCANCODE) and text preparation for iRacing chat."""
import ctypes
import re
import unicodedata
from ctypes import wintypes

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
INPUT_KEYBOARD = 1
MAPVK_VK_TO_VSC_EX = 4
SCAN_SHIFT, SCAN_CTRL, SCAN_ALT, SCAN_ENTER = 0x2A, 0x1D, 0x38, 0x1C

REPLACEMENTS = {
    '‘': "'", '’': "'", '‚': "'", '‛': "'", '′': "'", '`': "'",
    '“': '"', '”': '"', '„': '"', '‟': '"', '″': '"', '«': '"', '»': '"',
    '‐': '-', '‑': '-', '‒': '-', '–': '-', '—': '-', '―': '-', '−': '-',
    '…': '...', 'ł': 'l', 'Ł': 'L', 'ß': 'ss', 'æ': 'ae', 'Æ': 'AE',
    'ø': 'o', 'Ø': 'O', ' ': ' ', ' ': ' ', ' ': ' ',
}

def normalize_ascii(text):
    """Printable ASCII only: typographic punctuation simplified, diacritics removed, the rest dropped."""
    text = ''.join(REPLACEMENTS.get(c, c) for c in text)
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = ''.join(c if ' ' <= c <= '~' else (' ' if c.isspace() else '') for c in text)
    return re.sub(r'\s+', ' ', text).strip()

def split_message(text, limit, max_parts=3):
    """Split at sentence ends, then at word boundaries; never cut inside a word that fits."""
    if len(text) <= limit:
        return [text]
    pieces = []
    for sentence in re.split(r'(?<=[.!?])\s+', text):
        while len(sentence) > limit:
            cut = sentence.rfind(' ', 0, limit + 1)
            cut = cut if cut > 0 else limit
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if sentence:
            pieces.append(sentence)
    parts = []
    for piece in pieces:
        if parts and len(parts[-1]) + 1 + len(piece) <= limit:
            parts[-1] += ' ' + piece
        else:
            parts.append(piece)
    if len(parts) > max_parts:
        raise ValueError(f'Wiadomość za długa nawet po podziale na {max_parts} części — skróć wypowiedź')
    return parts

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', wintypes.WORD), ('wScan', wintypes.WORD), ('dwFlags', wintypes.DWORD),
                ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG), ('mouseData', wintypes.DWORD),
                ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [('uMsg', wintypes.DWORD), ('wParamL', wintypes.WORD), ('wParamH', wintypes.WORD)]

class _INPUTUNION(ctypes.Union):
    _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT), ('hi', HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [('type', wintypes.DWORD), ('u', _INPUTUNION)]

user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.VkKeyScanExW.argtypes = [wintypes.WCHAR, wintypes.HKL]
user32.VkKeyScanExW.restype = ctypes.c_short
user32.MapVirtualKeyExW.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.HKL]
user32.MapVirtualKeyExW.restype = wintypes.UINT
user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]
user32.GetKeyboardLayout.restype = wintypes.HKL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

def layout_of(hwnd):
    """Keyboard layout (HKL) active in the thread that owns the window."""
    return user32.GetKeyboardLayout(user32.GetWindowThreadProcessId(hwnd, None))

def key_event(scan, up=False):
    extended = scan > 0xFF
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0) | (KEYEVENTF_EXTENDEDKEY if extended else 0)
    event = INPUT(type=INPUT_KEYBOARD)
    event.u.ki = KEYBDINPUT(0, scan & 0xFF, flags, 0, 0)
    return event

def stroke(char, hkl):
    """Scan codes for one character in the given layout: (modifier scans, key scan)."""
    result = user32.VkKeyScanExW(char, hkl)
    if result == -1:
        raise ValueError(f'Znak {char!r} nie istnieje w układzie klawiatury iRacing')
    vk, state = result & 0xFF, (result >> 8) & 0xFF
    if state & ~0x07:
        raise ValueError(f'Znak {char!r} wymaga nieobsługiwanego modyfikatora')
    scan = user32.MapVirtualKeyExW(vk, MAPVK_VK_TO_VSC_EX, hkl)
    if not scan:
        raise ValueError(f'Brak scan code dla znaku {char!r}')
    if scan >> 8 in (0xE0, 0xE1):
        scan = 0x100 | (scan & 0xFF)
    modifiers = []
    if state & 1:
        modifiers.append(SCAN_SHIFT)
    if state & 2:
        modifiers.append(SCAN_CTRL)
    if state & 4:
        modifiers.append(SCAN_ALT)
    return tuple(modifiers), scan

def send(events):
    array = (INPUT * len(events))(*events)
    if user32.SendInput(len(events), array, ctypes.sizeof(INPUT)) != len(events):
        raise ctypes.WinError(ctypes.get_last_error())

def press(keys):
    """One atomic SendInput: modifiers down, key down, key up, modifiers up."""
    modifiers, scan = keys
    send([key_event(m) for m in modifiers] + [key_event(scan), key_event(scan, True)]
         + [key_event(m, True) for m in reversed(modifiers)])

def plan(text, hwnd):
    hkl = layout_of(hwnd)
    return [stroke(char, hkl) for char in text]

def enter():
    press(((), SCAN_ENTER))
