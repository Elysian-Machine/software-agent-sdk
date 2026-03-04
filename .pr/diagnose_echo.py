#!/usr/bin/env python3
"""Diagnose terminal echo of escape sequence responses.

The problem: When terminal queries are sent, the terminal responds by:
1. Writing the response to stdin (the "leak" we're flushing)
2. ECHOING the response to stdout (the visible noise)

This script tests whether we can suppress the echo.
"""

import os
import select
import sys
import termios
import time


def send_query_normal_mode():
    """Send query in normal terminal mode - expect visible echo."""
    print("\n[Normal mode] Sending DSR query...")
    sys.stdout.write("\x1b[6n")
    sys.stdout.flush()
    time.sleep(0.2)


def send_query_no_echo_mode():
    """Send query with echo disabled - should suppress visible response."""
    print("\n[No-echo mode] Sending DSR query...")

    # Save current terminal settings
    old_settings = termios.tcgetattr(sys.stdin)

    try:
        # Disable echo (ECHO flag)
        new_settings = list(old_settings)
        new_settings[3] &= ~termios.ECHO  # Disable echo
        termios.tcsetattr(sys.stdin, termios.TCSANOW, new_settings)

        # Send the query
        sys.stdout.write("\x1b[6n")
        sys.stdout.flush()

        # Wait for response
        time.sleep(0.2)

        # Read and discard the response from stdin
        new_settings[3] &= ~termios.ICANON  # Also disable canonical mode for reading
        new_settings[6][termios.VMIN] = 0
        new_settings[6][termios.VTIME] = 0
        termios.tcsetattr(sys.stdin, termios.TCSANOW, new_settings)

        if select.select([sys.stdin], [], [], 0)[0]:
            data = os.read(sys.stdin.fileno(), 4096)
            print(f"  (Flushed {len(data)} bytes from stdin: {data!r})")

    finally:
        # Restore original settings
        termios.tcsetattr(sys.stdin, termios.TCSANOW, old_settings)

    print("  Query sent with echo disabled")


def send_query_raw_mode():
    """Send query in raw mode - full control."""
    print("\n[Raw mode] Sending DSR query...")

    old_settings = termios.tcgetattr(sys.stdin)

    try:
        # Enter raw mode (no echo, no canonical, no signals)
        new_settings = list(old_settings)
        new_settings[3] &= ~(termios.ECHO | termios.ICANON | termios.ISIG)
        new_settings[6][termios.VMIN] = 0
        new_settings[6][termios.VTIME] = 0
        termios.tcsetattr(sys.stdin, termios.TCSANOW, new_settings)

        # Send the query
        sys.stdout.write("\x1b[6n")
        sys.stdout.flush()

        # Wait and read response
        time.sleep(0.2)

        if select.select([sys.stdin], [], [], 0)[0]:
            data = os.read(sys.stdin.fileno(), 4096)
            print(f"  (Flushed {len(data)} bytes from stdin: {data!r})")

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSANOW, old_settings)

    print("  Query sent in raw mode")


def main():
    print("=" * 60)
    print("TERMINAL ECHO DIAGNOSTIC")
    print("=" * 60)
    print(f"stdin.isatty(): {sys.stdin.isatty()}")
    print(f"stdout.isatty(): {sys.stdout.isatty()}")

    if not sys.stdout.isatty():
        print("\n⚠️  Run directly in terminal, not piped!")
        return

    # Test 1: Normal mode (expect visible echo)
    send_query_normal_mode()
    print("  ^ Did you see escape codes above this line?")

    # Test 2: Echo disabled
    send_query_no_echo_mode()
    print("  ^ Should be NO visible escape codes")

    # Test 3: Raw mode
    send_query_raw_mode()
    print("  ^ Should be NO visible escape codes")

    # Test 4: Multiple queries with echo suppression
    print("\n[Multiple queries with echo suppressed]")
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        new_settings = list(old_settings)
        new_settings[3] &= ~(termios.ECHO | termios.ICANON)
        new_settings[6][termios.VMIN] = 0
        new_settings[6][termios.VTIME] = 0
        termios.tcsetattr(sys.stdin, termios.TCSANOW, new_settings)

        for i in range(3):
            sys.stdout.write("\x1b[6n")  # DSR
            sys.stdout.write("\x1b]11;?\x07")  # OSC 11
        sys.stdout.flush()
        time.sleep(0.3)

        total = 0
        while select.select([sys.stdin], [], [], 0)[0]:
            data = os.read(sys.stdin.fileno(), 4096)
            if not data:
                break
            total += len(data)
        print(f"  Flushed {total} bytes, no visible echo")

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSANOW, old_settings)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("If echo suppression works, we can modify flush_stdin() to")
    print("disable echo BEFORE flushing, preventing visible noise.")


if __name__ == "__main__":
    main()
