# app/concurrency/read_write_lock.py
import threading
from contextlib import contextmanager

class ReadWriteLock:
    """
    Simple readers-writer lock with writer preference.
    - Multiple readers can hold the lock concurrently.
    - Writers have exclusive access and are favored to avoid starvation.
    """
    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._readers = 0
        self._writer = False
        self._waiting_writers = 0

    @contextmanager
    def read_lock(self):
        with self._cond:
            # Block new readers if a writer holds the lock OR is waiting.
            while self._writer or self._waiting_writers > 0:
                self._cond.wait()
            self._readers += 1
        try:
            yield
        finally:
            with self._cond:
                self._readers -= 1
                if self._readers == 0:
                    self._cond.notify_all()

    @contextmanager
    def write_lock(self):
        with self._cond:
            self._waiting_writers += 1
            while self._writer or self._readers > 0:
                self._cond.wait()
            self._waiting_writers -= 1
            self._writer = True
        try:
            yield
        finally:
            with self._cond:
                self._writer = False
                self._cond.notify_all()
