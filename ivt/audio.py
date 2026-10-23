import logging
import threading
from dataclasses import dataclass
import numpy as np
import sounddevice as sd

RATE = 16000
HOST_API = 'MME'  # accepts 16 kHz mono on typical Windows drivers; one entry per physical input
log = logging.getLogger(__name__)

@dataclass(frozen=True)
class Microphone:
    index: int
    name: str      # raw PortAudio name, stored in settings (MME truncates to 31 characters)
    hostapi: str
    label: str     # display name, completed from DirectSound when MME truncated it
    rate: float    # default sample rate of the device

def microphones(hostapi=HOST_API):
    """Input devices of a single host API, so each physical microphone is listed once."""
    apis = sd.query_hostapis()
    devices = [(i, d, apis[d['hostapi']]['name']) for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0]
    full_names = [d['name'] for _, d, api in devices if api == 'Windows DirectSound']
    result = []
    for i, d, api in devices:
        # Skip the (localized) "Microsoft Sound Mapper - Input" pseudo-device.
        if api != hostapi or ('Microsoft' in d['name'] and d['name'].endswith(' - Input')):
            continue
        label = d['name'].strip()
        longer = [n for n in full_names if n.startswith(d['name']) and n != d['name']]
        if len(longer) == 1:
            label = longer[0]
        result.append(Microphone(i, d['name'], api, label, d['default_samplerate']))
    return result

def find_microphone(name, hostapi=HOST_API):
    """Exact match on name + host API; None means the system default input."""
    if not name:
        return None
    choices = [m for m in microphones(hostapi) if m.name == name]
    if not choices:
        raise RuntimeError(f'Mikrofon „{name.strip()}” ({hostapi}) nie jest podłączony — wybierz go ponownie w Ustawieniach')
    if len(choices) > 1:
        log.warning('%d devices named %r in %s, using the first', len(choices), name, hostapi)
    return choices[0]

def open_rate(device):
    """16 kHz when the driver accepts it, otherwise the device's native rate (resampled later)."""
    try:
        sd.check_input_settings(device=device, samplerate=RATE, channels=1, dtype='float32')
        return RATE
    except Exception as exc:
        native = int(sd.query_devices(device if device is not None else sd.default.device[0])['default_samplerate'])
        log.info('16 kHz rejected (%s), recording at %d Hz and resampling', exc, native)
        return native

def resample(audio, source_rate, target_rate=RATE):
    if source_rate == target_rate or len(audio) == 0:
        return audio.astype(np.float32, copy=False)
    if source_rate > target_rate:
        # Windowed-sinc low-pass below the target Nyquist frequency before decimating.
        cutoff = 0.45 * target_rate / source_rate
        taps = np.arange(-64, 65)
        kernel = 2 * cutoff * np.sinc(2 * cutoff * taps) * np.hamming(len(taps))
        audio = np.convolve(audio, kernel / kernel.sum(), mode='same')
    length = int(round(len(audio) * target_rate / source_rate))
    positions = np.arange(length) * (source_rate / target_rate)
    return np.interp(positions, np.arange(len(audio)), audio).astype(np.float32)

class Recorder:
    def __init__(self):
        self.stream = None
        self.frames = []
        self.level = 0.0
        self.problems = 0
        self.rate = RATE
        self.lock = threading.Lock()

    def start(self, config):
        self.frames, self.level, self.problems, self.count = [], 0.0, 0, 0
        mic = find_microphone(config.microphone, config.microphone_api)
        device = mic.index if mic else None
        self.rate = open_rate(device)
        self.maximum = int(config.max_seconds * self.rate)
        def callback(data, frames, timing, status):
            if status:
                # Overflow drops a few milliseconds of audio; the rest of the utterance stays usable.
                self.problems += 1
                log.warning('Audio callback status: %s', status)
            block = np.clip(data[:, 0] * config.gain, -1, 1).copy()
            self.level = float(np.sqrt(np.mean(block ** 2)))
            with self.lock:
                remaining = self.maximum - self.count
                if remaining > 0:
                    self.frames.append(block[:remaining])
                    self.count += len(block[:remaining])
        self.stream = sd.InputStream(samplerate=self.rate, channels=1, dtype='float32', device=device, callback=callback)
        self.stream.start()

    def stop(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            finally:
                self.stream = None
        self.level = 0.0
        with self.lock:
            result = np.concatenate(self.frames) if self.frames else np.empty(0, dtype=np.float32)
            self.frames = []
        if self.problems:
            log.warning('Recording finished with %d callback status flags', self.problems)
        return resample(result, self.rate)

def usable(audio, threshold):
    if len(audio) < RATE * 0.3:
        return False
    blocks = [audio[i:i+320] for i in range(0, len(audio), 320)]
    return sum(float(np.sqrt(np.mean(b*b))) >= threshold for b in blocks) >= 10
