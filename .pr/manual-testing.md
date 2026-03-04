# Manual Testing Guide for PR #2245

**PR**: [Fix terminal escape code leak from stdin](https://github.com/OpenHands/software-agent-sdk/pull/2245)
**Branch**: `fix/stdin-escape-code-leak`
**Issue**: #2244

---

## ⚠️ INVESTIGATION FINDINGS

### Root Cause Analysis (2026-03-04)

The escape codes appearing in the test output are **NOT stdin leaks** - they are being captured as part of the terminal tool's PTY output stream.

**What's happening:**
1. The `gh` command (or other CLI tools with spinners) sends terminal queries:
   - DSR (`\x1b[6n`) - cursor position request
   - OSC 11 (`\x1b]11;?`) - background color request

2. The terminal responds by writing escape sequences to the PTY

3. The SDK's terminal tool captures ALL PTY output, including these terminal responses

4. The captured output (including escape codes) is displayed by the visualizer

**Evidence:** The escape codes appeared IN THE MIDDLE of the conversation output (between "Exit code: 0" and "Message from Agent"), not after the script exited.

**Implication:** The `flush_stdin()` fix addresses a DIFFERENT problem (stdin corruption for interactive CLI apps). The escape codes in the test output are a PTY output filtering issue, not a stdin leak.

### Two Separate Issues:

1. **stdin leak** (what PR #2245 fixes): Terminal responses accumulating in stdin, corrupting subsequent `input()` calls or appearing as garbage AFTER script exits

2. **PTY output pollution** (what we observed): Terminal responses being captured as part of command output and displayed by the visualizer

### Recommendation:

The PTY output issue should be addressed separately, possibly by:
- Filtering escape sequences from captured terminal output
- Setting terminal environment variables to disable queries (e.g., `TERM=dumb`)
- Using `--no-pager` or similar flags for CLI tools

---

## Environment Status ✅

- [x] On correct branch: `fix/stdin-escape-code-leak`
- [x] Branch up to date with origin
- [x] Dependencies synced (`uv sync --dev`)
- [x] LLM_API_KEY configured
- [x] LLM_BASE_URL: `https://llm-proxy.app.all-hands.dev/`

## Quick Commands

```bash
# Ensure you're on the right branch
git checkout fix/stdin-escape-code-leak
git pull

# Sync dependencies
uv sync --dev

# Run automated tests first
uv run pytest tests/sdk/logger/test_flush_stdin.py -v
```

---

## Test 1: Minimal Reproduction (No API Key Needed)

This test directly injects terminal queries to verify the fix works:

```bash
cd /Users/jpshack/code/all-hands/software-agent-sdk
uv run python - <<'EOF'
#!/usr/bin/env python3
"""Minimal reproduction of ANSI escape code leak."""

import os
import select
import sys
import time

def check_stdin() -> bytes:
    """Check for pending data in stdin (non-blocking)."""
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
    except Exception:
        return b""

def main():
    print("ANSI Escape Code Leak Test")
    print("=" * 40)

    if not sys.stdout.isatty():
        print("ERROR: Run in a real terminal (not CI/piped)")
        sys.exit(1)

    for turn in range(1, 4):
        print(f"\n--- Turn {turn} ---")
        # Send DSR query (cursor position request)
        # Terminal responds with: ESC [ row ; col R
        print("  Sending DSR query (\\x1b[6n)...")
        sys.stdout.write("\x1b[6n")
        sys.stdout.flush()

        time.sleep(0.1)

        leaked = check_stdin()
        if leaked:
            print(f"  LEAK DETECTED: {len(leaked)} bytes: {leaked!r}")
        else:
            print("  No leak (terminal may not respond)")

    print("\n" + "=" * 40)
    print("If you see ';1R' or similar after this script exits, that's the bug.")

if __name__ == "__main__":
    main()
EOF
```

**Expected results BEFORE fix**: Leak detected, garbage in prompt after exit
**Expected results AFTER fix**: Still shows leaks (this is the raw terminal behavior - the fix is in the SDK layer)

---

## Test 2: SDK Agent Test with flush_stdin()

This tests the actual fix by running an agent with terminal tools:

```bash
cd /Users/jpshack/code/all-hands/software-agent-sdk
uv run python - <<'EOF'
#!/usr/bin/env python3
"""Real-world reproduction using SDK agent."""

import os
import sys

from openhands.sdk import Agent, Conversation, LLM, Tool
from openhands.tools.terminal import TerminalTool

llm = LLM(
    model=os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514"),
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL"),
)

agent = Agent(llm=llm, tools=[Tool(name=TerminalTool.name)])
conversation = Conversation(agent=agent, workspace="/tmp")

# Commands with spinners (like gh) trigger more queries
print("Sending message to agent...")
conversation.send_message("Run: gh pr list --repo OpenHands/openhands --limit 3")
conversation.run()
conversation.close()

print("\n" + "=" * 40)
print("Check for garbage in your shell prompt after this exits.")
print("With the fix, there should be NO garbage like ';1R' or 'rgb:...'")
EOF
```

**Expected results AFTER fix**: No garbage in terminal prompt after script exits

---

## Test 3: Multiple Conversation Turns

Tests that stdin is properly flushed between conversation turns:

```bash
cd /Users/jpshack/code/all-hands/software-agent-sdk
uv run python - <<'EOF'
#!/usr/bin/env python3
"""Multi-turn conversation test."""

import os
from openhands.sdk import Agent, Conversation, LLM, Tool
from openhands.tools.terminal import TerminalTool

llm = LLM(
    model=os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514"),
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL"),
)

agent = Agent(llm=llm, tools=[Tool(name=TerminalTool.name)])
conversation = Conversation(agent=agent, workspace="/tmp")

# Multiple turns to accumulate potential leaks
for i, cmd in enumerate(["echo 'Turn 1'", "ls -la /tmp | head -5", "echo 'Done'"]):
    print(f"\n{'='*40}\nTurn {i+1}: {cmd}\n{'='*40}")
    conversation.send_message(f"Run: {cmd}")
    conversation.run()

conversation.close()
print("\n" + "=" * 40)
print("Multiple turns complete. Check for accumulated garbage.")
EOF
```

---

## Test 4: Automated Unit Tests

```bash
# Run the flush_stdin tests
uv run pytest tests/sdk/logger/test_flush_stdin.py -v

# Run all SDK logger tests  
uv run pytest tests/sdk/logger/ -v

# Run with coverage
uv run pytest tests/sdk/logger/test_flush_stdin.py -v --cov=openhands.sdk.logger --cov-report=term-missing
```

---

## Comparison Testing (Before/After)

To compare behavior with and without the fix:

```bash
# Test on main branch (before fix)
git stash
git checkout main
uv sync --dev
# Run Test 2 above - expect garbage in prompt

# Test on fix branch (after fix)
git checkout fix/stdin-escape-code-leak
git stash pop
uv sync --dev
# Run Test 2 above - expect NO garbage
```

---

## What to Look For

### ✅ Success indicators:
- No escape code garbage (`^[[23;1R`, `;1R`, `rgb:...`) in terminal after script exits
- `input()` calls work correctly without pre-filled garbage
- Automated tests pass

### ❌ Failure indicators:
- Garbage characters appearing in shell prompt after script exits
- `input()` returning unexpected content
- Terminal mode corruption (echo off, raw mode stuck)

---

## Files Changed in This PR

```
openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py  # Calls flush_stdin()
openhands-sdk/openhands/sdk/conversation/visualizer/default.py       # Calls flush_stdin()
openhands-sdk/openhands/sdk/logger/__init__.py                       # Exports flush_stdin
openhands-sdk/openhands/sdk/logger/logger.py                         # Implements flush_stdin()
tests/sdk/logger/test_flush_stdin.py                                 # Unit tests
```

To review the implementation:
```bash
git --no-pager show HEAD -- openhands-sdk/openhands/sdk/logger/logger.py | head -300
```
