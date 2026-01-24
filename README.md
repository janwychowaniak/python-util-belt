# python-util-belt

A curated collection of tiny, well-documented Python helpers that stitch together clean, maintainable applications.

## Philosophy

This is **NOT** a traditional Python package. It's a personal "utility belt" - a collection of self-contained, single-file utilities designed to be copied directly into your projects.

**Core Principles:**
- **Minimal dependencies** - modules use only Python stdlib (with rare pragmatic exceptions*)
- **Self-contained** - each utility is a complete, single `.py` file
- **Copy-paste friendly** - no package management overhead
- **Corporate-friendly** - no network dependencies in target projects
- **Single source of truth** - this repo via git history

*Note: `rmq.py` requires the `pika` library for RabbitMQ connectivity - a pragmatic exception where implementing AMQP from scratch would be impractical.

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/python-util-belt.git ~/python-util-belt
```

### 2. Browse available utilities

```bash
cd ~/python-util-belt
./scripts/list_modules.py
```

### 3. Copy a utility to your project

```bash
# Simple copy
./scripts/copy_module.sh ncvz ~/my-project/utils/

# Or manual copy
cp modules/ncvz.py ~/my-project/utils/
```

### 4. Use in your code

```python
from utils.ncvz import ncvz

# Check network connectivity
if ncvz('google.com', 80):
    print("Connection successful!")
```

## Available Utilities

### `ncvz` - Network Connectivity Checker

Python equivalent of `nc -vz HOST PORT` with corporate proxy support and URL parsing.

**Features:**
- Direct TCP connectivity checks
- Full URL support (extracts host/port automatically)
- Corporate proxy support via HTTP CONNECT
- Configurable logging (stdlib, loguru, or custom)
- Environment-based proxy auto-detection
- Zero external dependencies

**Usage:**
```python
from utils.ncvz import ncvz, ncvz_auto, ncvz_external

# Basic connectivity check
ncvz('google.com', 80)  # True/False

# With timeout
ncvz('internal.service', 5432, timeout=2.0)

# Full URL support (port extracted from URL)
ncvz('http://127.0.0.1:19000')  # Port 19000 from URL
ncvz('https://api.service.com')  # Port 443 inferred from https scheme
ncvz('http://example.com:8080', timeout=1.0)

# Via corporate proxy
ncvz('external-api.com', 443, proxy='http://proxy.company.com:8080')

# Auto-detect proxy from environment (HTTP_PROXY, HTTPS_PROXY)
ncvz_auto('api.service.com', 443)
ncvz_auto('http://internal.service:5000')  # Also supports URLs
```

**Version:** 1.1
**Author:** Mila 🪄

---

### `catch_signals` - Signal Handler Protection

Defer signal termination (SIGINT/SIGTERM) for critical code sections.

**Features:**
- Deferred signal handling for critical operations
- Support for SIGINT (Ctrl+C) and SIGTERM signals
- Proper exit codes (130 for SIGINT, 143 for SIGTERM)
- Configurable logging (stdlib, loguru, or custom)
- Immediate handler registration at import time
- Zero external dependencies

**Usage:**
```python
from utils.catch_signals import assist_signals

# Protect critical operation
with assist_signals():
    critical_database_commit()
    cleanup_temporary_files()

# With custom logger
from loguru import logger
with assist_signals(logger=logger):
    long_running_backup()

# Multiple protected sections
while running:
    with assist_signals():
        process_batch()  # Each batch independently protected
```

**Version:** 1.0
**Author:** Jan 🪄

---

### `rmq` - RabbitMQ JSON Messaging

Simple producer/consumer for JSON message passing via RabbitMQ.

**External Dependency:** Requires `pika` library - install with: `pip install pika`

**Features:**
- JSON-only payloads (send dict, receive dict)
- One-shot send function for infrequent messages
- Persistent connection class for high-frequency sending
- Blocking consumer with manual acknowledgment and automatic retry
- Flexible authentication (explicit username/password or guest default)
- Configurable logging (stdlib, loguru, or custom)

**Usage:**
```python
from utils.rmq import send_json, RMQProducer, consume_json

# One-shot send (simple)
send_json({'task': 'process', 'id': 123}, 'work_queue')

# Persistent producer (efficient for multiple sends)
with RMQProducer('tasks', host='localhost') as producer:
    producer.send({'task': 'first'})
    producer.send({'task': 'second'})

# Consumer (blocks forever)
def process(data: dict):
    print(f"Task: {data['task']}")

consume_json('work_queue', process)

# With authentication
send_json(data, 'queue', username='admin', password='secret')
```

**Version:** 1.0
**Author:** Jan 🪄

---

*More utilities coming soon...*

## Development Workflow

### Adding a New Utility

1. **Create the module** in `modules/your_utility.py`
   - Single file, self-contained
   - Comprehensive docstring with examples
   - Only stdlib dependencies
   - Include `Version:` and `Author:` in docstring

2. **Test during development** using manual testing notes
   - Create `dev-notes/your_utility.md` for testing notes
   - Document test scenarios and expected results
   - This is for development aid, not automated tests

3. **Update this README** with:
   - Utility description
   - Key features
   - Usage examples
   - Version and author

4. **Commit to git**
   ```bash
   git add modules/your_utility.py dev-notes/your_utility.md
   git commit -m "Add your_utility module"
   ```

### Module Guidelines

Each utility module should:
- Be completely self-contained in a single `.py` file
- Prefer Python standard library (external deps allowed if pragmatic and well-justified)
- If using external dependencies, prominently document in module docstring
- Have a comprehensive module-level docstring including:
  - Clear description and key features
  - Basic and advanced usage examples
  - Function signatures with docstrings
  - Environment variables (if applicable)
  - Version and author information
- Follow the pattern: feature-rich but zero dependencies

### Example Module Structure

```python
"""
Module Name - Brief description

Longer description with key features listed.

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
        Description of what function does

Author: Your Name
Version: 1.0
"""

import stdlib_module1
import stdlib_module2

def function(...):
    """Function docstring."""
    pass
```

## Directory Structure

```
python-util-belt/
├── README.md              # This file
├── CLAUDE.md              # Guidance for Claude Code
├── modules/               # Self-contained utility modules
│   └── ncvz.py
├── dev-notes/             # Manual testing notepads (not automated tests)
│   └── ncvz.md
└── scripts/               # Helper tools
    ├── copy_module.sh     # Copy utility to your project
    └── list_modules.py    # List available utilities
```

## FAQ

**Q: Why not publish as a package on PyPI?**
A: That would create external dependencies. The goal is zero-dependency utilities you can copy into any environment, including corporate networks with restricted package access.

**Q: How do I update a utility I've already copied?**
A: Pull the latest from this repo and re-copy the module. Git history tracks all changes.

**Q: Should I commit copied utilities to my project?**
A: Yes! Once copied, they're part of your project. You control when/if to update them.

**Q: What about tests?**
A: Write tests in your target project as needed. The `dev-notes/` directory contains manual testing notes used during development, not automated tests.

**Q: Can I modify copied utilities?**
A: Absolutely! Once copied, customize as needed. If you make improvements worth sharing, consider contributing back.

## License

MIT License - see LICENSE file for details.

## Contributing

This is a personal utility collection, but contributions are welcome! If you have a utility that fits the philosophy (self-contained, stdlib-only, well-documented), feel free to open a PR.
