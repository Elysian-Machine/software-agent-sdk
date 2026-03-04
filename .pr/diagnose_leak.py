#!/usr/bin/env python3
"""Diagnose stdin escape code leak.

Run this DIRECTLY in a terminal (not piped):
    uv run python .pr/diagnose_leak.py

Watch for garbage appearing AFTER the script exits.
"""

import os
import select
import sys
import time


def check_stdin_raw() -> bytes:
    """Read pending stdin data without blocking."""
    if not sys.stdin.isatty():
        return b""
    try:
        import termios

        old = termios.tcgetattr(sys.stdin)
        new = list(old)
        new[3] &= ~(termios.ICANON | termios.ECHO)
        new[6][termios.VMIN] = 0
        new[6][termios.VTIME] = 0
        termios.tcsetattr(sys.stdin, termios.TCSANOW, new)
        data = b""
        if select.select([sys.stdin], [], [], 0)[0]:
            data = os.read(sys.stdin.fileno(), 4096)
        termios.tcsetattr(sys.stdin, termios.TCSANOW, old)
        return data
    except Exception as e:
        print(f"Error: {e}")
        return b""


def main():
    from openhands.sdk.logger import flush_stdin, logger as logger_module

    print("=" * 60)
    print("STDIN LEAK DIAGNOSTIC")
    print("=" * 60)
    print(f"stdin.isatty(): {sys.stdin.isatty()}")
    print(f"stdout.isatty(): {sys.stdout.isatty()}")

    if not sys.stdout.isatty():
        print("\n⚠️  WARNING: stdout is not a TTY!")
        print("    Terminal queries won't get responses.")
        print("    Run directly in terminal, not piped.")

    # Test 1: Send query, wait, check stdin
    print("\n[Test 1] Send DSR query, check stdin after 200ms")
    sys.stdout.write("\x1b[6n")
    sys.stdout.flush()
    time.sleep(0.2)
    data1 = check_stdin_raw()
    print(f"  stdin data: {data1!r}")

    # Test 2: Send query, flush with SDK, check what was caught
    print("\n[Test 2] Send DSR query, call flush_stdin()")
    sys.stdout.write("\x1b[6n")
    sys.stdout.flush()
    time.sleep(0.2)
    flushed = flush_stdin()
    preserved = logger_module._preserved_input_buffer
    print(f"  Bytes flushed: {flushed}")
    print(f"  Preserved buffer: {preserved!r}")

    # Test 3: OSC 11 query
    print("\n[Test 3] Send OSC 11 query (background color)")
    sys.stdout.write("\x1b]11;?\x07")
    sys.stdout.flush()
    time.sleep(0.2)
    flushed2 = flush_stdin()
    preserved2 = logger_module._preserved_input_buffer
    print(f"  Bytes flushed: {flushed2}")
    print(f"  Preserved buffer: {preserved2!r}")

    # Test 4: Multiple rapid queries (simulates Rich/gh behavior)
    print("\n[Test 4] Multiple rapid queries then flush")
    for _ in range(3):
        sys.stdout.write("\x1b[6n")
        sys.stdout.write("\x1b]11;?\x07")
    sys.stdout.flush()
    time.sleep(0.3)
    flushed3 = flush_stdin()
    preserved3 = logger_module._preserved_input_buffer
    print(f"  Bytes flushed: {flushed3}")
    print(f"  Preserved buffer: {preserved3!r}")

    # Final flush before exit
    print("\n[Final] Calling flush_stdin() before exit")
    final_flushed = flush_stdin()
    print(f"  Final bytes flushed: {final_flushed}")

    print("\n" + "=" * 60)
    print("DONE - Watch for garbage on the next shell prompt!")
    print("If you see '^[[...R' or 'rgb:...' after '$', the leak persists.")
    print("=" * 60)


if __name__ == "__main__":
    main()
