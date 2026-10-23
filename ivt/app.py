import os
os.environ['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS'] = '1'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import logging
import logging.handlers
import queue
import threading
import time
import uuid
import tkinter as tk
from tkinter import ttk, messagebox
from collections import deque
from dataclasses import replace
from .config import Config, DATA, HOTKEYS
from .audio import Recorder, usable, microphones
from .engine import Engine
from .chat import Sender, Cancelled
from .windows import WindowsChat
from . import theme, autostart

log = logging.getLogger(__name__)
CHOICES = [('model', 'Model', ['small', 'medium', 'large-v3']), ('device', 'Obliczenia', ['auto', 'cuda', 'cpu']),
           ('engine', 'Silnik', ['direct', 'two-stage', 'polish']), ('mode', 'Tryb przycisku', ['ptt', 'toggle']),
           ('hotkey', 'Skrót klawiatury', HOTKEYS)]
# key, label, display scale (seconds shown as ms), minimum, maximum — in config units
NUMBERS = [('gain', 'Wzmocnienie', 1, 0.1, 10), ('silence', 'Próg ciszy (RMS)', 1, 0.0001, 0.5),
           ('max_chars', 'Limit znaków', 1, 10, 500), ('open_delay', 'Pauza po otwarciu [ms]', 1000, 0.05, 3),
           ('send_delay', 'Pauza przed Enter [ms]', 1000, 0.01, 3), ('char_delay', 'Pauza między znakami [ms]', 1000, 0, 0.2)]

class App:
    def __init__(self, root):
        self.root = root
        self.config = Config.load()
        self.events = queue.Queue()
        self.recorder = Recorder()
        self.cancel = threading.Event()
        self.busy = False
        self.recording = False
        self.pending = None
        self.history = deque(maxlen=10)
        self.engine = Engine(self.config)
        self.io = WindowsChat(self.config)
        self.sender = Sender(self.io, self.config)
        self.binding = False
        self.input_sources = set()
        self.joysticks = {}
        self.joystick_guids = {}
        self.button_log = deque(maxlen=4)
        self.tray = None
        self.state = 'idle'
        self.state_since = time.monotonic()
        self.sdk_checked = 0
        root.title('iRacing Voice Translator')
        scale = root.winfo_fpixels('1i') / 96
        root.geometry(f'{int(600 * scale)}x{int(700 * scale)}')
        root.minsize(int(540 * scale), int(600 * scale))
        theme.apply(root, ttk.Style(root))
        self.build_header()
        notebook = ttk.Notebook(root)
        notebook.pack(fill='both', expand=True, padx=12, pady=(10, 12))
        for title, builder in [('Start', self.build_start), ('Ustawienia', self.build_settings),
                               ('Historia', self.build_history), ('Diagnostyka', self.build_diagnostics)]:
            frame = ttk.Frame(notebook, padding=14)
            builder(frame)
            notebook.add(frame, text=title)
        self.notebook = notebook
        root.protocol('WM_DELETE_WINDOW', self.hide)
        self.set_state('idle', 'Załaduj model na zakładce Start')
        if Config.load_problem:
            self.show_warning(Config.load_problem)
        self.init_inputs()
        self.refresh_wheels()
        self.tick()

    # ---------- layout ----------
    def build_header(self):
        head = ttk.Frame(self.root, style='Card.TFrame', padding=(16, 12))
        head.pack(fill='x')
        top = ttk.Frame(head, style='Card.TFrame')
        top.pack(fill='x')
        self.dot = tk.Canvas(top, width=20, height=20, bg=theme.SURFACE, highlightthickness=0)
        self.dot_id = self.dot.create_oval(2, 2, 18, 18, outline='')
        self.dot.pack(side='left', padx=(0, 10))
        self.state_text = tk.StringVar()
        ttk.Label(top, textvariable=self.state_text, style='Status.TLabel').pack(side='left')
        self.sdk_text = tk.StringVar(value='iRacing: sprawdzanie…')
        ttk.Label(top, textvariable=self.sdk_text, style='CardMuted.TLabel').pack(side='right')
        self.detail = tk.StringVar()
        self.wrapped = [ttk.Label(head, textvariable=self.detail, style='CardMuted.TLabel')]
        self.wrapped[0].pack(anchor='w', pady=(4, 8))
        level = ttk.Frame(head, style='Card.TFrame')
        level.pack(fill='x')
        ttk.Label(level, text='Mikrofon', style='CardMuted.TLabel', width=10).pack(side='left')
        self.level = ttk.Progressbar(level, maximum=100, style='Level.Horizontal.TProgressbar')
        self.level.pack(side='left', fill='x', expand=True)
        self.last_pl = tk.StringVar(value='PL: —')
        self.last_en = tk.StringVar(value='EN: —')
        for var, style in [(self.last_pl, 'CardMuted.TLabel'), (self.last_en, 'Message.TLabel')]:
            label = ttk.Label(head, textvariable=var, style=style)
            label.pack(anchor='w', pady=(6, 0))
            self.wrapped.append(label)
        self.warning_text = tk.StringVar()
        self.warning_label = ttk.Label(head, textvariable=self.warning_text, style='Warning.TLabel')
        self.wrapped.append(self.warning_label)
        head.bind('<Configure>', lambda e: [w.configure(wraplength=max(200, e.width - 40)) for w in self.wrapped])

    def row(self, parent, pady=4):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=pady)
        return frame

    def build_start(self, f):
        self.model_info = tk.StringVar()
        ttk.Label(f, textvariable=self.model_info, style='Heading.TLabel').pack(anchor='w')
        row = self.row(f, (6, 12))
        ttk.Button(row, text='Pobierz + załaduj model', style='Primary.TButton', command=lambda: self.load(True)).pack(side='left')
        ttk.Button(row, text='Załaduj offline', command=lambda: self.load(False)).pack(side='left', padx=8)
        ttk.Separator(f).pack(fill='x', pady=4)
        ttk.Label(f, text='Test bez wysyłania do gry', style='Heading.TLabel').pack(anchor='w', pady=(8, 0))
        row = self.row(f, (6, 8))
        self.test_button = ttk.Button(row, text='Nagraj test', command=self.test_record)
        self.test_button.pack(side='left')
        ttk.Button(row, text='Anuluj (Esc)', command=self.abort).pack(side='left', padx=8)
        ttk.Label(f, text='Podgląd wiadomości — możesz poprawić przed wysłaniem:', style='Muted.TLabel').pack(anchor='w')
        self.text = tk.Text(f, height=3, wrap='word')
        theme.text_widget(self.text)
        self.text.pack(fill='x', pady=4)
        row = self.row(f)
        self.send_button = ttk.Button(row, text='Wyślij podgląd za 5 s', style='Primary.TButton', command=self.preview_send, state='disabled')
        self.send_button.pack(side='left')
        self.hint = tk.StringVar()
        hint = ttk.Label(f, textvariable=self.hint, style='Muted.TLabel', wraplength=520)
        hint.pack(anchor='w', pady=(12, 0))
        f.bind('<Configure>', lambda e: hint.configure(wraplength=max(200, e.width - 40)))
        self.update_hint()

    def build_settings(self, outer):
        canvas = tk.Canvas(outer, bg=theme.BG, highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        f = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=f, anchor='nw')
        canvas.configure(yscrollcommand=scroll.set)
        f.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', lambda m: canvas.yview_scroll(-m.delta // 120, 'units')))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))
        scroll.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        f.columnconfigure(1, weight=1)
        r = 0
        ttk.Label(f, text='Mikrofon (MME)').grid(row=r, column=0, sticky='w', pady=4, padx=(0, 10))
        self.mic_box = ttk.Combobox(f, state='readonly')
        self.mic_box.grid(row=r, column=1, sticky='ew', pady=4)
        ttk.Button(f, text='Odśwież', command=self.refresh_mics).grid(row=r, column=2, padx=(6, 0))
        self.refresh_mics()
        self.vars = {}
        for key, label, values in CHOICES:
            r += 1
            ttk.Label(f, text=label).grid(row=r, column=0, sticky='w', pady=4, padx=(0, 10))
            var = tk.StringVar(value=str(getattr(self.config, key)))
            self.vars[key] = var
            ttk.Combobox(f, textvariable=var, values=values, state='readonly').grid(row=r, column=1, sticky='ew', pady=4)
        r += 1
        ttk.Label(f, text='F13–F20 zmapujesz w SimHub; nie kolidują z iRacing', style='Muted.TLabel').grid(row=r, column=1, columnspan=2, sticky='w')
        r += 1
        ttk.Label(f, text='Kierownica').grid(row=r, column=0, sticky='w', pady=4, padx=(0, 10))
        self.devices = ttk.Combobox(f, state='readonly')
        self.devices.grid(row=r, column=1, sticky='ew', pady=4)
        ttk.Button(f, text='Przypisz', command=self.bind_wheel).grid(row=r, column=2, padx=(6, 0))
        r += 1
        self.wheel_label = tk.StringVar()
        ttk.Label(f, textvariable=self.wheel_label, style='Muted.TLabel').grid(row=r, column=1, columnspan=2, sticky='w')
        r += 1
        ttk.Label(f, text='Słownik').grid(row=r, column=0, sticky='w', pady=(10, 4), padx=(0, 10))
        self.vocabulary = tk.StringVar(value=self.config.vocabulary)
        ttk.Entry(f, textvariable=self.vocabulary).grid(row=r, column=1, columnspan=2, sticky='ew', pady=(10, 4))
        r += 1
        ttk.Label(f, text='Tory, zakręty, nicki — po przecinku, np. Eau Rouge, Raidillon, Kowalski', style='Muted.TLabel').grid(row=r, column=1, columnspan=2, sticky='w')
        r += 1
        grid = ttk.Frame(f)
        grid.grid(row=r, column=0, columnspan=3, sticky='ew', pady=(12, 4))
        self.numbers = {}
        for i, (key, label, scale, low, high) in enumerate(NUMBERS):
            grid.columnconfigure(i % 3, weight=1)
            ttk.Label(grid, text=label, style='Muted.TLabel').grid(row=i // 3 * 2, column=i % 3, sticky='w', padx=(0, 8))
            value = getattr(self.config, key) * scale
            var = tk.StringVar(value=f'{value:g}')
            self.numbers[key] = var
            ttk.Entry(grid, textvariable=var, width=12).grid(row=i // 3 * 2 + 1, column=i % 3, sticky='ew', padx=(0, 8), pady=(2, 8))
        r += 1
        checks = ttk.Frame(f)
        checks.grid(row=r, column=0, columnspan=3, sticky='w', pady=4)
        self.auto = tk.BooleanVar(value=self.config.auto_send)
        self.beeps = tk.BooleanVar(value=self.config.beeps)
        self.autostart = tk.BooleanVar(value=autostart.enabled())
        self.sdk_names = tk.BooleanVar(value=self.config.sdk_names)
        for text, var in [('Automatyczne wysyłanie do czatu (włącz po testach)', self.auto), ('Sygnały dźwiękowe', self.beeps),
                          ('Dodaj do słownika tor i kierowców z bieżącej sesji iRacing', self.sdk_names),
                          ('Uruchamiaj razem z Windows', self.autostart)]:
            ttk.Checkbutton(checks, text=text, variable=var).pack(anchor='w')
        r += 1
        ttk.Button(f, text='Zapisz ustawienia', style='Primary.TButton', command=self.save).grid(row=r, column=0, columnspan=3, sticky='w', pady=(10, 4))

    def build_history(self, f):
        ttk.Label(f, text='Ostatnie 10 wyników (tylko w pamięci, znikają po zamknięciu)', style='Muted.TLabel').pack(anchor='w', pady=(0, 6))
        self.log = self.scrolled_text(f)

    def build_diagnostics(self, f):
        row = self.row(f, (0, 6))
        ttk.Button(row, text='Odśwież diagnostykę', command=self.refresh_diagnostics).pack(side='left')
        self.live_buttons = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text='Podgląd przycisków na żywo', variable=self.live_buttons).pack(side='left', padx=12)
        self.buttons_text = tk.StringVar(value='Włącz podgląd i naciśnij dowolny przycisk kontrolera.')
        live = ttk.Label(f, textvariable=self.buttons_text, style='Muted.TLabel', justify='left')
        live.pack(anchor='w', fill='x', pady=(0, 6))
        f.bind('<Configure>', lambda e: live.configure(wraplength=max(200, e.width - 40)), add='+')
        self.diag = self.scrolled_text(f)

    def scrolled_text(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True)
        text = tk.Text(frame, wrap='word', state='disabled')
        theme.text_widget(text)
        scroll = ttk.Scrollbar(frame, orient='vertical', command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        text.pack(side='left', fill='both', expand=True)
        return text

    # ---------- state ----------
    def set_state(self, kind, detail=''):
        label, color = theme.STATES[kind]
        self.state, self.state_since = kind, time.monotonic()
        self.state_text.set(label)
        self.dot.itemconfigure(self.dot_id, fill=color)
        self.detail.set(detail)

    def show_warning(self, text):
        self.warning_text.set('⚠ ' + text if text else '')
        if text:
            self.warning_label.pack(anchor='w', pady=(8, 0))
        else:
            self.warning_label.pack_forget()

    def ready_state(self, detail=''):
        if self.engine.model is None:
            self.set_state('idle', detail or 'Załaduj model na zakładce Start')
        else:
            self.set_state('ready', detail or 'Przytrzymaj przycisk, aby nagrać')

    def update_hint(self):
        names = {j['guid']: j['name'] for j in getattr(self, 'joystick_info', [])}
        assigned = self.config.joystick and self.config.button >= 0
        wheel = (f'{names.get(self.config.joystick, "kierownica (odłączona)")}, przycisk {self.config.button + 1}'
                 if assigned else 'brak przycisku kierownicy')
        mode = 'przytrzymaj (PTT)' if self.config.mode == 'ptt' else 'naciśnij, aby zacząć i skończyć'
        self.hint.set(f'Nagrywanie: {wheel} lub {self.config.hotkey.upper()} — {mode}. Esc anuluje. '
                      f'Automatyczne wysyłanie: {"WŁĄCZONE" if self.config.auto_send else "wyłączone (tylko podgląd)"}.')
        self.model_info.set(f'Model {self.config.model} · {self.config.engine} · {self.config.device}'
                            + (f' → załadowany na {self.engine.actual_device.upper()}' if self.engine.model else ' — niezaładowany'))
        if hasattr(self, 'wheel_label'):
            self.wheel_label.set(f'Przypisano: {wheel}' if assigned else 'Nie przypisano — wybierz urządzenie i kliknij „Przypisz”')

    # ---------- actions ----------
    def worker(self, job):
        def run():
            try:
                job()
            except Cancelled as exc:
                self.events.put(('error', str(exc)))
            except Exception as exc:
                log.exception('Worker failed')
                self.events.put(('error', f'{type(exc).__name__}: {exc}'))
            finally:
                self.events.put(('idle', None))
        threading.Thread(target=run, daemon=True).start()

    def refresh_mics(self):
        self.mics = microphones()
        names = [m.name for m in self.mics]
        self.mic_box['values'] = ['Domyślny systemowy'] + [m.label for m in self.mics]
        self.mic_box.current(names.index(self.config.microphone) + 1 if self.config.microphone in names else 0)

    def save(self):
        if self.busy or self.recording:
            # Keep the current state visible (e.g. "Pobieranie modelu…") instead of masking it with an error.
            self.set_state(self.state, 'Poczekaj — trwa ' + ('nagrywanie' if self.recording else 'poprzednia operacja'))
            return False
        new = replace(self.config)
        try:
            for key, var in self.vars.items():
                setattr(new, key, var.get())
            for key, label, scale, low, high in NUMBERS:
                value = float(self.numbers[key].get().replace(',', '.')) / scale
                if not low <= value <= high:
                    raise ValueError(f'{label}: dozwolone {low * scale:g}–{high * scale:g}')
                setattr(new, key, type(getattr(new, key))(value))
        except ValueError as exc:
            self.set_state('error', f'Nieprawidłowe ustawienie — {exc}')
            return False
        choice = self.mic_box.current()
        new.microphone = self.mics[choice - 1].name if choice > 0 else ''
        new.microphone_api = self.mics[choice - 1].hostapi if choice > 0 else 'MME'
        new.auto_send, new.beeps, new.sdk_names = self.auto.get(), self.beeps.get(), self.sdk_names.get()
        new.vocabulary = ', '.join(n.strip() for n in self.vocabulary.get().split(',') if n.strip())
        try:
            if self.autostart.get() != autostart.enabled():
                autostart.set_enabled(self.autostart.get())
        except OSError as exc:
            self.show_warning(f'Nie udało się zmienić autostartu: {exc}')
        changed = (new.model, new.device, new.engine) != (self.config.model, self.config.device, self.config.engine)
        self.config = new
        self.config.save()
        self.io.config = self.sender.config = new
        if changed:
            self.engine = Engine(new)
            self.show_warning('')
        self.update_hint()
        self.ready_state('Zapisano. Załaduj model ponownie.' if changed else 'Zapisano ustawienia')
        return True

    def load(self, download):
        if self.busy or self.recording or not self.save():
            return
        self.start_load(download)

    def autoload(self):
        """Load the already downloaded model at startup; a missing model only shows the usual hint."""
        if not (self.busy or self.recording or self.engine.model):
            self.start_load(False)

    def start_load(self, download):
        self.busy = True
        self.set_state('loading', 'Pobieranie modelu…' if download else 'Ładowanie z dysku…')
        def job():
            self.engine.load(download)
            self.events.put(('loaded', None))
        self.worker(job)

    def beep(self, freq):
        if self.config.beeps:
            import winsound
            threading.Thread(target=lambda: winsound.Beep(freq, 70), daemon=True).start()

    def start(self, test=False):
        if self.busy or self.recording:
            return
        if self.engine.model is None:
            self.set_state('idle', 'Najpierw załaduj model na zakładce Start')
            return
        self.cancel.clear()
        self.test_only = test
        self.pending = None
        self.send_button.configure(state='disabled')
        try:
            self.recorder.start(self.config)
        except Exception as exc:
            self.set_state('error', str(exc))
            return
        self.recording = True
        self.record_started = time.perf_counter()
        self.test_button.configure(text='Zakończ test' if test else 'Nagraj test')
        self.set_state('recording', 'Puść przycisk, aby zakończyć · Esc anuluje' if not test else 'Kliknij „Zakończ test”, aby przetworzyć')
        self.beep(900)

    def stop(self):
        if not self.recording:
            return
        self.recording = False
        self.test_button.configure(text='Nagraj test')
        audio = self.recorder.stop()
        duration = time.perf_counter() - self.record_started
        self.beep(600)
        if self.cancel.is_set():
            return
        if not usable(audio, self.config.silence):
            self.ready_state('Odrzucono: cisza lub za krótkie nagranie')
            return
        self.busy = True
        self.set_state('recognizing', f'Model {self.config.model} na {self.engine.actual_device.upper()}')
        test_only = self.test_only
        names = [n for n in self.config.vocabulary.split(',') if n.strip()]
        def job():
            if self.config.sdk_names:
                names.extend(self.io.sdk.session_names())
            start = time.perf_counter()
            source, output, times = self.engine.process(audio, names)
            if self.cancel.is_set():
                return
            if not output:
                self.events.put(('ready', 'Nie rozpoznano mowy — nic nie wysłano'))
                return
            identity = uuid.uuid4().hex
            times['recording_s'] = duration
            times['release_to_result_s'] = time.perf_counter() - start
            self.events.put(('result', (source, output, times)))
            if self.config.auto_send and not test_only:
                self.events.put(('sending', 'Nie przełączaj okna do czasu wysłania'))
                times['input_s'] = self.sender.send(identity, output, self.cancel)
                self.beep(1200)
                self.events.put(('sent', 'Sprawdź w grze, czy wiadomość dotarła'))
            else:
                self.events.put(('pending', (identity, output)))
        self.worker(job)

    def abort(self):
        self.cancel.set()
        self.pending = None
        self.send_button.configure(state='disabled')
        if self.recording:
            self.recording = False
            self.test_button.configure(text='Nagraj test')
            self.recorder.stop()
        self.ready_state('Anulowano')

    def test_record(self):
        if self.recording:
            self.stop()
        else:
            self.start(True)

    def preview_send(self):
        if not self.pending or self.busy:
            return
        identity, _ = self.pending
        text = self.text.get('1.0', 'end').strip()
        self.cancel.clear()
        self.busy = True
        self.send_button.configure(state='disabled')
        self.set_state('sending', 'Przełącz się do iRacing — wysyłanie za 5 s')
        def job():
            if self.cancel.wait(5):
                return
            self.sender.send(identity, text, self.cancel)
            self.beep(1200)
            self.events.put(('sent', 'Sprawdź w grze, czy wiadomość dotarła'))
        self.worker(job)

    def refresh_diagnostics(self):
        from .diagnostics import report
        self.diag.configure(state='normal')
        self.diag.delete('1.0', 'end')
        self.diag.insert('1.0', report(list(self.joysticks.values()), self.engine))
        self.diag.configure(state='disabled')

    # ---------- inputs ----------
    def init_inputs(self):
        import pygame
        pygame.display.init()
        pygame.joystick.init()
        self.pygame = pygame
        from pynput import keyboard
        self.keys_down = set()
        def key_event(key, down):
            name = getattr(key, 'name', None)
            if down and name not in self.keys_down:
                self.keys_down.add(name)
                self.events.put(('key', (name, True)))
            elif not down and name in self.keys_down:
                self.keys_down.discard(name)
                self.events.put(('key', (name, False)))
        self.listener = keyboard.Listener(on_press=lambda k: key_event(k, True), on_release=lambda k: key_event(k, False))
        self.listener.start()

    def refresh_wheels(self):
        pg = self.pygame
        for i in range(pg.joystick.get_count()):
            joy = pg.joystick.Joystick(i)
            self.joysticks[joy.get_instance_id()] = joy
            self.joystick_guids[joy.get_instance_id()] = joy.get_guid()
        self.joystick_info = [{'id': k, 'name': j.get_name(), 'guid': j.get_guid(), 'buttons': j.get_numbuttons()}
                              for k, j in self.joysticks.items() if j.get_numbuttons()]
        self.devices['values'] = [f'{j["name"]} ({j["buttons"]} przycisków)' for j in self.joystick_info]
        guids = [j['guid'] for j in self.joystick_info]
        if self.joystick_info:
            self.devices.current(guids.index(self.config.joystick) if self.config.joystick in guids else 0)
        self.update_hint()

    def bind_wheel(self):
        if self.busy or self.recording or not self.joystick_info:
            return
        self.binding = True
        self.set_state(self.state, 'Naciśnij przycisk na wybranym urządzeniu…')

    def edge(self, source, down):
        if down:
            if source in self.input_sources:
                return
            self.input_sources.add(source)
            if self.config.mode == 'toggle':
                if self.recording:
                    self.stop()
                else:
                    self.start()
            elif len(self.input_sources) == 1:
                self.start()
        else:
            self.input_sources.discard(source)
            if self.config.mode == 'ptt' and not self.input_sources:
                self.stop()

    def device_removed(self, instance_id):
        """Only the assigned controller (by GUID) may interrupt a recording."""
        self.joysticks.pop(instance_id, None)
        guid = self.joystick_guids.pop(instance_id, None)
        if guid and guid == self.config.joystick and 'wheel' in self.input_sources:
            self.input_sources.discard('wheel')
            if self.recording:
                self.abort()
                return True
        return False

    def joystick_button(self, event, down):
        joy = self.joysticks.get(event.instance_id)
        if joy is None:
            return
        guid = self.joystick_guids.get(event.instance_id)
        if self.live_buttons.get():
            self.button_log.appendleft(f'{"▼ wciśnięty" if down else "▲ puszczony"}  {joy.get_name()} · przycisk {event.button + 1} '
                                       f'(indeks {event.button}) · GUID {guid}')
            self.buttons_text.set('\n'.join(self.button_log))
        if self.binding and down:
            selected = self.devices.current()
            if selected < 0 or self.joystick_info[selected]['id'] != event.instance_id:
                return
            self.config.joystick, self.config.button = guid, event.button
            self.config.save()
            self.binding = False
            self.update_hint()
            self.ready_state(f'Przypisano {joy.get_name()}, przycisk {event.button + 1}')
        elif guid == self.config.joystick and event.button == self.config.button:
            self.edge('wheel', down)

    def tick(self):
        try:
            pg = self.pygame
            for e in pg.event.get():
                if e.type == pg.JOYDEVICEADDED:
                    self.refresh_wheels()
                elif e.type == pg.JOYDEVICEREMOVED:
                    if self.device_removed(e.instance_id):
                        self.set_state('error', 'Odłączono przypisaną kierownicę — nagranie anulowane')
                    self.refresh_wheels()
                elif e.type in (pg.JOYBUTTONDOWN, pg.JOYBUTTONUP):
                    self.joystick_button(e, e.type == pg.JOYBUTTONDOWN)
            while not self.events.empty():
                event, value = self.events.get_nowait()
                if event == 'error':
                    self.set_state('error', value)
                elif event in ('sending', 'sent'):
                    self.set_state(event, value)
                elif event == 'ready':
                    self.ready_state(value)
                elif event == 'idle':
                    self.busy = False
                    if self.state in ('loading', 'recognizing'):
                        self.ready_state()
                elif event == 'loaded':
                    self.update_hint()
                    self.ready_state(f'Model {self.config.model} na {self.engine.actual_device.upper()}')
                    self.show_warning(self.engine.warning)
                    if self.engine.warning:
                        messagebox.showwarning('GPU nie działa', self.engine.warning)
                elif event == 'key':
                    name, down = value
                    if name == 'esc' and down:
                        self.abort()
                    elif name == self.config.hotkey:
                        self.edge('keyboard', down)
                elif event == 'pending':
                    self.pending = value
                    self.send_button.configure(state='normal')
                    self.ready_state('Podgląd gotowy — sprawdź tekst i wyślij z zakładki Start')
                elif event == 'result':
                    source, output, times = value
                    self.text.delete('1.0', 'end')
                    self.text.insert('1.0', output)
                    self.last_pl.set('PL: ' + (source if source != output else '— (tryb direct tłumaczy od razu)'))
                    self.last_en.set('EN: ' + output)
                    self.history.appendleft(f'{time.strftime("%H:%M:%S")}  {source}\n→ {output}\n'
                                            + ', '.join(f'{k}: {v:.2f}' for k, v in times.items()))
                    self.log.configure(state='normal')
                    self.log.delete('1.0', 'end')
                    self.log.insert('1.0', '\n\n'.join(self.history))
                    self.log.configure(state='disabled')
                elif event == 'show':
                    self.root.deiconify()
                elif event == 'quit':
                    self.quit()
                    return
            now = time.monotonic()
            if now - self.sdk_checked > 1:
                self.sdk_checked = now
                self.sdk_text.set('● iRacing wykryty' if self.io.sdk_connected() else '○ iRacing niewykryty')
            if self.state == 'sent' and now - self.state_since > 5:
                self.ready_state()
            self.level['value'] = min(100, self.recorder.level * 400) if self.recording else 0
            if self.recording and time.perf_counter() - self.record_started >= self.config.max_seconds:
                self.stop()
        except Exception as exc:
            log.exception('UI tick failed')
            self.set_state('error', str(exc))
        self.root.after(15, self.tick)

    def hide(self):
        if self.tray is None:
            import pystray
            from PIL import Image, ImageDraw
            image = Image.new('RGB', (64, 64), theme.BG)
            ImageDraw.Draw(image).ellipse((12, 12, 52, 52), fill=theme.LEVEL)
            self.tray = pystray.Icon('IVT', image, 'iRacing Voice Translator', pystray.Menu(
                pystray.MenuItem('Pokaż', lambda: self.events.put(('show', None)), default=True),
                pystray.MenuItem('Zakończ', lambda: self.events.put(('quit', None)))))
            self.tray.run_detached()
        self.root.withdraw()

    def quit(self):
        self.abort()
        self.listener.stop()
        self.pygame.quit()
        if self.tray:
            self.tray.stop()
        self.root.destroy()

def setup_logging():
    DATA.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(DATA / 'ivt.log', maxBytes=512_000, backupCount=1, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    logging.basicConfig(level=logging.INFO, handlers=[handler])

def main():
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    mutex = kernel.CreateMutexW(None, False, 'Local\\iRacingVoiceTranslator.SingleInstance')
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        messagebox.showinfo('iRacing Voice Translator', 'Program jest już uruchomiony — sprawdź zasobnik systemowy.')
        return
    setup_logging()
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # crisp text on scaled displays
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    root.report_callback_exception = lambda typ, value, tb: (log.error('Tk callback', exc_info=(typ, value, tb)),
                                                              messagebox.showerror('Błąd', str(value)))
    try:
        app = App(root)
        root.after(300, app.autoload)
        root.mainloop()
    finally:
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(mutex)

if __name__ == '__main__':
    main()
