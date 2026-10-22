"""Guarded chat sequence; transport is injectable for deterministic tests."""
import logging
import threading
import time
import re

log = logging.getLogger(__name__)

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
    """Focus + SDK check → Cancel → BeginChat → pause → text → pause → focus check → Enter.

    Every interruption after the first SDK command sends Cancel, so no half-typed field stays open.
    """
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
                if cancel.is_set():
                    raise Cancelled('Anulowano')
                if not window or self.io.target() != window:
                    raise Cancelled('iRacing nie jest aktywnym oknem')
            def pause(seconds):
                until = time.monotonic() + seconds
                while time.monotonic() < until:
                    check()
                    time.sleep(min(0.01, seconds))
                check()
            check()
            if not self.io.sdk_connected():
                raise Cancelled('iRacing SDK nie jest połączone — uruchom sesję w symulatorze')
            self.attempted.add(identity)
            try:
                self.io.cancel_chat()
                pause(0.05)
                self.io.begin_chat()
                pause(self.config.open_delay)
                for char in text:
                    check()
                    self.io.character(char)
                    pause(self.config.char_delay)
                pause(self.config.send_delay)
                check()
                self.io.enter()
            except BaseException:
                try:
                    self.io.cancel_chat()
                except Exception:
                    log.exception('Chat cancel after interruption failed')
                raise
            return time.perf_counter() - started
        finally:
            self.lock.release()
