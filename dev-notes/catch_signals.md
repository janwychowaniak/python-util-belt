# catch_signals - Manual Testing Notes

## Overview

This file contains manual test scenarios for the `catch_signals` module. These are not automated tests - they're reference guides for manually testing signal handling behavior during development and after making changes.

## Test Environment Setup

```python
# Basic test script template
from time import sleep
from catch_signals import assist_signals

# For custom logger testing
# from loguru import logger
```

---

## Test Scenario 1: Signal During Protected Block (Deferred Exit)

**Purpose:** Verify that signals received inside a protected block are deferred until the block completes.

**Test Script:**
```python
from time import sleep
from catch_signals import assist_signals

print("Starting protected block...")
with assist_signals():
    print("  [PROTECTED] Sleeping 5 seconds - press Ctrl+C during this time")
    sleep(5)
    print("  [PROTECTED] Block completed")
print("After protected block (should not reach here)")
```

Press `Ctrl+C` during the 5-second sleep (while "PROTECTED" message visible). Observe that the sleep completes before exit.

Expected Exit Code: 130 (verify with `echo $?`)

---

## Test Scenario 2: Signal Outside Protected Block (Immediate Exit)

**Purpose:** Verify that signals received outside protected blocks cause immediate exit.

**Test Script:**
```python
from time import sleep
from catch_signals import assist_signals

print("Outside protected block - press Ctrl+C now")
sleep(5)
print("Still outside (should not reach here after Ctrl+C)")
```

Press `Ctrl+C` during the 5-second sleep. Observe immediate exit.

Expected Exit Code: 130

---

## Test Scenario 3: Custom Logger (Loguru Compatibility)

**Purpose:** Verify that custom loggers work correctly (e.g., loguru).

**Prerequisites:**
```bash
pip install loguru
```

**Test Script:**
```python
from time import sleep
from loguru import logger
from catch_signals import assist_signals

logger.info("Using loguru logger")
with assist_signals(logger=logger):
    logger.info("In protected block - press Ctrl+C")
    sleep(5)
    logger.info("Block completed")
```

Press `Ctrl+C` during sleep. Verify loguru-formatted output appears.

Expected Exit Code: 130

**Note:** Should work with any logger that implements `.debug()`, `.info()`, `.warning()` methods.

---

## Test Scenario 4: SIGTERM Handling (Exit Code 143)

**Purpose:** Verify SIGTERM signal handling and correct exit code (143).

**Test Script:**
```python
# test_sigterm.py
from time import sleep
from catch_signals import assist_signals

print("PID:", __import__('os').getpid())
print("Waiting for SIGTERM...")

with assist_signals():
    print("  [PROTECTED] Sleeping 30 seconds")
    sleep(30)
    print("  [PROTECTED] Completed")
```

Terminal 1: `python3 test_sigterm.py` -> Note the PID from output
Terminal 2: `kill -TERM <PID>`

Expected Exit Code: 143

---

## Test Scenario 5: Multiple Protected Blocks (Sequential)

**Purpose:** Verify that multiple protected blocks work correctly in sequence.

**Test Script:**
```python
from time import sleep
from catch_signals import assist_signals

for i in range(3):
    print(f"\nIteration {i}")
    with assist_signals():
        print(f"  [PROTECTED] Processing batch {i} (2 seconds)")
        sleep(2)
        print(f"  [PROTECTED] Batch {i} complete")
    print(f"Between blocks (iteration {i})")

print("All iterations completed")
```

Press `Ctrl+C` during one of the protected blocks. Observe that current block completes before exit.

**Expected Behavior:**
- ✓ Signal during block: completes that block, then exits
- ✓ Exit code is 130

---

## Test Scenario 6: Nested Blocks (Edge Case)

**Purpose:** Document behavior of nested context managers (simple flag, not counted).

**Test Script:**
```python
from time import sleep
from catch_signals import assist_signals

print("Outer block start")
with assist_signals():
    print("  [OUTER] In outer block")
    sleep(2)

    print("  Inner block start")
    with assist_signals():
        print("    [INNER] In inner block - press Ctrl+C here")
        sleep(5)
        print("    [INNER] Inner complete")

    print("  [OUTER] Between inner and outer end")
    sleep(2)
    print("  [OUTER] Outer complete")

print("After all blocks")
```

Press `Ctrl+C` during the *inner* block sleep. Observe behavior.

**Expected Behavior:**
- ✓ Signal deferred until inner block completes
- ✓ After inner block, program exits (does NOT continue outer block)
- ✓ Exit code is 130

**Note:** Nesting is supported but uses a simple boolean flag, not depth tracking. The signal causes exit when the innermost block completes, even if outer blocks remain. This is documented as "supported but not recommended" in the API documentation.

---

## Exit Code Verification Commands

After running any test, check the exit code:

```bash
# Bash/Zsh
echo $?

# Expected exit codes:
# - 0   : Normal completion (no signal)
# - 130 : SIGINT (Ctrl+C, signal 2)
# - 143 : SIGTERM (signal 15)
```

**Exit Code Formula:** `128 + signal_number`
- SIGINT = 2 → 128 + 2 = 130
- SIGTERM = 15 → 128 + 15 = 143

---

## Testing Lazy Initialization (Import Safety)

**Purpose:** Verify no signal handlers are registered at import time.

**Test Script:**
```python
# test_lazy_init.py
import sys
import signal

print("1. Before import - default SIGINT handler:")
print("  ", signal.signal(signal.SIGINT, signal.SIG_DFL))

import catch_signals

print("2. After import - SIGINT handler (should be default):")
print("  ", signal.signal(signal.SIGINT, signal.SIG_DFL))

print("3. Restoring and using assist_signals...")
signal.signal(signal.SIGINT, signal.default_int_handler)
with catch_signals.assist_signals():
    print("4. Inside protected block - handlers now registered")
    print("   Press Ctrl+C to test")
    from time import sleep
    sleep(5)
```

**Expected Behavior:**
- ✓ Before first use: default signal handler in place
- ✓ After import: handlers NOT registered yet
- ✓ After first `assist_signals()`: handlers registered
- ✓ No side effects from simple `import catch_signals`

---

## Common Issues & Troubleshooting

### Issue: Exit code is 0 instead of 130/143
**Cause:** Script completed normally, signal not received
**Solution:** Ensure you're pressing Ctrl+C during the sleep, not after

### Issue: Multiple presses of Ctrl+C
**Behavior:** Second Ctrl+C during same protected block may cause immediate exit (OS behavior)
**Note:** This is expected - single signal is deferred, multiple signals may force exit

---

## Development Notes

### Signal Number Reference
```python
signal.SIGINT = 2   # Ctrl+C
signal.SIGTERM = 15 # kill command default
```

### Exit Code Convention
Standard Unix convention: `exit_code = 128 + signal_number`
- Matches bash behavior
- Allows calling code to identify which signal caused exit
- Different from simple `sys.exit(0)` or `sys.exit(1)`

### Why Lazy Initialization?
- Avoids import-time side effects (Pythonic)
- Safe for modules that import but don't use
- Clean testing (can import without affecting signal handlers)
- Follows best practices from PEP 8 and Python stdlib

### Thread Safety Note
Signal handlers are process-wide in Python. This module uses a simple module-level state appropriate for single-threaded or main-thread signal handling. **Not designed for complex multi-threaded scenarios where different threads need independent signal protection.**
