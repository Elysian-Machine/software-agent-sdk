"""Filter terminal query sequences from captured output.

When CLI tools (like `gh`, `npm`, etc.) run inside a PTY, they may send
terminal query sequences as part of their progress/spinner UI. These queries
get captured as output. When displayed, the terminal processes them and
responds, causing visible escape code garbage.

This module provides filtering to remove these query sequences while
preserving legitimate formatting escape codes (colors, bold, etc.).

See: https://github.com/OpenHands/software-agent-sdk/issues/2244
"""

import re


# Terminal query sequences that trigger responses (and cause visible garbage)
# These should be stripped from captured output before display.
#
# Reference: ECMA-48, XTerm Control Sequences
# https://invisible-island.net/xterm/ctlseqs/ctlseqs.html

# DSR (Device Status Report) - cursor position query
# Format: ESC [ 6 n  ->  Response: ESC [ row ; col R
_DSR_PATTERN = re.compile(rb"\x1b\[6n")

# OSC (Operating System Command) queries
# Format: ESC ] Ps ; ? (BEL | ST)
# The ";?" pattern indicates a QUERY (vs SET which has actual values)
# Examples:
#   OSC 10 ; ? - foreground color query
#   OSC 11 ; ? - background color query
#   OSC 4 ; index ; ? - palette color query
#   OSC 12 ; ? - cursor color query
#   OSC 17 ; ? - highlight background query
# Terminators: BEL (\x07) or ST (ESC \)
#
# This pattern matches ANY OSC query (ending with ;?) rather than
# specific codes, making it future-proof for other query types.
_OSC_QUERY_PATTERN = re.compile(
    rb"\x1b\]"  # OSC introducer
    rb"\d+"  # Parameter number (10, 11, 4, 12, etc.)
    rb"(?:;[^;\x07\x1b]*)?"  # Optional sub-parameter (e.g., palette index)
    rb";\?"  # Query marker - the key indicator this is a query
    rb"(?:\x07|\x1b\\)"  # BEL or ST terminator
)

# DA (Device Attributes) primary query
# Format: ESC [ c  or  ESC [ 0 c
_DA_PATTERN = re.compile(rb"\x1b\[0?c")

# DA2 (Secondary Device Attributes) query
# Format: ESC [ > c  or  ESC [ > 0 c
_DA2_PATTERN = re.compile(rb"\x1b\[>0?c")

# DECRQSS (Request Selection or Setting) - various terminal state queries
# Format: ESC P $ q <setting> ST
_DECRQSS_PATTERN = re.compile(
    rb"\x1bP\$q"  # DCS introducer + DECRQSS
    rb"[^\x1b]*"  # Setting identifier
    rb"\x1b\\"  # ST terminator
)


def filter_terminal_queries(output: str) -> str:
    """Filter terminal query sequences from captured terminal output.

    Removes escape sequences that would cause the terminal to respond
    when the output is displayed, while preserving legitimate formatting
    sequences (colors, cursor movement, etc.).

    Args:
        output: Raw terminal output that may contain query sequences.

    Returns:
        Filtered output with query sequences removed.
    """
    # Convert to bytes for regex matching (escape sequences are byte-level)
    output_bytes = output.encode("utf-8", errors="surrogateescape")

    # Remove each type of query sequence
    output_bytes = _DSR_PATTERN.sub(b"", output_bytes)
    output_bytes = _OSC_QUERY_PATTERN.sub(b"", output_bytes)
    output_bytes = _DA_PATTERN.sub(b"", output_bytes)
    output_bytes = _DA2_PATTERN.sub(b"", output_bytes)
    output_bytes = _DECRQSS_PATTERN.sub(b"", output_bytes)

    # Convert back to string
    return output_bytes.decode("utf-8", errors="surrogateescape")
