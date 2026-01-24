# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Philosophy

**python-util-belt** is a curated collection of tiny, well-documented, self-contained Python utilities designed to be easily copied into any project. This is NOT a traditional package/library - it's a personal "utility belt" without package management overhead.

**Core Principles:**
- **Minimal dependencies** - modules prefer stdlib (pragmatic exceptions documented)
- **Self-contained** - each utility is a single .py file with complete functionality
- **Copy-paste friendly** - utilities are designed to be copied directly into projects
- **Lean automation** - simple bash/Python scripts for convenience, not complexity
- **Corporate-friendly** - no network dependencies in target projects
- **Git as version control** - git history is the single source of truth

## Architecture: The Minimal Approach

After evaluating various approaches (YAML metadata, complex install scripts, full test suites), we opted for the **leanest viable structure** that solves the core problem: maintaining reusable utilities while keeping them easy to use.

**What we chose NOT to include:**
- ❌ YAML metadata files (use docstrings instead)
- ❌ Complex Python install scripts (simple bash helper sufficient)
- ❌ Automated tests in main repo (tests belong in target projects)
- ❌ Separate examples directory (examples live in docstrings)
- ❌ Version tracking files in target projects (git history is enough)

### Directory Structure

```
python-util-belt/
├── README.md              # User-facing documentation and catalog
├── CLAUDE.md              # This file
├── modules/               # Self-contained utility modules
│   ├── ncvz.py            # Network connectivity checker
│   ├── catch_signals.py   # Signal handler protection
│   └── rmq.py             # RabbitMQ JSON messaging (requires pika)
├── dev-notes/             # Manual testing notepads (development aids)
│   ├── ncvz.md            # Network connectivity test scenarios
│   ├── catch_signals.md   # Signal handling test scenarios
│   └── rmq.md             # RabbitMQ messaging test scenarios
└── scripts/               # Simple helper tools
    ├── copy_module.sh     # Bash script to copy modules to projects
    └── list_modules.py    # Python script to list available modules
```

### Key Design Decisions

**1. Docstring-based metadata** (not YAML)
- Module metadata lives in comprehensive docstrings
- Scripts extract info using `ast.parse()` (stdlib only)
- No duplication between code and metadata files
- Example: `ncvz.py` has all metadata in its module docstring

**2. Simple copy workflow** (not complex installer)
- Primary: `./scripts/copy_module.sh MODULE_NAME TARGET_DIR`
- Alternative: Manual `cp modules/MODULE.py target/`
- No version tracking in target projects
- Git history in this repo tracks all changes

**3. dev-notes/ for development aids** (not automated tests)
- Manual testing notepads used during development
- Documents test scenarios and expected behaviors
- Not automated test suites
- Examples: `dev-notes/ncvz.md` has manual test cases and proxy configurations, `dev-notes/catch_signals.md` has signal handling test scenarios

**4. Minimal scripts** (bash + simple Python)
- `copy_module.sh`: ~40 lines, copies module and shows usage
- `list_modules.py`: ~80 lines, extracts docstring metadata and displays catalog
- No external dependencies (stdlib only)

## Usage Workflow

### For Users (Using Utilities)

```bash
# One-time setup
git clone https://github.com/you/python-util-belt.git ~/python-util-belt

# Browse available modules
~/python-util-belt/scripts/list_modules.py

# Copy to your project
~/python-util-belt/scripts/copy_module.sh ncvz ./my-project/utils/

# Use in code
from utils.ncvz import ncvz
```

### For Developers (Adding Utilities)

1. **Create module** in `modules/your_utility.py`
   - Single file, self-contained
   - Comprehensive docstring (see template below)
   - Prefer stdlib dependencies (external deps allowed if pragmatic)
   - Must include `Version:` and `Author:` in docstring
   - If using external deps, prominently document in "External Dependency" section

2. **Create dev notes** in `dev-notes/your_utility.md`
   - Manual test scenarios
   - Test data (hosts, ports, proxies, etc.)
   - Expected behaviors
   - Development observations

3. **Update README.md** with utility description and examples

4. **Commit to git**

### Module Template

```python
"""
Module Name - Brief one-line description

This module provides longer description with key features listed.

Key Features:
    - Feature 1
    - Feature 2
    - Feature 3

Basic Usage:
    >>> from module import function
    >>> function('example')
    True

Advanced Usage:
    >>> function('example', timeout=2.0, option=True)
    False

Environment Variables:
    ENV_VAR - Description of what it does

Functions:
    function(arg1, arg2, **kwargs) -> ReturnType
        Detailed description of what function does

Author: Your Name
Version: 1.0
"""

import stdlib_module1
import stdlib_module2
from typing import Optional

def function(...):
    """Function docstring with args, returns, examples."""
    pass
```

## Current Modules

### ncvz.py (v1.1)
Network connectivity checker - Python equivalent of `nc -vz HOST PORT`

**Location:** `modules/ncvz.py`
**Dev Notes:** `dev-notes/ncvz.md`
**Features:**
- Direct TCP connectivity checks
- Full URL support (extracts host/port automatically from URLs)
- Corporate proxy support via HTTP CONNECT
- Configurable logging (stdlib, loguru, or custom)
- Environment-based proxy auto-detection
- Zero external dependencies

**Functions:**
- `ncvz(host, port=None, timeout=3.0, proxy=None, logger=None) -> bool` - Accepts host+port or full URL
- `ncvz_auto(host, port=None, timeout=3.0, logger=None) -> bool` - Accepts host+port or full URL
- `ncvz_external(host, port=None, timeout=3.0, logger=None) -> bool` - Accepts host+port or full URL

**URL Parsing:**
- Supports http://, https://, ws://, wss:// schemes
- Extracts port from URL or infers from scheme (http/ws: 80, https/wss: 443)
- Maintains backward compatibility with traditional host+port arguments

### catch_signals.py (v1.0)
Signal handler protection - Defer signal termination for critical code sections

**Location:** `modules/catch_signals.py`
**Dev Notes:** `dev-notes/catch_signals.md`
**Features:**
- Deferred signal handling for critical operations
- Support for SIGINT (Ctrl+C) and SIGTERM signals
- Proper exit codes (130 for SIGINT, 143 for SIGTERM)
- Configurable logging (stdlib, loguru, or custom)
- Immediate handler registration at import time
- Zero external dependencies

**Functions:**
- `assist_signals(logger=None) -> ContextManager`

**Key Implementation Details:**
- Signal handlers registered immediately at module import time
- Encapsulated state in private `_SignalState` class
- Follows Unix exit code convention: 128 + signal_number
- Simple boolean flag for nesting (not depth-counted)

### rmq.py (v1.0)
RabbitMQ JSON messaging - Simple producer/consumer for JSON payloads

**Location:** `modules/rmq.py`
**Dev Notes:** `dev-notes/rmq.md`
**External Dependency:** Requires `pika` library (install: `pip install pika`)
**Features:**
- JSON-only payloads (send dict, receive dict)
- One-shot send function for infrequent messages
- Persistent connection class for high-frequency sending
- Blocking consumer with manual acknowledgment and automatic retry
- Flexible authentication (explicit username/password or guest default)
- Configurable logging (stdlib, loguru, or custom)
- Automatic queue declaration
- Connection health checking

**Functions:**
- `send_json(data, queue, host='localhost', **kwargs) -> bool`
- `RMQProducer(queue, host='localhost', **kwargs)` - Context manager class
- `consume_json(queue, callback, **kwargs)` - Blocking consumer

**Key Implementation Details:**
- First module with external dependency (pragmatic exception)
- Lazy connection in RMQProducer (connects on first send or explicit connect())
- JSON serialization with >1MB payload warnings
- Heartbeat defaults: 0 (one-shot), 600s (producer), 1200s (consumer)
- Manual acknowledgment: ack after success, nack+requeue on failure (automatic retry)
- Malformed JSON rejected without requeue (prevents infinite loops)
- No auto-reconnect (caller should retry on False return)

## Development Commands

### List available modules
```bash
./scripts/list_modules.py
```

### Copy module to a project
```bash
./scripts/copy_module.sh MODULE_NAME TARGET_DIR

# Examples
./scripts/copy_module.sh ncvz ~/my-project/utils/
./scripts/copy_module.sh catch_signals ~/my-project/utils/
./scripts/copy_module.sh rmq ~/my-project/utils/  # Don't forget: pip install pika
```

### Test module functionality
```bash
# Use dev-notes as reference
python3
>>> from modules.ncvz import ncvz
>>> ncvz('google.com', 80)
True

>>> from modules.catch_signals import assist_signals
>>> with assist_signals():
...     print("Protected")
Protected

>>> from modules.rmq import send_json  # Requires: pip install pika
>>> send_json({'task': 'test'}, 'queue')
True
```

### Add new module
```bash
# 1. Create module file
vim modules/new_utility.py

# 2. Create dev notes
vim dev-notes/new_utility.md

# 3. Update README
vim README.md

# 4. Test
python3 -c "from modules.new_utility import function; function('test')"

# 5. Commit
git add modules/new_utility.py dev-notes/new_utility.md README.md
git commit -m "Add new_utility module"
```

## Guidelines

### Module Quality Standards
- **Self-contained**: Single file, minimal dependencies
- **Well-documented**: Comprehensive docstring with examples
- **Feature-rich**: Solve real problems, not toy examples
- **Tested**: Manual testing documented in dev-notes/
- **Typed**: Use type hints where appropriate
- **Error handling**: Graceful failure with clear error messages

### What NOT to Do
- Don't add external dependencies unless pragmatically justified and well-documented
- Don't create complex install scripts
- Don't add YAML/JSON metadata files
- Don't write automated tests in this repo (belongs in target projects)
- Don't create elaborate directory hierarchies
- Don't over-engineer simple problems

### When to Add a New Module
- Utility is genuinely reusable across projects
- Functionality cannot be achieved with 1-2 lines of stdlib
- No suitable stdlib alternative exists
- You've used it (or plan to use it) in 2+ projects

## FAQ

**Q: Why no metadata/ YAML files?**
A: Docstrings already contain all necessary metadata. YAML files create duplication and maintenance burden.

**Q: Why no automated tests?**
A: Tests are context-dependent. Write tests in target projects where utilities are used. dev-notes/ provides manual testing guidance for development.

**Q: Why bash instead of Python for copy_module?**
A: Bash is simpler for file operations and universally available on Linux/Mac. No AST parsing or metadata needed for copying.

**Q: Can utilities depend on each other?**
A: Avoid if possible. Each utility should be independently copyable. If shared code is needed, duplicate the small amount of code or extract to a separate utility.

**Q: Should I version utilities?**
A: Include version in docstring. Git history tracks all changes. No need for semantic versioning or release tags unless project grows significantly.

**Q: What about Windows support?**
A: Modules are cross-platform (Python stdlib). Scripts work on WSL/Git Bash. Users can manually copy on Windows.

## Project History

1. **Initial brainstorming** - Explored complex approaches with YAML, install scripts, tests
2. **Research phase** - Analyzed real-world utility collections (Spatie, Go stdlib patterns)
3. **Simplification** - Eliminated overengineering, kept minimal viable structure
4. **First module** - `ncvz.py` network connectivity checker
5. **Documentation** - This CLAUDE.md and comprehensive README.md
6. **Second module** - `catch_signals.py` signal handler protection with proper exit codes
7. **Third module** - `rmq.py` RabbitMQ JSON messaging - first module with external dependency (pika)
8. **Architecture refinement** - Changed `catch_signals.py` from lazy to immediate handler registration for predictable startup behavior

## External Dependencies

### Philosophy Shift: Pragmatic Dependencies

The project originally targeted **zero external dependencies** (stdlib only). However, the `rmq.py` module introduces a pragmatic exception:

- **rmq.py requires `pika`** - RabbitMQ client library
- **Rationale**: Implementing AMQP 0-9-1 protocol from scratch with stdlib is impractical
- **Documented prominently** in module docstring, dev-notes, and README

### Dependency Management Strategy

**No requirements.txt in repo root** - Keep belt lean

**Per-module approach**:
- Module docstring clearly states: "External Dependency: Requires 'pika' library: pip install pika"
- dev-notes file documents installation command
- README catalog marks modules with external dependencies
- Users install dependencies when copying module to their project

**Client responsibility**:
- User copies `modules/rmq.py` to their project
- User runs: `pip install pika` (or adds to their requirements.txt)
- Module raises clear ImportError with installation instructions if pika missing

**Future modules with dependencies**:
- Document dependency in module docstring (prominent "External Dependency" section)
- Add installation command to dev-notes
- Mark in README catalog
- Keep dependencies minimal and well-justified
- Prefer stdlib when practical

## Future Considerations

**If project grows significantly**, consider adding:
- Git tags for releases (e.g., `v2024.12`)
- More sophisticated `list_modules.py` with search/filtering
- GitHub Actions for basic linting
- More modules in subdirectories by category (e.g., `modules/networking/`, `modules/files/`)

**Do NOT add unless absolutely necessary:**
- Package management (pip, poetry, etc.)
- External dependencies (unless pragmatically justified like rmq.py)
- Complex build systems
- Automated testing framework
- CI/CD beyond basic linting

## Contributing

When others contribute:
1. Ensure module follows all guidelines above
2. Verify minimal dependencies (prefer stdlib, document any external deps prominently)
3. Check docstring completeness
4. Request dev-notes with manual test scenarios
5. Update README with new utility info
