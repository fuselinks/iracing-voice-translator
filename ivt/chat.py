"""Guarded sequence; transport is injectable for deterministic tests."""
import threading
import time
import re

class Cancelled(RuntimeError):
    pass

def clean_message(text, limit):
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        raise ValueError('Pusta wiadomość')
    if text[0] in '/#!@$':
        raise ValueError('Rozpoznano prefiks komendy gry — wysyłanie anulowane')
    if len(text) > limit:
        raise ValueError('Wiadomość za długa — skróć wypowiedź')
    return text

class Sender:
    def __init__(self, transport, config):
        self.io, self.config = transport, config
        self.lock = threading.Lock()
        self.attempted = set()

    def send(self, identity, text, cancel):
        text = clean_message(text, self.config.max_chars)
        if not self.lock.acquire(False):
            raise Cancelled('Wysyłanie jest już w toku')
        started = time.perf_counter()
        try:
            if identity in self.attempted:
                raise Cancelled('Ta próba była już wykonana; brak automatycznego ponawiania')
            window = self.io.target()
            def check():
                if cancel.is_set() or not window or self.io.target() != window:
                    raise Cancelled('Anulowano lub iRacing utracił fokus')
            def pause(seconds):
                until = time.monotonic() + seconds
                while time.monotonic() < until:
                    check()
                    time.sleep(0.01)
                check()
            check()
            if not self.io.closed():
                raise Cancelled('Nie potwierdzono zamkniętego czatu / kalibracji')
            self.attempted.add(identity)
            self.io.key('t')
            pause(self.config.open_delay)
            if not self.io.opened():
                raise Cancelled('Nie potwierdzono otwarcia czatu')
            for char in text:
                check()
                self.io.character(char)
            pause(self.config.send_delay)
            if not self.io.opened():
                raise Cancelled('Pole czatu nie jest już potwierdzone')
            check()
            self.io.key('enter')
            return time.perf_counter() - started
        finally:
            self.lock.release()
