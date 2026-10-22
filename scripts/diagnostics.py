"""Prints device names (microphones, controllers) — check the output before sharing it."""
import os
import sys
from pathlib import Path
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import importlib.metadata
import pygame
from ivt.diagnostics import report

for package in ['faster-whisper','ctranslate2','nvidia-cublas-cu12','nvidia-cudnn-cu12','sounddevice','pygame-ce','pynput']:
    try:print(package,importlib.metadata.version(package))
    except importlib.metadata.PackageNotFoundError:print(package,'not installed')
pygame.joystick.init()
joysticks=[pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
print(report(joysticks))
pygame.quit()
