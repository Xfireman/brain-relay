"""Bounded, in-memory jobs. Restart discards jobs, never saved capsules."""
import time
from concurrent.futures import ThreadPoolExecutor
from threading import RLock, BoundedSemaphore
from uuid import uuid4


class QueueFull(RuntimeError):
    pass


class Jobs:
    def __init__(self, capacity=8, retained=32, ttl=1800):
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='relay')
        self.slots = BoundedSemaphore(capacity)
        self.lock = RLock()
        self.items = {}
        self.retained, self.ttl = retained, ttl

    def _prune(self):
        done = sorted((item['created'], key) for key, item in self.items.items() if item['status'] in ('succeeded', 'failed'))
        for created, key in done:
            if time.monotonic()-created > self.ttl or len(self.items) >= self.retained:
                del self.items[key]

    def submit(self, function):
        if not self.slots.acquire(blocking=False):
            raise QueueFull()
        task_id = str(uuid4())
        with self.lock:
            self._prune()
            self.items[task_id] = {'status': 'queued', 'created': time.monotonic()}
        def run():
            try:
                with self.lock:
                    self.items[task_id]['status'] = 'running'
                result = function()
                with self.lock:
                    self.items[task_id].update(status='succeeded', result=result)
            except Exception:
                with self.lock:
                    self.items[task_id].update(status='failed', error='provider_failed')
            finally:
                self.slots.release()
        self.pool.submit(run)
        return task_id

    def get(self, task_id):
        with self.lock:
            self._prune()
            item = self.items.get(task_id)
            return {key: value for key, value in item.items() if key != 'created'} if item else None
