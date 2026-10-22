import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict, fields

DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local/share'))) / 'iRacingVoiceTranslator'

@dataclass
class Config:
    model: str = 'medium'
    device: str = 'auto'
    engine: str = 'direct'
    microphone: str = ''
    joystick: str = ''
    button: int = -1
    hotkey: str = 'f9'
    mode: str = 'ptt'
    gain: float = 1.0
    silence: float = 0.008
    max_seconds: int = 20
    max_chars: int = 180
    open_delay: float = 0.35
    send_delay: float = 0.15
    auto_send: bool = False
    beeps: bool = True
    roi: str = ''
    visual_threshold: float = 8.0

    @classmethod
    def load(cls, folder=DATA):
        path = folder / 'settings.json'
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding='utf-8'))
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in fields(cls)}})

    def save(self, folder=DATA):
        folder.mkdir(parents=True, exist_ok=True)
        temp = folder / 'settings.tmp'
        temp.write_text(json.dumps(asdict(self), indent=2), encoding='utf-8')
        temp.replace(folder / 'settings.json')
