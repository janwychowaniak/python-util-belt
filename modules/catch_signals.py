"""
Signal handler protection - Defer signal termination for critical code sections.

This module provides a context manager that protects critical code sections from
immediate termination when SIGINT (Ctrl+C) or SIGTERM signals are received. Signals
are deferred until the protected block completes, allowing graceful cleanup and
preventing data corruption or incomplete operations.

Key Features:
    - Deferred signal handling for critical sections
    - Support for SIGINT (Ctrl+C) and SIGTERM signals
    - Proper exit codes (130 for SIGINT, 143 for SIGTERM)
    - Configurable logging (stdlib, loguru, or custom)
    - Lazy initialization (no import-time side effects)
    - Zero external dependencies

Basic Usage:
    >>> from catch_signals import assist_signals
    >>> with assist_signals():
    ...     # Protected code - signals deferred until block completes
    ...     critical_database_commit()
    ...     cleanup_temporary_files()

Advanced Usage:
    >>> from loguru import logger
    >>> with assist_signals(logger=logger):
    ...     long_running_backup()

    >>> # Multiple protected sections
    >>> while running:
    ...     with assist_signals():
    ...         process_batch()  # Each batch independently protected

Behavior:
    - Signal received INSIDE protected block: Deferred until block exits, then
      program exits with proper code (130 for SIGINT, 143 for SIGTERM)
    - Signal received OUTSIDE protected block: Immediate exit with proper code
    - Exit codes follow Unix convention: 128 + signal_number

Environment Variables:
    None

Functions:
    assist_signals(logger=None) -> ContextManager
        Context manager that protects code from immediate signal termination

Author: Jan 🪄
Version: 1.0
"""

import sys
import signal
import logging
from contextlib import contextmanager
from typing import Optional, Any


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Private module-level state (lazy initialization)

_signal_state: Optional['_SignalState'] = None


class _SignalState:
    """Encapsulates signal handling state (initialized lazily on first use)."""

    def __init__(self):
        self.received_signal: Optional[int] = None  # Signal number (2 for SIGINT, 15 for SIGTERM)
        self.in_protected_block: bool = False
        self.handlers_registered: bool = False


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Private helper functions

def _signal_handler(sig: int, frame, logger: Any) -> None:
    """
    Internal signal handler called when SIGINT or SIGTERM received.

    If currently in a protected block, stores the signal for deferred exit.
    Otherwise, exits immediately with proper exit code (128 + signal_number).

    Args:
        sig: Signal number (signal.SIGINT=2 or signal.SIGTERM=15)
        frame: Stack frame (unused, required by signal handler signature)
        logger: Logger instance for output
    """
    global _signal_state

    signal_name = 'SIGINT' if sig == signal.SIGINT else 'SIGTERM'
    logger.warning(f"Signal received: {signal_name} (signal {sig}), will exit")

    _signal_state.received_signal = sig

    if not _signal_state.in_protected_block:
        # Exit immediately with proper exit code (128 + signal_number)
        # SIGINT (2) -> 130, SIGTERM (15) -> 143
        exit_code = 128 + sig
        logger.info(f"Exiting immediately with code {exit_code}")
        sys.exit(exit_code)


def _ensure_handlers_registered(logger: Any) -> _SignalState:
    """
    Ensure signal handlers are registered (lazy initialization).

    On first call, creates the global state object and registers signal handlers
    for SIGINT and SIGTERM. Subsequent calls return the existing state without
    re-registering handlers.

    Args:
        logger: Logger instance to pass to signal handlers

    Returns:
        The global signal state object

    Note:
        This function enables lazy initialization - signal handlers are only
        registered when assist_signals() is first used, not at module import time.
    """
    global _signal_state

    if _signal_state is None:
        _signal_state = _SignalState()

    if not _signal_state.handlers_registered:
        # Register handlers for SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, lambda sig, frame: _signal_handler(sig, frame, logger))
        signal.signal(signal.SIGTERM, lambda sig, frame: _signal_handler(sig, frame, logger))
        _signal_state.handlers_registered = True
        logger.debug("Signal handlers registered for SIGINT and SIGTERM")

    return _signal_state


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Public API

@contextmanager
def assist_signals(logger: Optional[Any] = None):
    """
    Context manager that protects code from immediate signal termination.

    When SIGINT (Ctrl+C) or SIGTERM is received inside the protected block,
    the signal is deferred until the block completes. This allows critical
    operations to finish gracefully before the program exits with the proper
    exit code (130 for SIGINT, 143 for SIGTERM).

    Args:
        logger: Optional logger instance (defaults to stdlib logging).
                Supports any logger with .debug(), .info(), .warning() methods.
                Compatible with stdlib logging, loguru, or custom loggers.

    Yields:
        None

    Examples:
        Basic usage - protect critical operation:
        >>> with assist_signals():
        ...     critical_database_commit()

        With custom logger (loguru):
        >>> from loguru import logger
        >>> with assist_signals(logger=logger):
        ...     long_running_backup()

        Multiple protected sections in a loop:
        >>> while running:
        ...     with assist_signals():
        ...         process_batch()  # Each batch protected individually

        Protect file operations:
        >>> with assist_signals():
        ...     with open('data.txt', 'w') as f:
        ...         f.write(important_data)
        ...     os.rename('data.txt', 'data.final')

    Notes:
        - Signal handlers registered on first use (lazy initialization)
        - Exit codes follow Unix convention: 128 + signal_number
          * SIGINT (signal 2) → exit code 130
          * SIGTERM (signal 15) → exit code 143
        - Nesting supported but uses simple flag (inner blocks don't add protection)
        - Thread safety: Signals are process-wide, state is module-level
        - Not designed for complex multi-threaded signal handling scenarios
    """
    # Fallback to stdlib logging if no logger provided
    if logger is None:
        logger = logging.getLogger(__name__)

    # Ensure handlers registered (lazy init on first call)
    state = _ensure_handlers_registered(logger)

    # Mark as in protected block
    state.in_protected_block = True

    try:
        yield
    finally:
        # Unmark protected block
        state.in_protected_block = False

        # If signal was received during protected block, exit now with proper code
        if state.received_signal is not None:
            exit_code = 128 + state.received_signal
            signal_name = 'SIGINT' if state.received_signal == signal.SIGINT else 'SIGTERM'
            logger.info(f"Protected block completed, exiting with code {exit_code} ({signal_name})")
            sys.exit(exit_code)
