"""Hardware/software report shown in the Diagnostics tab. Contains device names — check before sharing."""
import platform
import sounddevice as sd
from . import cuda
from .audio import microphones, RATE
from .config import DATA
from .irsdk import IRacingSDK

def microphone_lines():
    lines = []
    for mic in microphones():
        try:
            sd.check_input_settings(device=mic.index, samplerate=RATE, channels=1, dtype='float32')
            rate = '16 kHz OK'
        except Exception:
            rate = f'16 kHz odrzucone → nagrywanie {int(mic.rate)} Hz + resampling'
        lines.append(f'  • {mic.label} [{mic.hostapi}, natywnie {int(mic.rate)} Hz, {rate}]')
    return lines or ['  (brak wejść audio)']

def controller_lines(joysticks):
    lines = [f'  • {j.get_name()} | GUID {j.get_guid()} | przycisków: {j.get_numbuttons()}' for j in joysticks]
    return lines or ['  (brak kontrolerów)']

def report(joysticks=(), engine=None):
    sections = [f'System: Windows {platform.release()}, Python {platform.python_version()}', '',
                'Mikrofony (MME):'] + microphone_lines()
    sections += ['', 'Kontrolery (SDL):'] + controller_lines(joysticks)
    sections += ['', 'CUDA:'] + ['  ' + line for line in cuda.describe().splitlines()]
    if engine is not None and engine.model is not None:
        sections.append(f'  Model w użyciu: {engine.config.model} na {engine.actual_device}')
        if engine.warning:
            sections.append('  UWAGA: ' + engine.warning)
    connected = IRacingSDK().connected()
    sections += ['', 'iRacing SDK: ' + ('połączone (symulator działa)' if connected else 'niepołączone (symulator nie działa lub brak sesji)')]
    sections += ['', f'Ustawienia i log: {DATA}']
    return '\n'.join(sections)
