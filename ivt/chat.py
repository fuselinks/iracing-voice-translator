"""Guarded chat sequence; transport is injectable for deterministic tests."""
import logging
import threading
import time
from .keyboard import normalize_ascii, split_message

log = logging.getLogger(__name__)

class Cancelled(RuntimeError):
    pass

def clean_message(text, limit, max_parts=3):
    """ASCII text split into at most `max_parts` chat messages, none starting with a game command prefix."""
    text = normalize_ascii(text)
    if not text:
        raise ValueError('Pusta wiadomość')
    parts = split_message(text, limit, max_parts)
    if any(part[0] in '/#!@$' for part in parts):
        raise ValueError('Rozpoznano prefiks komendy gry — wysyłanie anulowane')
    return parts

class Sender:
    """Focus + SDK check → Cancel → BeginChat → pause → text → pause → focus check → Enter.

    Every interruption after the first SDK command sends Cancel, so no half-typed field stays open.
    """
    def __init__(self, transport, config):
        self.io, self.config = transport, config
        self.lock = threading.Lock()
        self.attempted = set()

    def send(self, identity, text, cancel):
        parts = clean_message(text, self.config.max_chars)
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
            # Every character is mapped before the chat opens, so a bad character cannot leave it half-typed.
            plans = [self.io.prepare(part, window) for part in parts]
            self.attempted.add(identity)
            try:
                for number, keys in enumerate(plans):
                    if number:
                        pause(self.config.open_delay)
                    self.io.cancel_chat()
                    pause(0.05)
                    self.io.begin_chat()
                    pause(self.config.open_delay)
                    for key in keys:
                        check()
                        self.io.character(key)
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
