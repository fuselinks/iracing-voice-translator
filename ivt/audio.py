import threading
import numpy as np
import sounddevice as sd

RATE = 16000

class Recorder:
    def __init__(self):
        self.stream = None
        self.frames = []
        self.level = 0.0
        self.error = None
        self.lock = threading.Lock()

    def start(self, config):
        self.frames, self.error, self.level = [], None, 0.0
        self.maximum = config.max_seconds * RATE
        self.count = 0
        device = None
        if config.microphone:
            choices = [i for i,d in enumerate(sd.query_devices()) if d['name'] == config.microphone and d['max_input_channels']]
            if len(choices) != 1:
                raise RuntimeError('Mikrofon zniknął lub nazwa jest niejednoznaczna — wybierz ponownie')
            device = choices[0]
        def callback(data, frames, timing, status):
            if status:
                self.error = str(status)
            block = np.clip(data[:, 0] * config.gain, -1, 1).copy()
            self.level = float(np.sqrt(np.mean(block ** 2)))
            with self.lock:
                remaining = self.maximum - self.count
                if remaining > 0:
                    self.frames.append(block[:remaining])
                    self.count += len(block[:remaining])
        self.stream = sd.InputStream(samplerate=RATE, channels=1, dtype='float32', device=device, callback=callback)
        self.stream.start()

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        with self.lock:
            result = np.concatenate(self.frames) if self.frames else np.empty(0, dtype=np.float32)
            self.frames = []
        if self.error:
            raise RuntimeError('Przerwane audio: ' + self.error)
        return result

def usable(audio, threshold):
    if len(audio) < RATE * 0.3:
        return False
    blocks = [audio[i:i+320] for i in range(0, len(audio), 320)]
    return sum(float(np.sqrt(np.mean(b*b))) >= threshold for b in blocks) >= 10
