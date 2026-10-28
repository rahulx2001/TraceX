"""Blue-green deploy with call draining (feature #51).

On SIGTERM: stop accepting new contacts, let active ones reach CLOSING, persist,
then exit. ``DrainController`` is process-global.
"""

from __future__ import annotations

import asyncio
import signal
import threading
from typing import Any, Callable


class ServiceDrainingError(RuntimeError):
    """Raised when create_interaction is refused because the process is draining."""

    def __init__(self, message: str = "service_draining: not accepting new contacts") -> None:
        super().__init__(message)


class DrainController:
    def __init__(self) -> None:
        self._draining = False
        self._lock = threading.Lock()
        self._active: set[str] = set()
        self._on_drain_hooks: list[Callable[[], None]] = []
        self._sigterm_installed = False

    @property
    def draining(self) -> bool:
        with self._lock:
            return self._draining

    def register_active(self, interaction_id: str) -> bool:
        """Return False if draining (reject new contacts)."""
        with self._lock:
            if self._draining:
                return False
            self._active.add(interaction_id)
            return True

    def unregister(self, interaction_id: str) -> None:
        with self._lock:
            self._active.discard(interaction_id)

    def begin_drain(self) -> dict[str, Any]:
        with self._lock:
            self._draining = True
            active = list(self._active)
        for h in self._on_drain_hooks:
            try:
                h()
            except Exception:
                pass
        return {"draining": True, "active_interactions": active, "count": len(active)}

    def reset(self) -> None:
        """Clear drain flags (tests / post-deploy warm start)."""
        with self._lock:
            self._draining = False
            self._active.clear()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "draining": self._draining,
                "active_count": len(self._active),
                "active_interactions": list(self._active),
                "ready_to_exit": self._draining and len(self._active) == 0,
                "sigterm_handler_installed": self._sigterm_installed,
            }

    def on_drain(self, fn: Callable[[], None]) -> None:
        self._on_drain_hooks.append(fn)

    async def wait_until_drained(self, timeout_s: float = 120.0) -> bool:
        deadline = asyncio.get_event_loop().time() + timeout_s
        while asyncio.get_event_loop().time() < deadline:
            if self.status()["ready_to_exit"]:
                return True
            await asyncio.sleep(0.05)
        return self.status()["ready_to_exit"]


DRAIN = DrainController()


def install_sigterm_handler() -> Callable[[], None]:
    """Drain for a bounded interval, then forward SIGTERM to the server.

    Uvicorn owns process exit and graceful transport shutdown. Preserve its
    handler rather than swallowing the signal. Return a lifespan cleanup.
    """
    import os
    previous = signal.getsignal(signal.SIGTERM)
    task = None
    timeout = max(0.0, min(120.0, float(os.getenv("FRONTLINE_DRAIN_TIMEOUT_S", "10"))))

    def forward(signum, frame):
        if callable(previous):
            previous(signum, frame)
        elif previous == signal.SIG_DFL:
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            os.kill(os.getpid(), signal.SIGTERM)

    async def finish(signum, frame):
        await DRAIN.wait_until_drained(timeout)
        forward(signum, frame)

    def handler(signum, frame):
        nonlocal task
        DRAIN.begin_drain()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            forward(signum, frame)
            return
        if task is None:
            task = loop.create_task(finish(signum, frame))
        else:
            task.cancel()
            forward(signum, frame)

    def cleanup():
        if task is not None:
            task.cancel()
        if signal.getsignal(signal.SIGTERM) is handler:
            signal.signal(signal.SIGTERM, previous)
        DRAIN._sigterm_installed = False

    try:
        signal.signal(signal.SIGTERM, handler)
        DRAIN._sigterm_installed = True
    except (ValueError, OSError):
        pass
    return cleanup
