"""Async cancellation mixin for interruptible LLM calls.

This module provides the AsyncCancellationMixin class which manages a background
event loop for running async LLM calls that can be cancelled from any thread.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from concurrent.futures import CancelledError as FutureCancelledError, Future
from typing import Any, TypeVar

from openhands.sdk.llm.exceptions import LLMCancelledError
from openhands.sdk.logger import get_logger


logger = get_logger(__name__)

T = TypeVar("T")


class AsyncCancellationMixin:
    """Mixin providing async cancellation support for LLM calls.

    This mixin manages a background event loop in a daemon thread, allowing
    synchronous callers to use async LLM calls internally while supporting
    immediate cancellation via Future.cancel().

    Host class requirements (must define these private attributes):
    - _async_loop: asyncio.AbstractEventLoop | None
    - _async_loop_thread: threading.Thread | None
    - _current_future: Future[Any] | None
    - _task_lock: threading.Lock
    - usage_id: str (for logging/debugging)
    """

    # Type declarations for attributes that must be defined in the host class.
    # These are not actually assigned here - they tell the type checker what
    # attributes will be available at runtime.
    _async_loop: asyncio.AbstractEventLoop | None
    _async_loop_thread: threading.Thread | None
    _current_future: Future[Any] | None
    _task_lock: threading.Lock
    usage_id: str

    def _ensure_async_loop(self) -> asyncio.AbstractEventLoop:
        """Lazily create background event loop thread for interruptible calls.

        The event loop runs in a daemon thread and is used to execute async
        LLM calls. This allows synchronous callers to use async internally
        while supporting immediate cancellation via Task.cancel().
        """
        if self._async_loop is None:
            self._async_loop = asyncio.new_event_loop()
            self._async_loop_thread = threading.Thread(
                target=self._async_loop.run_forever,
                daemon=True,
                name=f"llm-async-{self.usage_id}",
            )
            self._async_loop_thread.start()
            logger.debug(f"Started async event loop thread for LLM {self.usage_id}")
        return self._async_loop

    def cancel(self) -> None:
        """Cancel any in-flight LLM call (best effort).

        This method cancels the current LLM call immediately. The cancellation
        will take effect at the next await point in the LLM call.

        Can be called from any thread. After cancellation, the LLM can be
        used for new calls - the cancellation only affects the currently
        running call.

        Example:
            >>> # In another thread:
            >>> llm.cancel()  # Cancels the current LLM call
        """
        with self._task_lock:
            if self._current_future is not None:
                logger.info(f"Cancelling LLM call for {self.usage_id}")
                # Cancel the Future directly - thread-safe and immediate
                self._current_future.cancel()

    def is_cancelled(self) -> bool:
        """Check if the current call has been cancelled.

        Returns:
            True if there's a current call and it has been cancelled.
        """
        with self._task_lock:
            if self._current_future is not None:
                return self._current_future.cancelled()
        return False

    def _close_async_resources(self) -> None:
        """Stop the background event loop and cleanup resources.

        This method should be called when the LLM instance is no longer needed,
        especially in long-running applications that create/destroy many LLM
        instances to prevent thread leaks.

        After calling this method, the LLM can still be used - the event loop
        will be lazily recreated on the next LLM call.
        """
        with self._task_lock:
            # Cancel any in-flight call first by cancelling the Future
            if self._current_future is not None:
                self._current_future.cancel()
                self._current_future = None

            if self._async_loop is not None:
                # Stop the event loop
                self._async_loop.call_soon_threadsafe(self._async_loop.stop)
                self._async_loop = None

            if self._async_loop_thread is not None:
                # Wait for thread to finish (with timeout to avoid deadlock)
                self._async_loop_thread.join(timeout=1.0)
                self._async_loop_thread = None

                logger.debug(f"Stopped async event loop thread for LLM {self.usage_id}")

    def _run_async_with_cancellation(
        self,
        coro: Coroutine[Any, Any, T],
        cancelled_error_message: str,
    ) -> T:
        """Run an async coroutine in the background event loop.

        This method submits the coroutine to the background event loop and blocks
        until completion, while allowing the call to be cancelled via cancel().

        Args:
            coro: The coroutine to execute.
            cancelled_error_message: Message for LLMCancelledError if cancelled.

        Returns:
            The result of the coroutine.

        Raises:
            LLMCancelledError: If the call is cancelled via cancel().
        """
        loop = self._ensure_async_loop()
        future: Future[T] = asyncio.run_coroutine_threadsafe(coro, loop)

        with self._task_lock:
            self._current_future = future

        try:
            return future.result()
        except (asyncio.CancelledError, FutureCancelledError):
            raise LLMCancelledError(cancelled_error_message)
        finally:
            with self._task_lock:
                self._current_future = None

    def _reset_async_state(self) -> None:
        """Reset async state for use in deepcopy.

        This sets async-related attributes to their initial states.
        They will be lazily recreated when needed.
        """
        self._async_loop = None
        self._async_loop_thread = None
        self._current_future = None
        self._task_lock = threading.Lock()
