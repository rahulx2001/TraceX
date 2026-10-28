"""Bound local inference work, including cold initialization.

Native inference cannot be interrupted safely. Timed-out work keeps its slot
until completion; new calls fail immediately instead of accumulating a queue.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
import math
import threading
import time
from typing import Callable, TypeVar

T = TypeVar("T")


class InferenceBusy(TimeoutError):
    pass


class InferenceDeadline:
    def __init__(self, workers: int = 2) -> None:
        self._slots = threading.BoundedSemaphore(workers)
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="slm_inference")

    def run(self, fn: Callable[[], T], *, deadline: float) -> T:
        remaining = deadline - time.monotonic()
        if not math.isfinite(remaining) or remaining <= 0:
            raise TimeoutError("inference deadline expired")
        if not self._slots.acquire(blocking=False):
            raise InferenceBusy("local inference capacity exhausted")
        try:
            future = self._pool.submit(fn)
        except BaseException:
            self._slots.release()
            raise
        future.add_done_callback(lambda _: self._slots.release())
        try:
            return future.result(timeout=max(0, deadline - time.monotonic()))
        except TimeoutError:
            future.cancel()
            raise


LOCAL_INFERENCE = InferenceDeadline()
