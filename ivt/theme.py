"""Dark ttk theme with every widget state mapped; all text/background pairs are >= 4.5:1 (WCAG AA)."""
import ctypes

BG = '#0f1319'        # window
SURFACE = '#171d26'   # header card, tabs
FIELD = '#222a36'     # entries, combobox fields, lists
HOVER = '#2c3646'     # active (hovered) buttons and fields
PRESSED = '#3a475c'
BORDER = '#3b4657'
TEXT = '#eef2f7'
MUTED = '#aab4c3'
DISABLED_BG = '#1a2029'
DISABLED_TEXT = '#8f9aab'
PRIMARY = '#1f5fbf'
PRIMARY_ACTIVE = '#2a6fd6'
PRIMARY_PRESSED = '#184c99'
SELECT = '#2f5d9e'
WARNING = '#ffcc66'
ERROR = '#ff8f87'
SUCCESS = '#6ee7a0'
LEVEL = '#4cc38a'

# Status dot colors (non-text indicators, >= 3:1 against SURFACE).
STATES = {
    'ready': ('Gotowy', '#4cc38a'),
    'idle': ('Brak modelu', '#8f9aab'),
    'loading': ('Ładowanie modelu', '#4ea1ff'),
    'recording': ('Nagrywanie', '#ff5c5c'),
    'recognizing': ('Rozpoznawanie', '#4ea1ff'),
    'sending': ('Wysyłanie', '#c08cff'),
    'sent': ('Wysłano', '#4cc38a'),
    'error': ('Błąd', '#ff5c5c'),
}

# (foreground, background) pairs actually used for text; checked by tests/test_theme.py.
TEXT_PAIRS = [
    (TEXT, BG), (TEXT, SURFACE), (TEXT, FIELD), (TEXT, HOVER), (TEXT, PRESSED), (MUTED, BG), (MUTED, SURFACE),
    (MUTED, FIELD), (DISABLED_TEXT, DISABLED_BG), (DISABLED_TEXT, BG), ('#ffffff', PRIMARY), ('#ffffff', PRIMARY_ACTIVE),
    ('#ffffff', PRIMARY_PRESSED), ('#ffffff', SELECT), (WARNING, SURFACE), (ERROR, SURFACE), (ERROR, BG), (SUCCESS, SURFACE),
    (WARNING, BG), (TEXT, SELECT),
]

def luminance(color):
    channels = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(foreground, background):
    a, b = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (a + 0.05) / (b + 0.05)

def dark_title_bar(root):
    try:
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass

def apply(root, style):
    font = ('Segoe UI', 10)
    style.theme_use('clam')
    root.configure(bg=BG)
    style.configure('.', background=BG, foreground=TEXT, fieldbackground=FIELD, bordercolor=BORDER, darkcolor=BG,
                    lightcolor=BG, troughcolor=FIELD, selectbackground=SELECT, selectforeground='#ffffff',
                    insertcolor=TEXT, focuscolor=BORDER, font=font)
    style.map('.', foreground=[('disabled', DISABLED_TEXT)], background=[('disabled', BG)])
    style.configure('TFrame', background=BG)
    style.configure('Card.TFrame', background=SURFACE)
    style.configure('TLabel', background=BG, foreground=TEXT)
    style.configure('Muted.TLabel', foreground=MUTED)
    style.configure('Card.TLabel', background=SURFACE, foreground=TEXT)
    style.configure('CardMuted.TLabel', background=SURFACE, foreground=MUTED)
    style.configure('Status.TLabel', background=SURFACE, foreground=TEXT, font=('Segoe UI', 18, 'bold'))
    style.configure('Message.TLabel', background=SURFACE, foreground=TEXT, font=('Segoe UI', 11, 'bold'))
    style.configure('Warning.TLabel', background=SURFACE, foreground=WARNING, font=('Segoe UI', 10, 'bold'))
    style.configure('Error.TLabel', background=BG, foreground=ERROR)
    style.configure('Heading.TLabel', font=('Segoe UI', 11, 'bold'))

    for name, normal, active, pressed, text in [('TButton', FIELD, HOVER, PRESSED, TEXT),
                                                ('Primary.TButton', PRIMARY, PRIMARY_ACTIVE, PRIMARY_PRESSED, '#ffffff')]:
        style.configure(name, background=normal, foreground=text, bordercolor=BORDER, lightcolor=normal, darkcolor=normal,
                        padding=(12, 6), focusthickness=1, focuscolor=TEXT)
        style.map(name, background=[('disabled', DISABLED_BG), ('pressed', pressed), ('active', active)],
                  foreground=[('disabled', DISABLED_TEXT), ('pressed', text), ('active', text)],
                  lightcolor=[('disabled', DISABLED_BG), ('pressed', pressed), ('active', active)],
                  darkcolor=[('disabled', DISABLED_BG), ('pressed', pressed), ('active', active)],
                  bordercolor=[('disabled', BORDER), ('focus', TEXT)])

    style.configure('TEntry', fieldbackground=FIELD, foreground=TEXT, insertcolor=TEXT, bordercolor=BORDER,
                    lightcolor=FIELD, darkcolor=FIELD, padding=4)
    style.map('TEntry', fieldbackground=[('disabled', DISABLED_BG), ('readonly', FIELD)],
              foreground=[('disabled', DISABLED_TEXT)], bordercolor=[('focus', PRIMARY_ACTIVE)],
              lightcolor=[('focus', FIELD)])

    style.configure('TCombobox', fieldbackground=FIELD, background=FIELD, foreground=TEXT, arrowcolor=TEXT,
                    bordercolor=BORDER, lightcolor=FIELD, darkcolor=FIELD, padding=4, arrowsize=14)
    style.map('TCombobox',
              fieldbackground=[('disabled', DISABLED_BG), ('readonly', 'active', HOVER), ('readonly', FIELD)],
              background=[('disabled', DISABLED_BG), ('pressed', PRESSED), ('active', HOVER), ('readonly', FIELD)],
              foreground=[('disabled', DISABLED_TEXT), ('readonly', TEXT)],
              selectbackground=[('readonly', 'focus', SELECT), ('readonly', FIELD)],
              selectforeground=[('readonly', 'focus', '#ffffff'), ('readonly', TEXT)],
              arrowcolor=[('disabled', DISABLED_TEXT), ('active', TEXT)],
              bordercolor=[('focus', PRIMARY_ACTIVE)])
    # The drop-down list is a classic Tk Listbox inside a toplevel; it ignores ttk styles.
    root.option_add('*TCombobox*Listbox.background', FIELD)
    root.option_add('*TCombobox*Listbox.foreground', TEXT)
    root.option_add('*TCombobox*Listbox.selectBackground', SELECT)
    root.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')
    root.option_add('*TCombobox*Listbox.font', font)
    root.option_add('*TCombobox*Listbox.borderWidth', 0)

    style.configure('TCheckbutton', background=BG, foreground=TEXT, indicatorbackground=FIELD,
                    indicatorforeground='#ffffff', indicatorrelief='flat', padding=(0, 3))
    style.map('TCheckbutton', background=[('active', BG)], foreground=[('disabled', DISABLED_TEXT), ('active', TEXT)],
              indicatorbackground=[('disabled', DISABLED_BG), ('selected', 'active', PRIMARY_ACTIVE),
                                   ('selected', PRIMARY), ('active', HOVER)])

    style.configure('TNotebook', background=BG, borderwidth=0, tabmargins=(0, 4, 0, 0))
    style.configure('TNotebook.Tab', background=SURFACE, foreground=MUTED, padding=(14, 6), bordercolor=BORDER,
                    lightcolor=SURFACE, font=('Segoe UI', 10, 'bold'))
    style.map('TNotebook.Tab', background=[('selected', BG), ('active', HOVER)],
              foreground=[('selected', TEXT), ('active', TEXT)], lightcolor=[('selected', BG)],
              expand=[('selected', (0, 2, 0, 0))])

    style.configure('Level.Horizontal.TProgressbar', background=LEVEL, troughcolor=FIELD, bordercolor=SURFACE,
                    lightcolor=LEVEL, darkcolor=LEVEL, thickness=10)
    style.configure('TScrollbar', background=FIELD, troughcolor=BG, arrowcolor=TEXT, bordercolor=BG,
                    lightcolor=FIELD, darkcolor=FIELD)
    style.map('TScrollbar', background=[('active', HOVER), ('pressed', PRESSED)])
    style.configure('TSeparator', background=BORDER)
    dark_title_bar(root)

def text_widget(widget):
    """Colors for classic tk.Text widgets."""
    widget.configure(bg=FIELD, fg=TEXT, insertbackground=TEXT, selectbackground=SELECT, selectforeground='#ffffff',
                     relief='flat', highlightthickness=1, highlightbackground=BORDER, highlightcolor=PRIMARY_ACTIVE,
                     font=('Segoe UI', 10), padx=8, pady=6)
