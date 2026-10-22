import os
os.environ['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS'] = '1'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import queue
import threading
import time
import uuid
import tkinter as tk
from tkinter import ttk, messagebox
from collections import deque
from .config import Config
from .audio import Recorder, usable, RATE, microphones
from .engine import Engine
from .chat import Sender
from .windows import WindowsChat

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
        self.tray = None
        root.title('iRacing Voice Translator')
        root.geometry('790x850')
        root.configure(bg='#151923')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#151923', foreground='#edf1fa', fieldbackground='#242c3a')
        style.configure('TButton', background='#30405a', padding=6)
        self.frame = ttk.Frame(root, padding=16)
        self.frame.pack(fill='both', expand=True)
        ttk.Label(self.frame, text='iRacing Voice Translator', font=('Segoe UI', 19, 'bold')).pack(anchor='w')
        self.status = tk.StringVar(value='Pobierz lub załaduj model, następnie wykonaj testy')
        ttk.Label(self.frame, textvariable=self.status, wraplength=740).pack(anchor='w', pady=8)
        self.vars = {}
        self.mics = microphones(self.config.microphone_api)
        for key, label, choices in [ ('model','Model', ['small','medium','large-v3']),
            ('device','Obliczenia', ['auto','cuda','cpu']), ('engine','Silnik', ['direct','two-stage','polish']),
            ('mode','Przycisk', ['ptt','toggle']), ('hotkey','Skrót / SimHub', ['f8','f9','f10','f11','f12'])]:
            row = ttk.Frame(self.frame); row.pack(fill='x', pady=2)
            ttk.Label(row, text=label, width=23).pack(side='left')
            var = tk.StringVar(value=str(getattr(self.config,key))); self.vars[key] = var
            ttk.Combobox(row, textvariable=var, values=choices, state='readonly').pack(side='left', fill='x', expand=True)
        row = ttk.Frame(self.frame); row.pack(fill='x', pady=2)
        ttk.Label(row, text='Mikrofon (MME)', width=23).pack(side='left')
        self.mic_box = ttk.Combobox(row, values=['Domyślny systemowy']+[m.label for m in self.mics], state='readonly')
        self.mic_box.pack(side='left', fill='x', expand=True)
        names = [m.name for m in self.mics]
        self.mic_box.current(names.index(self.config.microphone)+1 if self.config.microphone in names else 0)
        self.devices = ttk.Combobox(self.frame, state='readonly')
        self.devices.pack(fill='x', pady=5)
        self.wheel_label = tk.StringVar(value=f'Przycisk: {self.config.joystick} / {self.config.button}')
        ttk.Label(self.frame, textvariable=self.wheel_label).pack(anchor='w')
        row = ttk.Frame(self.frame); row.pack(fill='x')
        ttk.Button(row, text='Przypisz następny przycisk', command=self.bind_wheel).pack(side='left')
        ttk.Button(row, text='Odśwież urządzenia', command=self.refresh_wheels).pack(side='left')
        self.level = ttk.Progressbar(self.frame, maximum=100); self.level.pack(fill='x', pady=6)
        settings = ttk.Frame(self.frame); settings.pack(fill='x')
        for i,(key,label) in enumerate([('gain','Wzmocnienie'),('silence','Próg ciszy'),('open_delay','Pauza po T [s]'),('send_delay','Pauza przed Enter [s]'),('max_chars','Limit znaków')]):
            ttk.Label(settings,text=label).grid(row=i//3*2,column=i%3,padx=5,sticky='w')
            var=tk.StringVar(value=str(getattr(self.config,key))); self.vars[key]=var
            ttk.Entry(settings,textvariable=var,width=20).grid(row=i//3*2+1,column=i%3,padx=5,sticky='w')
        self.auto = tk.BooleanVar(value=self.config.auto_send)
        self.beeps = tk.BooleanVar(value=self.config.beeps)
        ttk.Checkbutton(self.frame,text='Automatyczne wysyłanie (włącz po testach)',variable=self.auto).pack(anchor='w')
        ttk.Checkbutton(self.frame,text='Sygnały dźwiękowe',variable=self.beeps).pack(anchor='w')
        self.sdk_state=tk.StringVar(value='iRacing: sprawdzanie…')
        ttk.Label(self.frame,textvariable=self.sdk_state).pack(anchor='w')
        row=ttk.Frame(self.frame); row.pack(fill='x',pady=5)
        for text, command in [('Zapisz ustawienia',self.save),('Pobierz + załaduj model',lambda:self.load(True)),('Załaduj offline',lambda:self.load(False))]:
            ttk.Button(row,text=text,command=command).pack(side='left')
        row=ttk.Frame(self.frame); row.pack(fill='x',pady=5)
        ttk.Button(row,text='Test mikrofonu i tłumaczenia',command=self.test_record).pack(side='left')
        ttk.Button(row,text='Anuluj (Esc)',command=self.abort).pack(side='left')
        ttk.Button(row,text='Wyślij podgląd za 5 s',command=self.preview_send).pack(side='left')
        self.text=tk.Text(self.frame,height=3,bg='#242c3a',fg='white',insertbackground='white',wrap='word')
        self.text.pack(fill='x')
        self.log=tk.Text(self.frame,height=7,bg='#10141d',fg='#b8c9e6',wrap='word',state='disabled')
        self.log.pack(fill='both',expand=True,pady=5)
        root.protocol('WM_DELETE_WINDOW',self.hide)
        self.init_inputs()
        self.refresh_wheels()
        self.tick()

    def worker(self, job):
        def run():
            try: job()
            except Exception as exc: self.events.put(('error',f'{type(exc).__name__}: {exc}'))
            finally: self.events.put(('idle',None))
        threading.Thread(target=run,daemon=True).start()

    def save(self):
        if self.busy or self.recording:
            raise RuntimeError('Najpierw zakończ operację')
        from dataclasses import replace
        new=replace(self.config)
        for key,var in self.vars.items():
            old=getattr(new,key)
            setattr(new,key,type(old)(var.get()))
        if not (0.1<=new.gain<=10 and 0.0001<=new.silence<=0.5 and 0.05<=new.open_delay<=3 and 0.01<=new.send_delay<=3 and 10<=new.max_chars<=500):
            raise ValueError('Nieprawidłowe zakresy ustawień')
        choice=self.mic_box.current()
        new.microphone=self.mics[choice-1].name if choice>0 else ''
        new.microphone_api=self.mics[choice-1].hostapi if choice>0 else 'MME'
        new.auto_send=self.auto.get(); new.beeps=self.beeps.get()
        changed=(new.model,new.device,new.engine)!=(self.config.model,self.config.device,self.config.engine)
        self.config=new; self.config.save()
        self.io.config=new; self.sender.config=new
        if changed: self.engine=Engine(new)
        self.status.set('Zapisano. Model wymaga załadowania.' if changed else 'Zapisano ustawienia')

    def load(self,download):
        if self.busy or self.recording:return
        self.save(); self.busy=True
        self.status.set('Pobieranie / ładowanie modelu…')
        def job():
            self.engine.load(download)
            self.events.put(('status','Gotowy — '+self.engine.actual_device))
        self.worker(job)

    def beep(self,freq):
        if self.config.beeps:
            import winsound
            threading.Thread(target=lambda:winsound.Beep(freq,70),daemon=True).start()

    def start(self,test=False):
        if self.busy or self.recording:return
        if self.engine.model is None:
            self.status.set('Najpierw załaduj model');return
        self.cancel.clear(); self.test_only=test; self.pending=None
        self.recorder.start(self.config)
        self.recording=True; self.record_started=time.perf_counter()
        self.status.set('Nagrywanie — puść przycisk / Esc anuluje')
        self.beep(900)

    def stop(self):
        if not self.recording:return
        self.recording=False
        audio=self.recorder.stop(); duration=time.perf_counter()-self.record_started
        self.beep(600)
        if self.cancel.is_set():return
        if not usable(audio,self.config.silence):self.status.set('Odrzucono ciszę / zbyt krótki sygnał');return
        self.busy=True; self.status.set('Rozpoznawanie / tłumaczenie…')
        def job():
            start=time.perf_counter()
            source,output,times=self.engine.process(audio)
            self.events.put(('status','Model: '+self.config.model+' / '+self.engine.actual_device))
            if self.cancel.is_set():return
            if not output: self.events.put(('status','Odrzucono brak mowy'));return
            identity=uuid.uuid4().hex
            times['recording_s']=duration
            times['release_to_result_s']=time.perf_counter()-start
            if self.config.auto_send and not self.test_only:
                self.events.put(('status','Wysyłanie…'))
                times['input_s']=self.sender.send(identity,output,self.cancel)
                times['release_to_end_s']=time.perf_counter()-start
                self.beep(1200)
                self.events.put(('status','Zakończono próbę wysyłania (doręczenie niepotwierdzone)'))
            else:self.events.put(('pending',(identity,output)))
            self.events.put(('result',(source,output,times)))
        self.worker(job)

    def abort(self):
        self.cancel.set(); self.pending=None
        if self.recording:
            self.recording=False; self.recorder.stop()
        self.status.set('Anulowano; sprawdź ręcznie czat, jeśli był otwarty')

    def test_record(self):
        if self.recording:self.stop()
        else:self.start(True)

    def preview_send(self):
        if not self.pending or self.busy:return
        identity,_=self.pending; text=self.text.get('1.0','end').strip()
        self.cancel.clear(); self.busy=True
        self.status.set('Przełącz się do iRacing — próba za 5 s')
        def job():
            if self.cancel.wait(5):return
            self.sender.send(identity,text,self.cancel)
            self.beep(1200); self.events.put(('status','Zakończono próbę wysłania'))
        self.worker(job)

    def init_inputs(self):
        import pygame
        pygame.display.init(); pygame.joystick.init()
        self.pygame=pygame; self.joysticks={}
        from pynput import keyboard
        self.keys_down=set()
        def key_event(key,down):
            name=getattr(key,'name',None)
            if down and name not in self.keys_down:
                self.keys_down.add(name); self.events.put(('key',(name,True)))
            elif not down and name in self.keys_down:
                self.keys_down.discard(name); self.events.put(('key',(name,False)))
        self.listener=keyboard.Listener(on_press=lambda k:key_event(k,True),on_release=lambda k:key_event(k,False))
        self.listener.start()

    def refresh_wheels(self):
        pg=self.pygame
        for i in range(pg.joystick.get_count()):
            joy=pg.joystick.Joystick(i); joy.init(); self.joysticks[joy.get_instance_id()]=joy
        labels=[f'{j.get_name()} | {j.get_guid()} | {j.get_numbuttons()} przycisków' for j in self.joysticks.values()]
        self.devices['values']=labels
        if labels:self.devices.current(0)

    def bind_wheel(self):
        if self.busy or self.recording:return
        self.binding=True; self.status.set('Naciśnij przycisk na wybranym urządzeniu')

    def edge(self,source,down):
        if down:
            if source in self.input_sources:return
            self.input_sources.add(source)
            if self.config.mode=='toggle':
                if self.recording:self.stop()
                else:self.start()
            elif len(self.input_sources)==1:self.start()
        else:
            self.input_sources.discard(source)
            if self.config.mode=='ptt' and not self.input_sources:self.stop()

    def tick(self):
        try:
            pg=self.pygame
            for e in pg.event.get():
                if e.type==pg.JOYDEVICEADDED:self.refresh_wheels()
                elif e.type==pg.JOYDEVICEREMOVED:
                    self.joysticks.pop(e.instance_id,None);self.abort();self.input_sources.clear()
                elif e.type in (pg.JOYBUTTONDOWN,pg.JOYBUTTONUP):
                    joy=self.joysticks.get(e.instance_id)
                    if joy is None:continue
                    guid=joy.get_guid(); down=e.type==pg.JOYBUTTONDOWN
                    if self.binding and down:
                        selected=self.devices.current()
                        if selected>=0 and list(self.joysticks.values())[selected].get_instance_id()!=e.instance_id:continue
                        self.config.joystick=guid; self.config.button=e.button;self.config.save();self.binding=False
                        self.wheel_label.set(f'{joy.get_name()} / przycisk {e.button+1} (indeks {e.button})')
                        self.status.set('Przypisano przycisk')
                    elif guid==self.config.joystick and e.button==self.config.button:self.edge('wheel',down)
            while not self.events.empty():
                event,value=self.events.get_nowait()
                if event in ('status','error'):self.status.set(('Błąd: ' if event=='error' else '')+value)
                elif event=='idle':self.busy=False
                elif event=='key':
                    name,down=value
                    if name=='esc' and down:self.abort()
                    elif name==self.config.hotkey:self.edge('keyboard',down)
                elif event=='pending':self.pending=value;self.status.set('Podgląd — wiadomość gotowa do ręcznego wysłania')
                elif event=='result':
                    source,output,times=value
                    self.text.delete('1.0','end');self.text.insert('1.0',output)
                    self.history.append(f'{source}\n→ {output}\n'+', '.join(f'{k}: {v:.2f}' for k,v in times.items()))
                    self.log.configure(state='normal');self.log.delete('1.0','end');self.log.insert('1.0','\n\n'.join(self.history));self.log.configure(state='disabled')
                elif event=='show':self.root.deiconify()
                elif event=='quit':self.quit();return
            now=time.monotonic()
            if now-getattr(self,'sdk_checked',0)>1:
                self.sdk_checked=now
                self.sdk_state.set('iRacing: wykryty (SDK połączone)' if self.io.sdk_connected() else 'iRacing: niewykryty')
            self.level['value']=min(100,self.recorder.level*400)
            if self.recording and time.perf_counter()-self.record_started>=self.config.max_seconds:self.stop()
        except Exception as exc:self.status.set('Błąd: '+str(exc))
        self.root.after(15,self.tick)

    def hide(self):
        if self.tray is None:
            import pystray
            from PIL import Image,ImageDraw
            image=Image.new('RGB',(64,64),'#151923');ImageDraw.Draw(image).ellipse((12,12,52,52),fill='#48bfaa')
            self.tray=pystray.Icon('IVT',image,'iRacing Voice Translator',pystray.Menu(
                pystray.MenuItem('Pokaż',lambda:self.events.put(('show',None)),default=True),
                pystray.MenuItem('Zakończ',lambda:self.events.put(('quit',None)))))
            self.tray.run_detached()
        self.root.withdraw()

    def quit(self):
        self.abort();self.listener.stop();self.pygame.quit()
        if self.tray:self.tray.stop()
        self.root.destroy()

def main():
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
    kernel.CreateMutexW.restype=wintypes.HANDLE
    mutex=kernel.CreateMutexW(None,False,'Local\\iRacingVoiceTranslator.SingleInstance')
    if not mutex:raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error()==183:
        messagebox.showinfo('iRacing Voice Translator','Program jest już uruchomiony — sprawdź zasobnik systemowy.')
        return
    root=tk.Tk()
    root.report_callback_exception=lambda typ,value,tb:messagebox.showerror('Błąd',str(value))
    try:
        App(root);root.mainloop()
    finally:
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        kernel.CloseHandle(mutex)

if __name__=='__main__':main()
