"""Tests for ResourceLockManager."""

import threading
import time

import pytest

from openhands.sdk.conversation.resource_lock_manager import ResourceLockManager


def test_basic_lock_and_release():
    mgr = ResourceLockManager()
    with mgr.lock("file:/a.py"):
        pass  # should not raise


def test_no_keys_is_noop():
    mgr = ResourceLockManager()
    with mgr.lock():
        pass  # zero keys → no locks acquired, no error


def test_serializes_same_resource():
    """Two threads locking the same resource must not overlap."""
    mgr = ResourceLockManager()
    log: list[str] = []

    def worker(name: str) -> None:
        with mgr.lock("file:/shared.py"):
            log.append(f"{name}-enter")
            time.sleep(0.05)
            log.append(f"{name}-exit")

    t1 = threading.Thread(target=worker, args=("A",))
    t2 = threading.Thread(target=worker, args=("B",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # One must fully complete before the other starts
    assert log == ["A-enter", "A-exit", "B-enter", "B-exit"] or log == [
        "B-enter",
        "B-exit",
        "A-enter",
        "A-exit",
    ]


def test_parallel_different_resources():
    """Two threads locking different resources should overlap."""
    mgr = ResourceLockManager()
    barrier = threading.Barrier(2, timeout=5)
    reached_barrier = [False, False]

    def worker(idx: int, key: str) -> None:
        with mgr.lock(key):
            reached_barrier[idx] = True
            barrier.wait()  # both must reach here concurrently

    t1 = threading.Thread(target=worker, args=(0, "file:/a.py"))
    t2 = threading.Thread(target=worker, args=(1, "file:/b.py"))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert all(reached_barrier)


def test_sorted_order_prevents_deadlock():
    """Sorted acquisition prevents deadlocks with opposite request order."""
    mgr = ResourceLockManager()
    results: list[str] = []

    def worker(name: str, k1: str, k2: str) -> None:
        with mgr.lock(k1, k2):
            results.append(name)

    t1 = threading.Thread(target=worker, args=("A", "r:1", "r:2"))
    t2 = threading.Thread(target=worker, args=("B", "r:2", "r:1"))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert set(results) == {"A", "B"}


def test_timeout_raises():
    mgr = ResourceLockManager(timeouts={"file:": 0.05})

    # Hold the lock in another thread
    held = threading.Event()
    release = threading.Event()

    def holder() -> None:
        with mgr.lock("file:/x"):
            held.set()
            release.wait(timeout=5)

    t = threading.Thread(target=holder)
    t.start()
    held.wait()

    with pytest.raises(TimeoutError, match="file:/x"):
        with mgr.lock("file:/x"):
            pass

    release.set()
    t.join()


def test_duplicate_keys_deduplicated():
    """Passing the same key multiple times should not deadlock."""
    mgr = ResourceLockManager()
    with mgr.lock("file:/a.py", "file:/a.py"):
        pass


def test_default_timeouts():
    mgr = ResourceLockManager()
    assert mgr._get_timeout("file:/foo") == 30.0
    assert mgr._get_timeout("terminal:session") == 300.0
    assert mgr._get_timeout("browser:session") == 300.0
    assert mgr._get_timeout("mcp:server") == 300.0
    assert mgr._get_timeout("tool:my_tool") == 60.0
    assert mgr._get_timeout("unknown:key") == 30.0


def test_release_on_exception():
    """Lock must be released even if the body raises."""
    mgr = ResourceLockManager()
    with pytest.raises(RuntimeError):
        with mgr.lock("file:/a.py"):
            raise RuntimeError("boom")

    # Should be able to re-acquire immediately
    with mgr.lock("file:/a.py"):
        pass


def test_partial_release_on_timeout():
    """If the second lock times out, the first must be released."""
    mgr = ResourceLockManager(timeouts={"r:": 0.05})

    held = threading.Event()
    release = threading.Event()

    def holder() -> None:
        with mgr.lock("r:b"):
            held.set()
            release.wait(timeout=5)

    t = threading.Thread(target=holder)
    t.start()
    held.wait()

    with pytest.raises(TimeoutError):
        with mgr.lock("r:a", "r:b"):
            pass  # r:a acquired, r:b times out

    # r:a should have been released despite the timeout on r:b
    acquired = threading.Event()

    def check() -> None:
        with mgr.lock("r:a"):
            acquired.set()

    checker = threading.Thread(target=check)
    checker.start()
    checker.join(timeout=2)
    assert acquired.is_set()

    release.set()
    t.join()
