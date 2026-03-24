"""Resource-level lock manager for parallel tool execution.

Provides per-resource locking so that tools operating on the same shared state
(files, terminal session, browser session, …) are serialized while tools
touching *different* resources can run concurrently.

Locks are acquired in sorted order to prevent deadlocks and use FIFOLock
for fairness (no starvation).
"""

from __future__ import annotations

import threading
from collections.abc import Generator
from contextlib import contextmanager
from typing import ClassVar

from openhands.sdk.conversation.fifo_lock import FIFOLock


class ResourceLockManager:
    """Manages per-resource FIFO locks for concurrent tool execution.

    Usage::

        mgr = ResourceLockManager()
        with mgr.lock("file:/a.py", "file:/b.py"):
            # exclusive access to both files
            ...
    """

    DEFAULT_TIMEOUTS: ClassVar[dict[str, float]] = {
        "file:": 30.0,
        "terminal:": 300.0,
        "browser:": 300.0,
        "mcp:": 300.0,
        "tool:": 60.0,
    }

    def __init__(
        self,
        timeouts: dict[str, float] | None = None,
    ) -> None:
        self._locks: dict[str, FIFOLock] = {}
        self._meta_lock = threading.Lock()
        self._timeouts = timeouts or self.DEFAULT_TIMEOUTS

    def _get_lock(self, key: str) -> FIFOLock:
        """Return (or lazily create) the FIFOLock for *key*."""
        with self._meta_lock:
            if key not in self._locks:
                self._locks[key] = FIFOLock()
            return self._locks[key]

    def _get_timeout(self, key: str) -> float:
        """Return the timeout for a resource key based on its prefix."""
        for prefix, timeout in self._timeouts.items():
            if key.startswith(prefix):
                return timeout
        return 30.0

    @contextmanager
    def lock(self, *resource_keys: str) -> Generator[None]:
        """Acquire locks for all *resource_keys* in sorted order, then release.

        Sorted acquisition prevents deadlocks when two threads need
        overlapping sets of resources.

        Raises:
            TimeoutError: If a lock cannot be acquired within its timeout.
        """
        sorted_keys = sorted(set(resource_keys))
        acquired: list[str] = []
        try:
            for key in sorted_keys:
                timeout = self._get_timeout(key)
                if not self._get_lock(key).acquire(timeout=timeout):
                    raise TimeoutError(
                        f"Could not acquire lock for '{key}' within {timeout}s"
                    )
                acquired.append(key)
            yield
        finally:
            for key in reversed(acquired):
                self._locks[key].release()
