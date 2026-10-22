import json
import logging
import os
from pathlib import Path
from dataclasses import dataclass, asdict, fields

DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local/share'))) / 'iRacingVoiceTranslator'
HOTKEYS = ['f8', 'f9', 'f10', 'f11', 'f12'] + [f'f{n}' for n in range(13, 21)]
log = logging.getLogger(__name__)

@dataclass
class Config:
    model: str = 'medium'
    device: str = 'auto'
    engine: str = 'direct'
    microphone: str = ''
    microphone_api: str = 'MME'
    joystick: str = ''
    button: int = -1
    hotkey: str = 'f13'
    mode: str = 'ptt'
    gain: float = 1.0
    silence: float = 0.008
    max_seconds: int = 20
    max_chars: int = 180
    open_delay: float = 0.35
    send_delay: float = 0.15
    char_delay: float = 0.01
    auto_send: bool = False
    beeps: bool = True
    roi: str = ''
    visual_threshold: float = 8.0

    @classmethod
    def load(cls, folder=DATA):
        """Never fails: a missing or damaged file gives defaults (damaged one is kept as settings.json.bad)."""
        path = folder / 'settings.json'
        cls.load_problem = None
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                raise ValueError('not an object')
        except (OSError, ValueError) as exc:
            log.warning('Damaged settings.json (%s), using defaults', exc)
            cls.load_problem = 'Uszkodzony settings.json — wczytano ustawienia domyślne (kopia: settings.json.bad)'
            try:
                path.replace(folder / 'settings.json.bad')
            except OSError:
                pass
            return cls()
        config = cls()
        for field in fields(cls):
            if field.name not in data:
                continue
            default = getattr(config, field.name)
            value = data[field.name]
            try:
                if isinstance(default, bool):
                    if not isinstance(value, bool):
                        raise TypeError
                elif isinstance(default, (int, float)):
                    if isinstance(value, bool):
                        raise TypeError
                    value = type(default)(value)
                elif not isinstance(value, str):
                    raise TypeError
            except (TypeError, ValueError):
                log.warning('Ignoring invalid setting %s', field.name)
                cls.load_problem = 'Część ustawień była nieprawidłowa — przywrócono wartości domyślne'
                continue
            setattr(config, field.name, value)
        return config

    def save(self, folder=DATA):
        folder.mkdir(parents=True, exist_ok=True)
        temp = folder / 'settings.tmp'
        temp.write_text(json.dumps(asdict(self), indent=2), encoding='utf-8')
        temp.replace(folder / 'settings.json')
