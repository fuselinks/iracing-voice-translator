"""No names, paths, audio or transcripts in the output."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import platform
import importlib.metadata
import sounddevice as sd
import ctranslate2
import pygame
print('Python',platform.python_version(),'Windows',platform.release())
for package in ['faster-whisper','ctranslate2','sounddevice','pygame-ce','pynput','Pillow']:
    print(package,importlib.metadata.version(package))
print('CUDA device count:',ctranslate2.get_cuda_device_count())
print('Input device count:',sum(bool(d['max_input_channels']) for d in sd.query_devices()))
pygame.joystick.init()
print('Joystick count:',pygame.joystick.get_count())
pygame.quit()
